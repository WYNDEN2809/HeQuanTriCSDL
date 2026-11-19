"""In-app and optional email notifications for operational events."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from accounts.models import BrandMember

from .models import Notification

logger = logging.getLogger(__name__)


def _recipients(brand_id, user_ids=None):
    members = BrandMember.objects.filter(brand_id=brand_id, user__is_active=True).select_related("user")
    if user_ids is not None:
        members = members.filter(user_id__in=user_ids)
    else:
        roles = getattr(settings, "ALERT_NOTIFICATION_ROLES", ("BRAND_ADMIN", "OPS_MANAGER"))
        members = members.filter(brand_role__in=roles)
    return [member.user for member in members]


def _send_email(notification):
    if not getattr(settings, "ALERT_EMAIL_NOTIFICATIONS", False) or not notification.user.email:
        return
    base = getattr(settings, "PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    try:
        send_mail(notification.title, f"{notification.message}\n\n{base}{notification.target_url}",
                  None, [notification.user.email], fail_silently=False)
    except Exception:
        logger.exception("Could not email notification %s to user %s", notification.pk, notification.user_id)
    else:
        notification.external_sent_at = timezone.now()
        notification.save(update_fields=["external_sent_at"])


@transaction.atomic
def notify_brand(*, brand_id, event_key, title, message, target_url, user_ids=None):
    """Create one notification per recipient and optionally send email once."""
    created = []
    for user in _recipients(brand_id, user_ids):
        notification, was_created = Notification.objects.get_or_create(
            user=user, event_key=event_key,
            defaults={"brand_id": brand_id, "title": title, "message": message, "target_url": target_url},
        )
        if was_created:
            created.append(notification)
        elif (getattr(settings, "ALERT_EMAIL_NOTIFICATIONS", False)
              and notification.external_sent_at is None):
            _send_email(notification)
        if was_created:
            _send_email(notification)
    return created


def notify_alert_created(alert):
    try:
        return notify_brand(
            brand_id=alert.machine.brand_id, event_key=f"alert:{alert.pk}:created",
            title=f"Cảnh báo {alert.severity}: {alert.alert_type}",
            message=f"Máy {alert.machine.name} phát sinh cảnh báo {alert.alert_type}.",
            target_url=f"/portal/alerts/{alert.pk}/",
        )
    except Exception:
        logger.exception("Could not create notifications for alert %s", alert.pk)
        return []


def notify_technician_assignment(alert, technician, ticket):
    try:
        return notify_brand(
            brand_id=alert.machine.brand_id, user_ids=[technician.pk],
            event_key=f"alert:{alert.pk}:ticket:{ticket.pk}:assigned:{technician.pk}",
            title=f"Phiếu bảo trì #{ticket.pk} được giao cho bạn",
            message=f"Cảnh báo #{alert.pk} tại máy {alert.machine.name} cần được xử lý.",
            target_url=f"/portal/maintenance/{ticket.pk}/",
        )
    except Exception:
        logger.exception("Could not create assignment notification for ticket %s", ticket.pk)
        return []


def retry_pending_emails(limit=500):
    if not getattr(settings, "ALERT_EMAIL_NOTIFICATIONS", False):
        return 0
    pending = list(Notification.objects.filter(external_sent_at__isnull=True)
                    .select_related("user").order_by("created_at")[:limit])
    attempted = 0
    for notification in pending:
        if notification.user.email:
            attempted += 1
            _send_email(notification)
    return attempted

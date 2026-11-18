"""Xu ly canh bao (Nguoi 3): tiep nhan, giao viec, xu ly, mo lai, qua han (escalation)."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from reports.audit import log_action

from .models import Alert

# Thoi gian xu ly toi da (gio) theo muc do; qua han => hien nhan "qua han" va dua len dau (escalation)
SLA_HOURS = {"CRITICAL": 1, "HIGH": 4, "MEDIUM": 24, "LOW": 72}


def sla_deadline(alert):
    return alert.created_at + timedelta(hours=SLA_HOURS.get(alert.severity, 24))


def is_overdue(alert, now=None):
    now = now or timezone.now()
    return alert.status != Alert.Status.RESOLVED and now > sla_deadline(alert)


def overdue_q(now=None):
    """Dieu kien loc DB cho canh bao chua xu ly va da qua han SLA."""
    now = now or timezone.now()
    q = Q()
    for sev, hours in SLA_HOURS.items():
        q |= Q(severity=sev, created_at__lt=now - timedelta(hours=hours))
    return q & ~Q(status=Alert.Status.RESOLVED)


def _brand_id(alert):
    return alert.machine.brand_id


def acknowledge_alert(alert, user):
    now = timezone.now()
    n = Alert.objects.filter(pk=alert.pk, status=Alert.Status.OPEN).update(
        status=Alert.Status.ACKNOWLEDGED, acknowledged_at=now)
    if not n:
        raise PortalError("Cảnh báo đã được tiếp nhận hoặc xử lý trước đó.")
    log_action(user, "ALERT_ACK", "Alert", alert.pk, _brand_id(alert),
               old_value={"status": alert.status}, new_value={"status": "ACKNOWLEDGED"})


def resolve_alert(alert, user, note):
    note = (note or "").strip()
    if not note:
        raise PortalError("Cần ghi chi tiết xử lý khi đóng cảnh báo.")
    now = timezone.now()
    n = Alert.objects.filter(pk=alert.pk, status__in=[Alert.Status.OPEN, Alert.Status.ACKNOWLEDGED]).update(
        status=Alert.Status.RESOLVED, resolved_at=now)
    if not n:
        raise PortalError("Cảnh báo đã được xử lý trước đó.")
    Alert.objects.filter(pk=alert.pk, acknowledged_at__isnull=True).update(acknowledged_at=now)
    log_action(user, "ALERT_RESOLVE", "Alert", alert.pk, _brand_id(alert),
               old_value={"status": alert.status}, new_value={"status": "RESOLVED", "note": note})


def reopen_alert(alert, user, note):
    note = (note or "").strip()
    if not note:
        raise PortalError("Cần ghi lý do mở lại cảnh báo.")
    n = Alert.objects.filter(pk=alert.pk, status=Alert.Status.RESOLVED).update(
        status=Alert.Status.OPEN, acknowledged_at=None, resolved_at=None)
    if not n:
        raise PortalError("Chỉ mở lại được cảnh báo đã xử lý.")
    log_action(user, "ALERT_REOPEN", "Alert", alert.pk, _brand_id(alert),
               old_value={"status": "RESOLVED"}, new_value={"status": "OPEN", "note": note})


def technicians_for(alert):
    """Ky thuat vien cua thuong hieu so huu may (de giao viec)."""
    return [m.user for m in BrandMember.objects.filter(
        brand_id=_brand_id(alert), brand_role="TECHNICIAN", user__is_active=True).select_related("user")]


@transaction.atomic
def assign_alert(alert, user, technician_id):
    """
    Giao viec: tao phieu bao tri tu canh bao va giao cho ky thuat vien (dich vu cua Nguoi 5),
    dong thoi tiep nhan canh bao neu dang o trang thai moi.
    """
    alert = Alert.objects.select_for_update().select_related("machine").get(pk=alert.pk)
    if alert.status == Alert.Status.RESOLVED:
        raise PortalError("Không thể giao việc cho cảnh báo đã xử lý; hãy mở lại cảnh báo trước.")
    tech = next((t for t in technicians_for(alert) if t.pk == technician_id), None)
    if tech is None:
        raise PortalError("Kỹ thuật viên không hợp lệ cho thương hiệu của máy này.")
    try:
        from maintenance.services import create_ticket_from_alert
    except ImportError:
        raise PortalError("Module bảo trì chưa được cài đặt.")
    ticket = create_ticket_from_alert(alert, created_by=user, assigned_to=tech)
    if alert.status == Alert.Status.OPEN:
        acknowledge_alert(alert, user)
    log_action(user, "ALERT_ASSIGN", "Alert", alert.pk, _brand_id(alert),
               new_value={"ticket_id": ticket.pk, "technician": tech.username})
    return ticket

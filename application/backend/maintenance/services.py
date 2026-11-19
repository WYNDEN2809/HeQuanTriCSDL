"""Maintenance ticket workflows shared by alerts and the brand portal."""

from django.db import transaction

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from reports.audit import log_action
from reports.notifications import notify_technician_assignment

from .models import MaintenanceRecord


@transaction.atomic
def create_ticket_from_alert(alert, created_by=None, assigned_to=None):
    """Create or reuse the ticket linked to an alert, keeping assignment in-brand."""
    alert = type(alert).objects.select_for_update().select_related("machine").get(pk=alert.pk)
    if created_by is None:
        creator = BrandMember.objects.filter(
            brand_id=alert.machine.brand_id, user__is_active=True,
        ).select_related("user").order_by("id").first()
        if creator is None:
            raise PortalError("Không tìm được người dùng của thương hiệu để tạo phiếu bảo trì.")
        created_by = creator.user
    if assigned_to is not None:
        valid = BrandMember.objects.filter(
            brand_id=alert.machine.brand_id, user_id=assigned_to.pk,
            brand_role="TECHNICIAN", user__is_active=True,
        ).exists()
        if not valid:
            raise PortalError("Kỹ thuật viên không hợp lệ cho thương hiệu của máy này.")

    ticket = MaintenanceRecord.objects.filter(alert_id=alert.pk).first()
    if ticket:
        changed = ticket.assigned_to_id != getattr(assigned_to, "pk", None)
        if changed:
            ticket.assigned_to = assigned_to
            ticket.save(update_fields=["assigned_to"])
            log_action(created_by, "MAINTENANCE_ASSIGN", "MaintenanceRecord", ticket.pk,
                       alert.machine.brand_id, new_value={"assigned_to": getattr(assigned_to, "username", None)})
        if assigned_to is not None:
            try:
                notify_technician_assignment(alert, assigned_to, ticket)
            except Exception:
                # Ticket assignment must remain successful if email/notifications are unavailable.
                pass
        return ticket

    ticket = MaintenanceRecord.objects.create(
        alert=alert, machine=alert.machine, created_by=created_by, assigned_to=assigned_to,
        maintenance_type=MaintenanceRecord.Type.REPAIR,
        description=f"Tạo tự động từ cảnh báo #{alert.pk} ({alert.alert_type}, {alert.severity}).",
        status=MaintenanceRecord.Status.OPEN,
    )
    log_action(created_by, "MAINTENANCE_CREATE", "MaintenanceRecord", ticket.pk,
               alert.machine.brand_id, new_value={"alert_id": alert.pk, "assigned_to": getattr(assigned_to, "username", None)})
    if assigned_to is not None:
        try:
            notify_technician_assignment(alert, assigned_to, ticket)
        except Exception:
            pass
    return ticket

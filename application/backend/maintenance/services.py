<<<<<<< HEAD
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
=======
"""Vong doi phieu bao tri (Nguoi 5): tao, giao viec, ky thuat vien thuc hien, checklist, xit thu, dong phieu."""
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import BrandMember
from accounts.portal_utils import PortalError, ascii_text
from devices import machine_services
from devices.models import Alert, DeviceEvent, Machine, MachineSlot
from inventory.models import InventoryLog
from reports.audit import log_action

from .checklists import POST_TEST_TEXT, items_for
from .models import MaintenanceChecklistItem as Item
from .models import MaintenanceRecord as Record

PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SLA_HOURS = {"CRITICAL": 4, "HIGH": 24, "MEDIUM": 72, "LOW": 168}
OPEN_STATUSES = (Record.Status.OPEN, Record.Status.IN_PROGRESS)
_PREFIX = re.compile(r"^\[P:(LOW|MEDIUM|HIGH|CRITICAL)\]\s*")
ALERT_TO_TYPE = {
    "LOW_STOCK": "REFILL_SUPPORT", "MACHINE_OFFLINE": "INSPECTION", "DOOR_OPEN": "INSPECTION",
    "LEAKAGE_SUSPECTED": "REPAIR", "SENSOR_FAILURE": "PART_REPLACEMENT", "ACTUATOR_FAILURE": "REPAIR",
    "DISPENSE_FAILURE": "CALIBRATION",
}


# ------------------------------------------------------------------ do uu tien / han xu ly
def priority_of(ticket):
    """Do uu tien duoc luu trong tien to mo ta [P:HIGH]; neu khong co thi lay theo muc do canh bao gan voi phieu."""
    m = _PREFIX.match(ticket.description or "")
    if m:
        return m.group(1)
    if ticket.alert_id and ticket.alert is not None:
        return ticket.alert.severity
    return "MEDIUM"


def clean_description(ticket):
    return _PREFIX.sub("", ticket.description or "")


def due_at(ticket):
    return ticket.created_at + timedelta(hours=SLA_HOURS[priority_of(ticket)])


def is_overdue(ticket, now=None):
    return ticket.status in OPEN_STATUSES and (now or timezone.now()) > due_at(ticket)


def _desc(priority, text):
    prefix = f"[P:{priority}] "
    return prefix + (ascii_text(text, 500 - len(prefix)) or "")


# ------------------------------------------------------------------ tien ich
def _tech_or_error(brand_id, user):
    ok = BrandMember.objects.filter(
        user_id=user.pk, brand_id=brand_id, brand_role="TECHNICIAN", user__is_active=True).exists()
    if not ok:
        raise PortalError("Người được giao phải là kỹ thuật viên của thương hiệu sở hữu máy.")
    return user


def _default_creator(brand_id):
    for role in ("OPS_MANAGER", "BRAND_ADMIN"):
        m = BrandMember.objects.filter(brand_id=brand_id, brand_role=role, user__is_active=True).select_related("user").first()
        if m:
            return m.user
    raise PortalError("Thương hiệu chưa có Operations Manager hoặc Brand Admin để đứng tên phiếu.")


def _block_orders_if_critical(machine, priority, user, ticket):
    """Phieu CRITICAL: dua may sang trang thai ERROR => khong nhan don moi cho toi khi bao tri xong."""
    if priority != "CRITICAL":
        return
    machine = Machine.objects.get(pk=machine.pk)  # lay trang thai moi nhat
    if machine.status in (Machine.Status.ONLINE, Machine.Status.OFFLINE):
        machine_services.set_machine_status(machine, Machine.Status.ERROR, user, f"Critical ticket #{ticket.pk}")


def _open_tickets(machine_id, exclude_pk=None):
    qs = Record.objects.filter(machine_id=machine_id, status__in=OPEN_STATUSES)
    return qs.exclude(pk=exclude_pk) if exclude_pk else qs


# ------------------------------------------------------------------ tao / giao viec
def create_ticket(machine, created_by, maintenance_type, description, priority="MEDIUM", assigned_to=None, alert=None):
    if maintenance_type not in Record.Type.values:
        raise PortalError("Loại bảo trì không hợp lệ.")
    if priority not in PRIORITIES:
        raise PortalError("Mức ưu tiên không hợp lệ.")
    if assigned_to is not None:
        _tech_or_error(machine.brand_id, assigned_to)
    now = timezone.now()
    with transaction.atomic():
        rec = Record.objects.create(
            alert=alert, machine_id=machine.pk, created_by=created_by, assigned_to=assigned_to,
            maintenance_type=maintenance_type, description=_desc(priority, description),
            status=Record.Status.OPEN, created_at=now,
        )
        Item.objects.bulk_create([
            Item(record=rec, phase=phase, item_text=text, sort_order=i)
            for i, (phase, text) in enumerate(items_for(maintenance_type), start=1)
        ])
        _block_orders_if_critical(machine, priority, created_by, rec)
        log_action(created_by, "TICKET_CREATE", "MaintenanceRecord", rec.pk, machine.brand_id,
                   new_value={"machine": machine.name, "type": maintenance_type, "priority": priority,
                              "assigned_to": assigned_to.username if assigned_to else None,
                              "alert_id": alert.pk if alert else None})
    return rec


def create_ticket_from_alert(alert, created_by=None, assigned_to=None, priority=None):
    """Ham dung chung voi module canh bao: khong tao trung neu canh bao da co phieu dang mo."""
    alert = Alert.objects.select_related("machine", "machine_slot").get(pk=alert.pk)
    existing = Record.objects.filter(alert_id=alert.pk, status__in=OPEN_STATUSES).first()
    if existing:
        if assigned_to is not None and existing.assigned_to_id != assigned_to.pk:
            assign_ticket(existing, assigned_to, created_by or assigned_to)
            existing.refresh_from_db()
        return existing
    creator = created_by or _default_creator(alert.machine.brand_id)
    slot = f", slot {alert.machine_slot.slot_number}" if alert.machine_slot else ""
    return create_ticket(
        alert.machine, creator, ALERT_TO_TYPE.get(alert.alert_type, "INSPECTION"),
        f"Xu ly canh bao #{alert.pk} {alert.alert_type}{slot}", priority or alert.severity, assigned_to, alert,
    )


def assign_ticket(ticket, tech_user, by_user):
    if ticket.status not in OPEN_STATUSES:
        raise PortalError("Phiếu đã đóng.")
    _tech_or_error(ticket.machine.brand_id, tech_user)
    old = ticket.assigned_to_id
    Record.objects.filter(pk=ticket.pk).update(assigned_to_id=tech_user.pk)
    log_action(by_user, "TICKET_ASSIGN", "MaintenanceRecord", ticket.pk, ticket.machine.brand_id,
               old_value={"assigned_to_id": old}, new_value={"assigned_to": tech_user.username})


def set_priority(ticket, priority, by_user):
    if priority not in PRIORITIES:
        raise PortalError("Mức ưu tiên không hợp lệ.")
    if ticket.status not in OPEN_STATUSES:
        raise PortalError("Phiếu đã đóng.")
    old = priority_of(ticket)
    Record.objects.filter(pk=ticket.pk).update(description=_desc(priority, clean_description(ticket)))
    with transaction.atomic():
        _block_orders_if_critical(ticket.machine, priority, by_user, ticket)
        log_action(by_user, "TICKET_PRIORITY", "MaintenanceRecord", ticket.pk, ticket.machine.brand_id,
                   old_value={"priority": old}, new_value={"priority": priority})


# ------------------------------------------------------------------ ky thuat vien thuc hien
def _check_executor(ticket, user):
    if user.is_platform_admin:
        return
    if ticket.assigned_to_id not in (None, user.pk):
        raise PortalError("Phiếu này đã được giao cho kỹ thuật viên khác.")


def start_ticket(ticket, user):
    """Bat dau: phieu -> IN_PROGRESS va dua may vao che do bao tri (khong nhan don khach)."""
    _check_executor(ticket, user)
    with transaction.atomic():
        n = Record.objects.filter(pk=ticket.pk, status=Record.Status.OPEN).update(
            status=Record.Status.IN_PROGRESS,
            assigned_to_id=ticket.assigned_to_id if ticket.assigned_to_id else user.pk)
        if not n:
            raise PortalError("Phiếu không còn ở trạng thái mới.")
        machine_services.enter_maintenance(ticket.machine, user, f"Ticket #{ticket.pk}")
        log_action(user, "TICKET_START", "MaintenanceRecord", ticket.pk, ticket.machine.brand_id,
                   new_value={"machine_status": "MAINTENANCE"})


def _require_in_progress(ticket):
    if ticket.status != Record.Status.IN_PROGRESS:
        raise PortalError("Phiếu phải đang ở trạng thái 'Đang xử lý' (hãy bắt đầu bảo trì trước).")


def set_item(ticket, item_id, done, user, note=""):
    _check_executor(ticket, user)
    _require_in_progress(ticket)
    item = Item.objects.filter(pk=item_id, record_id=ticket.pk).first()
    if item is None:
        raise PortalError("Mục checklist không tồn tại.")
    if item.phase == Item.Phase.RESULT:
        raise PortalError("Kết quả được ghi bằng chức năng 'Ghi kết quả'.")
    if item.item_text == POST_TEST_TEXT:
        raise PortalError("Mục này chỉ hoàn thành bằng chức năng 'Xịt thử sau bảo trì'.")
    Item.objects.filter(pk=item.pk).update(
        is_done=bool(done), done_by_id=user.pk if done else None, done_at=timezone.now() if done else None,
        note=(note or "").strip()[:500] or None)


def record_result(ticket, user, text):
    _check_executor(ticket, user)
    _require_in_progress(ticket)
    text = (text or "").strip()
    if not text:
        raise PortalError("Cần ghi kết quả sửa chữa (hiện tượng, hành động, linh kiện thay, chi phí).")
    item = Item.objects.filter(record_id=ticket.pk, phase=Item.Phase.RESULT).first()
    if item is None:
        raise PortalError("Phiếu thiếu mục kết quả.")
    Item.objects.filter(pk=item.pk).update(is_done=True, done_by_id=user.pk, done_at=timezone.now(), note=text[:500])
    log_action(user, "TICKET_RESULT", "MaintenanceRecord", ticket.pk, ticket.machine.brand_id, new_value={"result": text[:500]})


def test_spray(ticket, user, slot_id, purpose="diag", passed=True, note=""):
    """
    Xit thu cua ky thuat vien: ghi RIENG (InventoryLog loai DIAGNOSTIC_SPRAY, khong co don hang, khong tinh doanh thu).
    purpose='post': xit thu sau bao tri; neu dat thi tick muc 'Xit thu sau bao tri thanh cong'.
    """
    _check_executor(ticket, user)
    _require_in_progress(ticket)
    machine = Machine.objects.get(pk=ticket.machine_id)
    if machine.status != Machine.Status.MAINTENANCE:
        raise PortalError("Máy phải đang ở chế độ bảo trì để xịt thử.")
    slot = MachineSlot.objects.filter(pk=slot_id, machine_id=machine.pk).first()
    if slot is None:
        raise PortalError("Slot không thuộc máy này.")
    now = timezone.now()
    with transaction.atomic():
        n = MachineSlot.objects.filter(pk=slot.pk, quantity__gt=0).update(quantity=F("quantity") - 1)
        if not n:
            raise PortalError("Slot đã hết nước hoa, không thể xịt thử.")
        after = MachineSlot.objects.get(pk=slot.pk).quantity
        InventoryLog.objects.create(
            user=user, machine_slot=slot, order=None, change_type=InventoryLog.ChangeType.DIAGNOSTIC_SPRAY,
            quantity_before=after + 1, quantity_after=after, change_amount=-1,
            reason=ascii_text(f"Test spray ticket {ticket.pk}", 30), created_at=now)
        machine_services.recompute_slot_status(slot.pk)
        DeviceEvent.objects.create(
            machine_id=machine.pk, event_type=DeviceEvent.EventType.MAINTENANCE_MODE,
            message=ascii_text(f"Diagnostic spray slot {slot.slot_number} ({purpose}) ticket {ticket.pk}", 500), created_at=now)
        if purpose == "post":
            Item.objects.filter(record_id=ticket.pk, item_text=POST_TEST_TEXT).update(
                is_done=bool(passed), done_by_id=user.pk if passed else None,
                done_at=now if passed else None, note=(note or "").strip()[:500] or None)
        log_action(user, "DIAGNOSTIC_SPRAY", "MaintenanceRecord", ticket.pk, machine.brand_id,
                   new_value={"slot": slot.slot_number, "purpose": purpose, "passed": bool(passed), "note": note})


def missing_items(ticket):
    return list(Item.objects.filter(record_id=ticket.pk, is_done=False).exclude(phase=Item.Phase.RESULT))


def complete_ticket(ticket, user):
    """Dong phieu CHI KHI: checklist xong + xit thu sau bao tri dat + da ghi ket qua. Sau do may duoc tra ve hoat dong."""
    _check_executor(ticket, user)
    _require_in_progress(ticket)
    missing = missing_items(ticket)
    if missing:
        raise PortalError(f"Còn {len(missing)} mục checklist chưa hoàn thành (bao gồm test sau bảo trì).")
    result = Item.objects.filter(record_id=ticket.pk, phase=Item.Phase.RESULT).first()
    if result is None or not result.is_done or not (result.note or "").strip():
        raise PortalError("Cần ghi kết quả sửa chữa trước khi đóng phiếu.")
    now = timezone.now()
    with transaction.atomic():
        n = Record.objects.filter(pk=ticket.pk, status=Record.Status.IN_PROGRESS).update(
            status=Record.Status.COMPLETED, completed_at=now)
        if not n:
            raise PortalError("Phiếu vừa được xử lý bởi người khác.")
        if ticket.alert_id:
            try:
                from devices.alert_services import resolve_alert

                alert = Alert.objects.select_related("machine").get(pk=ticket.alert_id)
                if alert.status != Alert.Status.RESOLVED:
                    resolve_alert(alert, user, f"Dong theo phieu bao tri #{ticket.pk}: {result.note}")
            except ImportError:
                pass
        _release_machine(ticket, user, f"Ticket #{ticket.pk} completed")
        log_action(user, "TICKET_COMPLETE", "MaintenanceRecord", ticket.pk, ticket.machine.brand_id,
                   new_value={"result": result.note})


def cancel_ticket(ticket, user, reason):
    reason = (reason or "").strip()
    if not reason:
        raise PortalError("Cần nhập lý do hủy phiếu.")
    with transaction.atomic():
        n = Record.objects.filter(pk=ticket.pk, status__in=OPEN_STATUSES).update(status=Record.Status.CANCELLED)
        if not n:
            raise PortalError("Phiếu đã đóng.")
        _release_machine(ticket, user, f"Ticket #{ticket.pk} cancelled")
        log_action(user, "TICKET_CANCEL", "MaintenanceRecord", ticket.pk, ticket.machine.brand_id, new_value={"reason": reason})


def _release_machine(ticket, user, reason):
    """Tra may ve hoat dong neu khong con phieu mo nao khac."""
    machine = Machine.objects.get(pk=ticket.machine_id)
    if machine.status in (Machine.Status.MAINTENANCE, Machine.Status.ERROR) and not _open_tickets(machine.pk, ticket.pk).exists():
        machine_services.exit_maintenance(machine, user, reason)
>>>>>>> origin/main

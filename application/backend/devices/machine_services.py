"""Dich vu doi trang thai / cau hinh may va slot (Nguoi 2). Moi thay doi deu ghi DeviceEvent + AuditLog."""
from decimal import Decimal

from django.utils import timezone

from accounts.portal_utils import PortalError, ascii_text
from reports.audit import log_action

from .models import DeviceEvent, Machine, MachineSlot


def _event(machine, event_type, message):
    DeviceEvent.objects.create(
        machine_id=machine.pk, event_type=event_type, message=ascii_text(message, 500), created_at=timezone.now()
    )


def set_machine_status(machine, new_status, user, reason="", event_type=DeviceEvent.EventType.MAINTENANCE_MODE):
    """Doi trang thai may (co kiem tra canh tranh). Ham chung, nguoi khac (bao tri) cung dung."""
    old = machine.status
    if old == new_status:
        return machine
    changed = Machine.objects.filter(pk=machine.pk, status=old).update(status=new_status)
    if not changed:
        raise PortalError("Trạng thái máy vừa thay đổi, hãy tải lại trang rồi thử lại.")
    machine.status = new_status
    _event(machine, event_type, f"Status {old} -> {new_status}. {reason}")
    log_action(user, "MACHINE_STATUS_CHANGE", "Machine", machine.pk, machine.brand_id,
               old_value={"status": old}, new_value={"status": new_status, "reason": reason})
    return machine


def disable_machine(machine, user, reason):
    if not (reason or "").strip():
        raise PortalError("Cần nhập lý do khi tắt máy.")
    if machine.status == Machine.Status.DISABLED:
        raise PortalError("Máy đã ở trạng thái tắt.")
    return set_machine_status(machine, Machine.Status.DISABLED, user, reason, DeviceEvent.EventType.SHUTDOWN)


def enable_machine(machine, user, reason=""):
    if machine.status != Machine.Status.DISABLED:
        raise PortalError("Chỉ bật lại được máy đang ở trạng thái tắt.")
    # Chuyen ve OFFLINE: may se tu thanh ONLINE khi gui heartbeat
    return set_machine_status(machine, Machine.Status.OFFLINE, user, reason or "Re-enabled", DeviceEvent.EventType.STARTUP)


def enter_maintenance(machine, user, reason=""):
    if machine.status == Machine.Status.DISABLED:
        raise PortalError("Máy đang bị tắt; hãy bật lại trước khi chuyển sang bảo trì.")
    if machine.status == Machine.Status.MAINTENANCE:
        return machine
    return set_machine_status(machine, Machine.Status.MAINTENANCE, user, reason or "Maintenance mode")


def exit_maintenance(machine, user, reason="", force=False):
    """
    Dua may ra khoi che do bao tri/loi. Quy tac de tai: chi tro lai hoat dong khi checklist + test sau bao tri
    da xong => neu con phieu bao tri chua dong thi tu choi (tru khi force=True, vi du luc dong phieu).
    """
    if machine.status not in (Machine.Status.MAINTENANCE, Machine.Status.ERROR):
        raise PortalError("Máy không ở chế độ bảo trì hoặc lỗi.")
    if not force:
        from maintenance.models import MaintenanceRecord

        open_tickets = MaintenanceRecord.objects.filter(
            machine_id=machine.pk,
            status__in=[MaintenanceRecord.Status.OPEN, MaintenanceRecord.Status.IN_PROGRESS],
        ).count()
        if open_tickets:
            raise PortalError(
                f"Máy còn {open_tickets} phiếu bảo trì chưa hoàn tất. Hoàn tất checklist và test sau bảo trì trước."
            )
    return set_machine_status(machine, Machine.Status.OFFLINE, user, reason or "Back to service")


# ------------------------------------------------------------------ slot
def slot_status_for(quantity, threshold):
    if quantity <= 0:
        return MachineSlot.Status.EMPTY
    if quantity <= threshold:
        return MachineSlot.Status.LOW_STOCK
    return MachineSlot.Status.ACTIVE


def recompute_slot_status(slot_id):
    """Tinh lai trang thai slot theo ton kho (khong dong vao slot dang bi tat thu cong)."""
    slot = MachineSlot.objects.get(pk=slot_id)
    if slot.status == MachineSlot.Status.DISABLED:
        return slot.status
    new = slot_status_for(slot.quantity, slot.low_stock_threshold)
    if new != slot.status:
        MachineSlot.objects.filter(pk=slot_id).update(status=new)
    return new


def set_slot_enabled(slot, enabled, user, reason=""):
    old = slot.status
    if enabled:
        if old != MachineSlot.Status.DISABLED:
            raise PortalError("Slot không ở trạng thái tắt.")
        new = slot_status_for(slot.quantity, slot.low_stock_threshold)
    else:
        if not (reason or "").strip():
            raise PortalError("Cần nhập lý do khi tắt slot.")
        if old == MachineSlot.Status.DISABLED:
            raise PortalError("Slot đã tắt.")
        new = MachineSlot.Status.DISABLED
    MachineSlot.objects.filter(pk=slot.pk).update(status=new)
    slot.status = new
    _event(slot.machine, DeviceEvent.EventType.MAINTENANCE_MODE, f"Slot {slot.slot_number}: {old} -> {new}. {reason}")
    log_action(user, "SLOT_STATUS_CHANGE", "MachineSlot", slot.pk, slot.machine.brand_id,
               old_value={"status": old}, new_value={"status": new, "reason": reason})
    return slot


def configure_slot(slot, user, price_per_spray, low_stock_threshold, spray_duration, reason=""):
    price = Decimal(price_per_spray)
    if price < 0 or price > Decimal("99999999"):
        raise PortalError("Giá không hợp lệ.")
    if not (0 <= low_stock_threshold <= slot.capacity):
        raise PortalError(f"Ngưỡng sắp hết phải từ 0 đến {slot.capacity}.")
    if not (100 <= spray_duration <= 5000):
        raise PortalError("Thời gian xịt phải từ 100 đến 5000 mili giây.")

    old = {"price_per_spray": str(slot.price_per_spray), "low_stock_threshold": slot.low_stock_threshold,
           "spray_duration": slot.spray_duration}
    new = {"price_per_spray": str(price), "low_stock_threshold": low_stock_threshold, "spray_duration": spray_duration}
    if old == new:
        raise PortalError("Không có thay đổi nào.")
    MachineSlot.objects.filter(pk=slot.pk).update(
        price_per_spray=price, low_stock_threshold=low_stock_threshold, spray_duration=spray_duration
    )
    recompute_slot_status(slot.pk)
    new["reason"] = reason
    log_action(user, "SLOT_CONFIG_CHANGE", "MachineSlot", slot.pk, slot.machine.brand_id, old_value=old, new_value=new)
    return slot

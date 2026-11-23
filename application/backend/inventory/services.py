"""Ton kho va refill o muc slot (Nguoi 2). Moi thay doi ghi InventoryLog (loi mot dong/lan) + AuditLog."""
from django.db import transaction
from django.utils import timezone

from accounts.portal_utils import PortalError, ascii_text
from catalog.models import Perfume
from devices.machine_services import recompute_slot_status
from devices.models import Alert, MachineSlot
from devices.services import raise_alert
from reports.audit import log_action

from .models import InventoryLog

ABNORMAL_LOSS_RATIO = 0.05   # hao hut > 5% suc chua (toi thieu 20 lan) so voi uoc tinh => nghi ro ri
ABNORMAL_LOSS_MIN = 20


def _need_reason(reason):
    if not (reason or "").strip():
        raise PortalError("Bắt buộc nhập lý do.")
    return reason.strip()


def _log(user, slot, change_type, before, after, reason):
    return InventoryLog.objects.create(
        user=user, machine_slot=slot, order=None, change_type=change_type,
        quantity_before=before, quantity_after=after, change_amount=after - before,
        reason=ascii_text(reason, 30), created_at=timezone.now(),
    )


def _apply(slot_pk, before, **fields):
    """Cap nhat co dieu kien: chi thanh cong neu ton kho chua bi giao dich khac thay doi."""
    n = MachineSlot.objects.filter(pk=slot_pk, quantity=before).update(**fields)
    if not n:
        raise PortalError("Tồn kho vừa thay đổi do có giao dịch mới. Hãy tải lại trang và thử lại.")


def _close_low_stock_alerts(slot_pk):
    slot = MachineSlot.objects.get(pk=slot_pk)
    if slot.status in (MachineSlot.Status.ACTIVE,):
        Alert.objects.filter(machine_slot_id=slot_pk, alert_type=Alert.Type.LOW_STOCK).exclude(
            status=Alert.Status.RESOLVED
        ).update(status=Alert.Status.RESOLVED, resolved_at=timezone.now())


def refill_slot(slot, user, new_quantity, reason):
    """Nap them nuoc hoa: so luong sau khi nap phai lon hon ton kho hien tai va khong qua suc chua."""
    reason = _need_reason(reason)
    slot = MachineSlot.objects.select_related("machine").get(pk=slot.pk)
    before, cap = slot.quantity, slot.capacity
    if new_quantity <= before:
        raise PortalError("Số lượng sau khi nạp phải lớn hơn tồn kho hiện tại.")
    if new_quantity > cap:
        raise PortalError(f"Vượt sức chứa của chai ({cap}).")
    with transaction.atomic():
        _apply(slot.pk, before, quantity=new_quantity)
        _log(user, slot, InventoryLog.ChangeType.REFILL, before, new_quantity, reason)
        recompute_slot_status(slot.pk)
        _close_low_stock_alerts(slot.pk)
        log_action(user, "REFILL_SLOT", "MachineSlot", slot.pk, slot.machine.brand_id,
                   old_value={"quantity": before}, new_value={"quantity": new_quantity, "reason": reason})


def replace_bottle(slot, user, perfume_id, new_quantity, reason):
    """Thay chai (co the doi mui huong). Mui huong phai thuoc cung thuong hieu va dang hoat dong."""
    reason = _need_reason(reason)
    slot = MachineSlot.objects.select_related("machine", "perfume").get(pk=slot.pk)
    perfume = Perfume.objects.filter(pk=perfume_id, brand_id=slot.machine.brand_id, is_active=True).first()
    if perfume is None:
        raise PortalError("Mùi hương không hợp lệ cho thương hiệu của máy này.")
    if not (1 <= new_quantity <= slot.capacity):
        raise PortalError(f"Số lượng chai mới phải từ 1 đến {slot.capacity}.")
    before = slot.quantity
    with transaction.atomic():
        _apply(slot.pk, before, quantity=new_quantity, perfume_id=perfume.pk)
        _log(user, slot, InventoryLog.ChangeType.REPLACE, before, new_quantity, reason)
        recompute_slot_status(slot.pk)
        _close_low_stock_alerts(slot.pk)
        log_action(user, "REPLACE_BOTTLE", "MachineSlot", slot.pk, slot.machine.brand_id,
                   old_value={"perfume_id": slot.perfume_id, "perfume": slot.perfume.name, "quantity": before},
                   new_value={"perfume_id": perfume.pk, "perfume": perfume.name, "quantity": new_quantity,
                              "reason": reason})


def adjust_inventory(slot, user, measured_quantity, reason):
    """Doi chieu: nhap so luong do duoc (cam bien/can). Chenh lech so voi uoc tinh duoc ghi lai kem ly do."""
    reason = _need_reason(reason)
    slot = MachineSlot.objects.select_related("machine").get(pk=slot.pk)
    before = slot.quantity
    if not (0 <= measured_quantity <= slot.capacity):
        raise PortalError(f"Số lượng đo được phải từ 0 đến {slot.capacity}.")
    if measured_quantity == before:
        raise PortalError("Số đo trùng với ước tính, không cần điều chỉnh.")
    with transaction.atomic():
        _apply(slot.pk, before, quantity=measured_quantity)
        _log(user, slot, InventoryLog.ChangeType.ADJUSTMENT, before, measured_quantity, reason)
        recompute_slot_status(slot.pk)
        log_action(user, "ADJUST_INVENTORY", "MachineSlot", slot.pk, slot.machine.brand_id,
                   old_value={"quantity": before}, new_value={"quantity": measured_quantity, "reason": reason})
        loss = before - measured_quantity
        if loss > max(ABNORMAL_LOSS_MIN, slot.capacity * ABNORMAL_LOSS_RATIO):
            raise_alert(slot.machine_id, Alert.Type.LEAKAGE_SUSPECTED, Alert.Severity.HIGH, slot.pk)
    return before - measured_quantity

from django.db import transaction

from accounts.portal_utils import PortalError
from devices.models import MachineSlot
from reports.audit import log_action

from .models import InventoryLog


@transaction.atomic
def refill_slot(slot, user, amount, reason=""):
    if amount < 1:
        raise PortalError("Số lượng nạp phải lớn hơn 0.")
    slot = MachineSlot.objects.select_for_update().select_related("machine").get(pk=slot.pk)
    before = slot.quantity
    after = min(slot.capacity, before + amount)
    if after == before:
        raise PortalError("Khe đã đầy, không có thay đổi tồn kho.")
    delta = after - before
    slot.quantity = after
    if slot.status != MachineSlot.Status.DISABLED:
        slot.status = MachineSlot.Status.ACTIVE if after > slot.low_stock_threshold else MachineSlot.Status.LOW_STOCK
    slot.save(update_fields=["quantity", "status"])
    InventoryLog.objects.create(
        user=user, machine_slot=slot, change_type=InventoryLog.ChangeType.REFILL,
        quantity_before=before, quantity_after=after, change_amount=delta,
        reason=(reason or "PORTAL_REFILL")[:30],
    )
    log_action(user, "INVENTORY_REFILL", "MachineSlot", slot.pk, slot.machine.brand_id,
               old_value={"quantity": before}, new_value={"quantity": after, "reason": reason})
    return slot, delta

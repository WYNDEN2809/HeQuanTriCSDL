"""Xu ly giao dich cho Operations Manager (Nguoi 4): hoan tien, xac nhan thu cong, thu lai co kiem soat."""
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.portal_utils import PortalError
from devices.services import can_accept_orders
from reports.audit import log_action
from reports.models import AuditLog

from .models import DispenseTransaction, Order, Payment
from .services import _deduct_inventory

MAX_RETRIES = 1  # moi don chi duoc thu lai toi da 1 lan de tranh xit lap lai khong kiem soat


def _brand(order):
    return order.machine_slot.machine.brand_id


def _need(reason):
    reason = (reason or "").strip()
    if not reason:
        raise PortalError("Bắt buộc nhập lý do.")
    return reason


def _paid(order):
    return Payment.objects.filter(order_id=order.pk, status=Payment.Status.SUCCESS).first()


def retry_count(order):
    return AuditLog.objects.filter(action="DISPENSE_RETRY", entity_type="Orders", entity_id=order.pk).count()


def available_actions(order):
    """Cac thao tac hop le cho don o trang thai hien tai (dung de hien form)."""
    actions = []
    dispense = DispenseTransaction.objects.filter(order_id=order.pk).first()
    if order.status in (Order.Status.DISPENSE_FAILED, Order.Status.REVIEW) and _paid(order):
        actions.append(("refund", "Hoàn tiền"))
    if order.status == Order.Status.REVIEW and dispense and dispense.status == DispenseTransaction.Status.UNCERTAIN:
        actions.append(("mark_dispensed", "Xác nhận đã xịt (thủ công)"))
    if (order.status == Order.Status.DISPENSE_FAILED and dispense
            and dispense.status == DispenseTransaction.Status.FAILED and retry_count(order) < MAX_RETRIES):
        actions.append(("retry", "Thử lại xịt (1 lần)"))
    return actions


def refund_order(order, user, reason):
    reason = _need(reason)
    if order.status not in (Order.Status.DISPENSE_FAILED, Order.Status.REVIEW):
        raise PortalError("Chỉ hoàn tiền cho đơn đã trả tiền nhưng xịt lỗi hoặc cần xem xét.")
    payment = _paid(order)
    if payment is None:
        raise PortalError("Đơn này không có thanh toán thành công để hoàn.")
    with transaction.atomic():
        n = Order.objects.filter(
            pk=order.pk, status__in=[Order.Status.DISPENSE_FAILED, Order.Status.REVIEW]
        ).update(status=Order.Status.REFUNDED)
        if not n:
            raise PortalError("Đơn vừa được xử lý bởi người khác. Hãy tải lại trang.")
        Payment.objects.filter(pk=payment.pk, status=Payment.Status.SUCCESS).update(status=Payment.Status.REFUNDED)
        log_action(user, "ORDER_REFUND", "Orders", order.pk, _brand(order),
                   old_value={"order_status": order.status, "payment_status": "SUCCESS"},
                   new_value={"order_status": "REFUNDED", "payment_status": "REFUNDED",
                              "amount": str(order.amount), "reason": reason})


def mark_dispensed(order, user, reason):
    """Nhan vien da kiem tra thuc te may DA xit nhung khong nhan duoc ket qua (UNCERTAIN)."""
    reason = _need(reason)
    dispense = DispenseTransaction.objects.filter(order_id=order.pk).first()
    if (order.status != Order.Status.REVIEW or dispense is None
            or dispense.status != DispenseTransaction.Status.UNCERTAIN):
        raise PortalError("Chỉ xác nhận thủ công cho đơn REVIEW có lệnh xịt không rõ kết quả.")
    now = timezone.now()
    with transaction.atomic():
        n = DispenseTransaction.objects.filter(pk=dispense.pk, status=DispenseTransaction.Status.UNCERTAIN).update(
            status=DispenseTransaction.Status.SUCCESS, executed_at=now, error_message="Manually confirmed by operator")
        m = Order.objects.filter(pk=order.pk, status=Order.Status.REVIEW).update(status=Order.Status.DISPENSED)
        if not n or not m:
            raise PortalError("Đơn vừa được xử lý bởi người khác. Hãy tải lại trang.")
        _deduct_inventory(order.machine_slot, order, now)
        log_action(user, "ORDER_MANUAL_DISPENSED", "Orders", order.pk, _brand(order),
                   old_value={"order_status": "REVIEW", "dispense_status": "UNCERTAIN"},
                   new_value={"order_status": "DISPENSED", "dispense_status": "SUCCESS", "reason": reason})


def retry_dispense(order, user, reason):
    """
    Thu lai co kiem soat. CHI cho don DISPENSE_FAILED co lenh FAILED (chac chan chua xit), toi da 1 lan.
    Don REVIEW (khong ro ket qua) tuyet doi khong thu lai tu dong vi co the da xit.
    Giu nguyen 1 dong DispenseTransaction cho don (UNIQUE OrderID): dat lai thanh PENDING voi lenh moi.
    """
    reason = _need(reason)
    dispense = DispenseTransaction.objects.filter(order_id=order.pk).first()
    if (order.status != Order.Status.DISPENSE_FAILED or dispense is None
            or dispense.status != DispenseTransaction.Status.FAILED or _paid(order) is None):
        raise PortalError("Chỉ thử lại được đơn đã trả tiền có lệnh xịt thất bại (FAILED).")
    if retry_count(order) >= MAX_RETRIES:
        raise PortalError("Đơn này đã thử lại tối đa. Hãy hoàn tiền hoặc kiểm tra máy.")
    slot = order.machine_slot
    if not can_accept_orders(slot.machine):
        raise PortalError("Máy đang không sẵn sàng (offline/bảo trì/lỗi), chưa thể thử lại.")
    if not slot.is_available:
        raise PortalError("Slot không còn khả dụng (hết hàng hoặc đã tắt).")

    now = timezone.now()
    new_command = "CMD-" + uuid.uuid4().hex
    with transaction.atomic():
        n = DispenseTransaction.objects.filter(pk=dispense.pk, status=DispenseTransaction.Status.FAILED).update(
            status=DispenseTransaction.Status.PENDING, command_id=new_command, error_message=None,
            acknowledged_at=None, executed_at=None, created_at=now,
            expires_at=now + timedelta(seconds=settings.DISPENSE_COMMAND_TTL_SECONDS))
        m = Order.objects.filter(pk=order.pk, status=Order.Status.DISPENSE_FAILED).update(status=Order.Status.PENDING)
        if not n or not m:
            raise PortalError("Đơn vừa được xử lý bởi người khác. Hãy tải lại trang.")
        log_action(user, "DISPENSE_RETRY", "Orders", order.pk, _brand(order),
                   old_value={"command_id": dispense.command_id, "error": dispense.error_message},
                   new_value={"command_id": new_command, "reason": reason})
    return new_command


def perform(action, order, user, reason):
    if action == "refund":
        return refund_order(order, user, reason)
    if action == "mark_dispensed":
        return mark_dispensed(order, user, reason)
    if action == "retry":
        return retry_dispense(order, user, reason)
    raise PortalError("Thao tác không hợp lệ.")

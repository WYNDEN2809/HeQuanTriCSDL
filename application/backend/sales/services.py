"""
Nghiep vu ban hang: tao don, xu ly webhook thanh toan, lenh xit, ket qua tu may, het han.

Nguyen tac thiet ke (khop cac business rule cua de tai):
  * Chi backend xac nhan thanh toan (webhook co chu ky) - man hinh kiosk khong phai bang chung.
  * Moi don toi da MOT lenh xit: rang buoc UNIQUE(OrderID) trong DB + kiem tra "compare-and-set".
  * Webhook trung (cung provider_transaction_id) khong bi xu ly lai (idempotent).
  * Don het han/da huy ma van nhan duoc tien -> chuyen REVIEW, KHONG sinh lenh xit.
  * Ket qua khong ro (UNCERTAIN) -> REVIEW, KHONG tu dong xit lan hai.
  * Don chi thanh DISPENSED sau khi may bao thanh cong.
Luu y: moi chuoi luu vao cot varchar deu dung tieng Viet khong dau/ASCII de khong bi mat ky tu.
"""
import json
import secrets
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from devices.models import Alert, Machine, MachineSlot
from devices.services import can_accept_orders, raise_alert
from inventory.models import InventoryLog
from reports.audit import log_action

from .models import DispenseTransaction, Order, Payment
from .security import sign_command, verify_webhook_signature


class OrderError(Exception):
    """Loi nghiep vu khi tao don (thong diep hien thi duoc cho khach)."""


class _Abort(Exception):
    pass


def _brand_id(order):
    return order.machine_slot.machine.brand_id


# ====================================================================== TAO DON
def create_order(machine_id, slot_id):
    try:
        slot = MachineSlot.objects.select_related("machine", "perfume").get(pk=slot_id, machine_id=machine_id)
    except MachineSlot.DoesNotExist:
        raise OrderError("Mùi hương không tồn tại trên máy này.")

    if not can_accept_orders(slot.machine):
        raise OrderError("Máy tạm ngừng phục vụ (mất kết nối hoặc không ở trạng thái hoạt động).")
    if not slot.is_available:
        raise OrderError("Mùi hương này hiện không khả dụng (hết hàng hoặc đã tắt).")

    now = timezone.now()
    reference = f"PAY-{now:%Y%m%d}-{secrets.token_hex(4).upper()}"
    # San pham va gia duoc CHOT tai thoi diem tao don
    order = Order.objects.create(
        machine_slot=slot,
        perfume=slot.perfume,
        unit_price=slot.price_per_spray,
        quantity=1,
        amount=slot.price_per_spray,
        payment_reference=reference,
        currency="VND",
        status=Order.Status.PENDING,
        expires_at=now + timedelta(seconds=settings.ORDER_TTL_SECONDS),
        created_at=now,
    )
    return order


def cancel_order(order):
    """Khach huy don chua thanh toan. Tra ve True neu huy duoc."""
    try:
        with transaction.atomic():
            n = Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(status=Order.Status.CANCELLED)
            if n == 0:
                return False
            if Payment.objects.filter(order_id=order.pk, status=Payment.Status.SUCCESS).exists():
                raise _Abort()  # da tra tien thi khong duoc huy
    except _Abort:
        return False
    return True


def order_stage(order):
    """Trang thai hien thi cho khach, suy ra tu Order + Payment."""
    if order.status == Order.Status.PENDING:
        if Payment.objects.filter(order_id=order.pk, status=Payment.Status.SUCCESS).exists():
            return "DISPENSING"
        return "WAITING_PAYMENT"
    return order.status


# ====================================================================== WEBHOOK THANH TOAN
def process_payment_webhook(raw_body, signature):
    """Xu ly thong bao thanh toan. Tra ve (http_status, dict)."""
    if not verify_webhook_signature(raw_body, signature):
        return 401, {"result": "invalid_signature"}

    try:
        data = json.loads(raw_body.decode("utf-8"))
        reference = data["payment_reference"]
        txn = str(data["provider_transaction_id"])
        amount = Decimal(str(data["amount"]))
        currency = data["currency"]
        status = data["status"]
    except (ValueError, KeyError, TypeError, InvalidOperation, UnicodeDecodeError):
        return 400, {"result": "invalid_payload"}

    if status not in ("SUCCESS", "FAILED"):
        return 400, {"result": "unsupported_status"}
    method = data.get("method") or Payment.Method.VIETQR
    if method not in Payment.Method.values:
        method = Payment.Method.VIETQR

    try:
        order = Order.objects.select_related("machine_slot__machine").get(payment_reference=reference)
    except Order.DoesNotExist:
        return 404, {"result": "unknown_payment_reference"}

    if amount != order.amount or currency != order.currency:
        log_action(None, "PAYMENT_MISMATCH", "Orders", order.pk, _brand_id(order),
                   new_value={"amount": str(amount), "currency": currency, "provider_transaction_id": txn})
        return 400, {"result": "amount_or_currency_mismatch"}

    if Payment.objects.filter(provider_transaction_id=txn).exists():
        return 200, {"result": "duplicate_notification"}

    try:
        return _apply_payment(order, txn, method, status)
    except IntegrityError:
        # hai thong bao cung luc: rang buoc UNIQUE trong DB chan ban thu hai
        return 200, {"result": "duplicate_notification"}


def _apply_payment(order, txn, method, status):
    now = timezone.now()
    brand_id = _brand_id(order)

    with transaction.atomic():
        if status == "FAILED":
            Payment.objects.create(
                order=order, method=method, provider_transaction_id=txn, amount=order.amount,
                status=Payment.Status.FAILED, paid_at=None, created_at=now,
            )
            if not Payment.objects.filter(order_id=order.pk, status=Payment.Status.SUCCESS).exists():
                Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(status=Order.Status.FAILED)
            return 200, {"result": "payment_failed_recorded"}

        # ---- SUCCESS ----
        if Payment.objects.filter(order_id=order.pk, status=Payment.Status.SUCCESS).exists():
            log_action(None, "PAYMENT_DUPLICATE_FOR_ORDER", "Orders", order.pk, brand_id,
                       new_value={"provider_transaction_id": txn})
            return 200, {"result": "ignored_order_already_paid"}

        Payment.objects.create(
            order=order, method=method, provider_transaction_id=txn, amount=order.amount,
            status=Payment.Status.SUCCESS, paid_at=now, created_at=now,
        )

        # Cap nhat "khong doi" de khoa dong don trong giao dich, roi moi quyet dinh co sinh lenh xit hay khong
        still_pending = (
            Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(status=Order.Status.PENDING) == 1
        )
        late = (not still_pending) or now >= order.expires_at
        if late:
            Order.objects.filter(pk=order.pk).exclude(status=Order.Status.DISPENSED).update(status=Order.Status.REVIEW)
            log_action(None, "PAYMENT_AFTER_EXPIRY", "Orders", order.pk, brand_id,
                       new_value={"provider_transaction_id": txn, "note": "paid but order not pending: manual review/refund"})
            return 200, {"result": "paid_after_expiry_needs_review"}

        # Moi don chi co MOT lenh xit (UNIQUE OrderID). Lenh chi duoc tao SAU KHI backend xac nhan thanh toan.
        cmd = DispenseTransaction.objects.create(
            order=order,
            status=DispenseTransaction.Status.PENDING,
            command_id="CMD-" + uuid.uuid4().hex,
            expires_at=now + timedelta(seconds=settings.DISPENSE_COMMAND_TTL_SECONDS),
            created_at=now,
        )
        log_action(None, "PAYMENT_CONFIRMED", "Orders", order.pk, brand_id,
                   new_value={"provider_transaction_id": txn, "amount": str(order.amount)})
        log_action(None, "DISPENSE_COMMAND_CREATED", "DispenseTransaction", cmd.pk, brand_id,
                   new_value={"command_id": cmd.command_id})
    return 200, {"result": "payment_confirmed", "command_id": cmd.command_id}


# ====================================================================== LENH XIT <-> THIET BI
def pending_commands_for(machine):
    now = timezone.now()
    return list(
        DispenseTransaction.objects.filter(
            status=DispenseTransaction.Status.PENDING,
            acknowledged_at__isnull=True,
            expires_at__gt=now,
            order__machine_slot__machine_id=machine.pk,
        ).select_related("order__machine_slot")
    )


def serialize_command(cmd, machine):
    slot = cmd.order.machine_slot
    expires = cmd.expires_at.isoformat()
    return {
        "command_id": cmd.command_id,
        "slot_number": slot.slot_number,
        "spray_duration": slot.spray_duration,
        "expires_at": expires,
        "signature": sign_command(cmd.command_id, machine.serial_number, slot.slot_number, slot.spray_duration, expires),
    }


def _get_command(machine, command_id):
    try:
        return DispenseTransaction.objects.select_related("order__machine_slot__machine").get(
            command_id=command_id, order__machine_slot__machine_id=machine.pk  # lenh gui sai may bi tu choi
        )
    except DispenseTransaction.DoesNotExist:
        return None


def device_ack(machine, command_id):
    cmd = _get_command(machine, command_id)
    if cmd is None:
        return 404, {"result": "unknown_command"}
    now = timezone.now()
    if cmd.expires_at <= now:
        return 410, {"result": "command_expired"}
    updated = DispenseTransaction.objects.filter(
        pk=cmd.pk, status=DispenseTransaction.Status.PENDING, acknowledged_at__isnull=True, expires_at__gt=now
    ).update(acknowledged_at=now)
    if updated == 0:
        return 409, {"result": "already_acknowledged_or_closed"}
    return 200, {"result": "acknowledged"}


def device_report_result(machine, command_id, success, error=""):
    cmd = _get_command(machine, command_id)
    if cmd is None:
        return 404, {"result": "unknown_command"}
    order = cmd.order
    slot = order.machine_slot
    now = timezone.now()
    brand_id = slot.machine.brand_id

    with transaction.atomic():
        if success:
            # May phai xac nhan (ack) truoc khi thuc thi
            updated = DispenseTransaction.objects.filter(
                pk=cmd.pk, status=DispenseTransaction.Status.PENDING, acknowledged_at__isnull=False
            ).update(status=DispenseTransaction.Status.SUCCESS, executed_at=now, error_message=None)
        else:
            updated = DispenseTransaction.objects.filter(
                pk=cmd.pk, status=DispenseTransaction.Status.PENDING
            ).update(status=DispenseTransaction.Status.FAILED, error_message=(error or "Device reported failure")[:500])
        if updated == 0:
            return 409, {"result": "command_closed_or_not_acknowledged"}

        if success:
            Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(status=Order.Status.DISPENSED)
            _deduct_inventory(slot, order, now)
        else:
            Order.objects.filter(pk=order.pk, status=Order.Status.PENDING).update(status=Order.Status.DISPENSE_FAILED)
            raise_alert(slot.machine_id, Alert.Type.DISPENSE_FAILURE, Alert.Severity.HIGH, slot.pk)

        log_action(None, "DISPENSE_RESULT", "DispenseTransaction", cmd.pk, brand_id,
                   new_value={"success": bool(success), "error": error or None})
    return 200, {"result": "recorded"}


def _deduct_inventory(slot, order, now):
    """Chi tru ton kho cua don da xit THANH CONG (xit thu cua ky thuat vien se ghi rieng sau nay)."""
    rows = MachineSlot.objects.filter(pk=slot.pk, quantity__gt=0).update(quantity=F("quantity") - 1)
    if not rows:
        return
    fresh = MachineSlot.objects.get(pk=slot.pk)
    InventoryLog.objects.create(
        user=None, machine_slot=fresh, order=order, change_type=InventoryLog.ChangeType.SALE,
        quantity_before=fresh.quantity + 1, quantity_after=fresh.quantity, change_amount=-1,
        reason="Customer spray", created_at=now,
    )
    if fresh.quantity <= 0:
        MachineSlot.objects.filter(pk=slot.pk).update(status=MachineSlot.Status.EMPTY)
        raise_alert(slot.machine_id, Alert.Type.LOW_STOCK, Alert.Severity.HIGH, slot.pk)
    elif fresh.quantity <= fresh.low_stock_threshold:
        MachineSlot.objects.filter(pk=slot.pk, status=MachineSlot.Status.ACTIVE).update(
            status=MachineSlot.Status.LOW_STOCK
        )
        raise_alert(slot.machine_id, Alert.Type.LOW_STOCK, Alert.Severity.MEDIUM, slot.pk)


# ====================================================================== HET HAN
def expire_stale(now=None):
    """
    * Don chua tra tien va qua han            -> EXPIRED
    * Lenh qua han, may CHUA ack              -> FAILED  (chac chan chua xit)  -> don DISPENSE_FAILED
    * Lenh qua han, may DA ack nhung mat ket qua -> UNCERTAIN -> don REVIEW (khong tu xit lai)
    """
    now = now or timezone.now()

    ids = list(
        Order.objects.filter(status=Order.Status.PENDING, expires_at__lt=now, dispense__isnull=True)
        .exclude(payments__status=Payment.Status.SUCCESS)
        .values_list("pk", flat=True)
    )
    if ids:
        Order.objects.filter(pk__in=ids, status=Order.Status.PENDING).update(status=Order.Status.EXPIRED)

    stale = list(
        DispenseTransaction.objects.filter(status=DispenseTransaction.Status.PENDING, expires_at__lt=now)
        .select_related("order__machine_slot__machine")
    )
    for cmd in stale:
        if cmd.acknowledged_at is None:
            new_status = DispenseTransaction.Status.FAILED
            message = "Command expired before device acknowledgement"
            order_status = Order.Status.DISPENSE_FAILED
        else:
            new_status = DispenseTransaction.Status.UNCERTAIN
            message = "No result received from device before timeout"
            order_status = Order.Status.REVIEW
        with transaction.atomic():
            n = DispenseTransaction.objects.filter(pk=cmd.pk, status=DispenseTransaction.Status.PENDING).update(
                status=new_status, error_message=message
            )
            if n:
                Order.objects.filter(pk=cmd.order_id, status=Order.Status.PENDING).update(status=order_status)
                log_action(None, "DISPENSE_TIMEOUT", "DispenseTransaction", cmd.pk, cmd.order.machine_slot.machine.brand_id,
                           new_value={"status": new_status, "order_status": order_status})

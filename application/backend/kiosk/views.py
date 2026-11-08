"""Giao dien khach hang tren man hinh cam ung kiosk (khong can dang nhap)."""
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from devices.models import Machine
from devices.services import can_accept_orders, machine_connectivity
from sales.models import Order
from sales.services import OrderError, cancel_order, create_order, expire_stale, order_stage

FINAL_STAGES = {"DISPENSED", "DISPENSE_FAILED", "REVIEW", "EXPIRED", "CANCELLED", "FAILED", "REFUNDED"}


def _stage_text(stage, ref):
    return {
        "WAITING_PAYMENT": ("Vui lòng quét mã QR để thanh toán", "Đơn sẽ tự hết hạn nếu chưa thanh toán.", "info"),
        "DISPENSING": ("Đã nhận thanh toán", "Hãy đặt giấy thử hoặc cổ tay vào khu vực xịt. Máy đang xịt...", "primary"),
        "DISPENSED": ("Hoàn tất!", "Hãy cảm nhận mùi hương. Cảm ơn bạn đã trải nghiệm.", "success"),
        "DISPENSE_FAILED": (
            "Máy chưa xịt được",
            f"Bạn đã thanh toán nhưng máy gặp sự cố. Vui lòng ghi lại mã đơn {ref} và liên hệ nhân viên để được hoàn tiền.",
            "danger"),
        "REVIEW": (
            "Giao dịch cần nhân viên kiểm tra",
            f"Vui lòng giữ mã đơn {ref}. Nhân viên sẽ kiểm tra và hoàn tiền nếu cần. Máy sẽ không tự xịt lại.",
            "warning"),
        "EXPIRED": ("Đơn đã hết hạn", f"Nếu bạn đã chuyển tiền, hãy liên hệ nhân viên với mã đơn {ref}.", "secondary"),
        "CANCELLED": ("Đơn đã hủy", "Bạn có thể chọn lại mùi hương.", "secondary"),
        "FAILED": ("Thanh toán không thành công", "Vui lòng thử lại bằng một đơn mới.", "danger"),
        "REFUNDED": ("Đơn đã được hoàn tiền", "Cảm ơn bạn đã thông cảm.", "secondary"),
    }.get(stage, ("Đang xử lý", "", "info"))


def machines(request):
    online = [m for m in Machine.objects.filter(status=Machine.Status.ONLINE).select_related("brand", "location")
              if machine_connectivity(m) == "online"]
    return render(request, "kiosk/machines.html", {"machines": online})


def machine_home(request, machine_id):
    machine = get_object_or_404(Machine.objects.select_related("brand", "location"), pk=machine_id)
    ready = can_accept_orders(machine)
    slots = list(machine.slots.select_related("perfume").order_by("slot_number"))
    for s in slots:
        s.orderable = ready and s.is_available
    return render(request, "kiosk/machine.html", {
        "machine": machine, "slots": slots, "ready": ready, "idle_seconds": settings.KIOSK_IDLE_SECONDS,
    })


@require_POST
def create_order_view(request, machine_id):
    try:
        order = create_order(machine_id, int(request.POST.get("slot_id", "0")))
    except (OrderError, ValueError) as exc:
        messages.error(request, str(exc) if isinstance(exc, OrderError) else "Lựa chọn không hợp lệ.")
        return redirect("kiosk_machine", machine_id=machine_id)
    return redirect("kiosk_order", reference=order.payment_reference)


def order_page(request, reference):
    expire_stale()
    order = get_object_or_404(
        Order.objects.select_related("perfume", "machine_slot__machine__brand", "machine_slot__machine__location"),
        payment_reference=reference,
    )
    pay_url = ""
    if settings.PAYMENT_SANDBOX_ENABLED:
        pay_url = request.build_absolute_uri(reverse("pay_sandbox", args=[reference]))
    return render(request, "kiosk/order.html", {
        "order": order, "machine": order.machine_slot.machine, "pay_url": pay_url,
        "stage": order_stage(order),
    })


def order_status(request, reference):
    expire_stale()
    order = get_object_or_404(Order, payment_reference=reference)
    stage = order_stage(order)
    title, message, tone = _stage_text(stage, reference)
    seconds_left = max(0, int((order.expires_at - timezone.now()).total_seconds()))
    return JsonResponse({
        "stage": stage, "title": title, "message": message, "tone": tone,
        "final": stage in FINAL_STAGES, "expires_in": seconds_left if stage == "WAITING_PAYMENT" else 0,
    })


@require_POST
def cancel_order_view(request, reference):
    order = get_object_or_404(Order.objects.select_related("machine_slot"), payment_reference=reference)
    if not cancel_order(order):
        messages.warning(request, "Không thể hủy đơn này (đã thanh toán hoặc đã xử lý).")
        return redirect("kiosk_order", reference=reference)
    return redirect("kiosk_machine", machine_id=order.machine_slot.machine_id)

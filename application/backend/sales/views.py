import json
import uuid

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Order, Payment
from .security import sign_webhook_body
from .services import order_stage, process_payment_webhook


@csrf_exempt
@require_POST
def payment_webhook(request):
    """Diem nhan thong bao thanh toan tu nha cung cap (co chu ky trong header X-Signature)."""
    code, body = process_payment_webhook(request.body, request.headers.get("X-Signature", ""))
    return JsonResponse(body, status=code)


def pay_sandbox(request, reference):
    """
    Trang thanh toan GIA LAP (thay cho app ngan hang/vi dien tu khi khach quet QR).
    Server tu tao thong bao co chu ky va dua vao CUNG ham xu ly voi webhook that.
    """
    if not settings.PAYMENT_SANDBOX_ENABLED:
        raise Http404
    order = get_object_or_404(
        Order.objects.select_related("perfume", "machine_slot__machine"), payment_reference=reference
    )

    if request.method == "POST":
        outcome = request.POST.get("outcome", "success")
        method = request.POST.get("method", Payment.Method.VIETQR)
        payload = {
            "payment_reference": order.payment_reference,
            "provider_transaction_id": "SBX" + uuid.uuid4().hex,
            "amount": str(order.amount),
            "currency": order.currency,
            "status": "SUCCESS" if outcome == "success" else "FAILED",
            "method": method,
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        code, result = process_payment_webhook(body, sign_webhook_body(body))
        return render(request, "sales/pay_result.html", {
            "order": order, "ok": code == 200 and outcome == "success", "result": result.get("result"),
        })

    return render(request, "sales/pay_sandbox.html", {
        "order": order, "stage": order_stage(order), "methods": Payment.Method.values,
    })

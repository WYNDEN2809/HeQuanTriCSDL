import json
import urllib.error
import urllib.request
import uuid

from django.core.management.base import BaseCommand, CommandError

from sales.models import Order
from sales.security import sign_webhook_body


class Command(BaseCommand):
    help = (
        "Gui thong bao thanh toan (webhook co chu ky) toi server qua HTTP that. "
        "Dung --times 2 de minh hoa 'webhook trung khong tao lenh xit thu hai'."
    )

    def add_arguments(self, parser):
        parser.add_argument("reference", help="Ma payment_reference cua don (vd PAY-20261105-ABCD1234)")
        parser.add_argument("--status", default="SUCCESS", choices=["SUCCESS", "FAILED"])
        parser.add_argument("--times", type=int, default=1, help="So lan gui CUNG MOT thong bao")
        parser.add_argument("--amount", help="Ghi de so tien (de thu truong hop sai tien)")
        parser.add_argument("--bad-signature", action="store_true", help="Gui voi chu ky sai")
        parser.add_argument("--base-url", default="http://127.0.0.1:8000")

    def handle(self, *args, **o):
        try:
            order = Order.objects.get(payment_reference=o["reference"])
        except Order.DoesNotExist:
            raise CommandError("Khong tim thay don voi ma nay.")
        payload = {
            "payment_reference": order.payment_reference,
            "provider_transaction_id": "CLI" + uuid.uuid4().hex,  # giu nguyen cho moi lan gui = cung 1 thong bao
            "amount": o["amount"] or str(order.amount),
            "currency": order.currency,
            "status": o["status"],
            "method": "VIETQR",
        }
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = "bad" if o["bad_signature"] else sign_webhook_body(body)
        for i in range(1, o["times"] + 1):
            req = urllib.request.Request(
                o["base_url"].rstrip("/") + "/api/payments/webhook/", data=body, method="POST",
                headers={"Content-Type": "application/json", "X-Signature": signature},
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    code, text = resp.status, resp.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                code, text = exc.code, exc.read().decode("utf-8")
            self.stdout.write(f"Lan {i}: HTTP {code} {text}")

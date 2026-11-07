import json
from datetime import timedelta
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.test import Client
from django.utils import timezone

from accounts.permissions import scope_queryset
from devices.models import Machine, MachineSlot
from inventory.models import InventoryLog
from sales.models import DispenseTransaction, Order, Payment
from sales.security import device_token, sign_command, sign_webhook_body
from sales.services import OrderError, cancel_order, create_order, expire_stale


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = (
        "Tu kiem thu cac quy tac cot loi (idempotent webhook, 1 don = toi da 1 lenh xit, het han, "
        "ket qua khong ro, tach brand...) tren DATABASE THAT trong 1 giao dich roi ROLLBACK - khong de lai du lieu."
    )

    def handle(self, *args, **opts):
        self.results = []
        try:
            with transaction.atomic():
                self._run()
                raise _Rollback()
        except _Rollback:
            pass

        ok = sum(1 for _, passed, _ in self.results if passed)
        self.stdout.write("")
        for name, passed, detail in self.results:
            mark = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")
            self.stdout.write(f" [{mark}] {name}" + (f"  -> {detail}" if (detail and not passed) else ""))
        total = len(self.results)
        line = f"\n{ok}/{total} kiem tra dat."
        self.stdout.write(self.style.SUCCESS(line) if ok == total else self.style.ERROR(line))
        self.stdout.write("(Toan bo du lieu thu nghiem da duoc rollback; chi cac ID tu tang co the nhay so.)")

    # ---------------------------------------------------------------- tien ich
    def check(self, name, cond, detail=""):
        self.results.append((name, bool(cond), detail))

    def webhook(self, payload, signature=None):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        sig = sign_webhook_body(body) if signature is None else signature
        r = self.client.post("/api/payments/webhook/", data=body, content_type="application/json", HTTP_X_SIGNATURE=sig)
        return r.status_code, r.json()

    def pay(self, order, txn, status="SUCCESS", amount=None):
        return self.webhook({
            "payment_reference": order.payment_reference, "provider_transaction_id": txn,
            "amount": str(amount if amount is not None else order.amount), "currency": order.currency,
            "status": status, "method": "VIETQR",
        })

    def dev(self, method, serial, path, data=None):
        kw = {"HTTP_AUTHORIZATION": "Bearer " + device_token(serial)}
        url = f"/api/device/{serial}/{path}"
        if method == "GET":
            return self.client.get(url, **kw)
        return self.client.post(url, data=json.dumps(data or {}), content_type="application/json", **kw)

    # ---------------------------------------------------------------- kich ban
    def _run(self):
        self.client = Client(HTTP_HOST="localhost")
        now = timezone.now()

        slot = (
            MachineSlot.objects.select_related("machine", "perfume")
            .filter(status=MachineSlot.Status.ACTIVE, quantity__gt=100, perfume__is_active=True)
            .exclude(machine__status=Machine.Status.DISABLED).first()
        )
        machine = slot.machine
        serial = machine.serial_number
        Machine.objects.filter(pk=machine.pk).update(status=Machine.Status.ONLINE, last_seen_at=now)
        qty0 = slot.quantity

        # 1) Tao don: gia & san pham duoc chot
        order = create_order(machine.pk, slot.pk)
        self.check("Tao don thanh cong, trang thai PENDING", order.status == Order.Status.PENDING)
        MachineSlot.objects.filter(pk=slot.pk).update(price_per_spray=F("price_per_spray") + 1000)
        order.refresh_from_db()
        self.check("Gia cua don duoc chot, khong doi khi gia slot doi", order.unit_price == slot.price_per_spray)

        # 2) May offline khong nhan don moi
        Machine.objects.filter(pk=machine.pk).update(status=Machine.Status.OFFLINE)
        try:
            create_order(machine.pk, slot.pk)
            self.check("May OFFLINE khong cho tao don", False)
        except OrderError:
            self.check("May OFFLINE khong cho tao don", True)
        Machine.objects.filter(pk=machine.pk).update(status=Machine.Status.ONLINE, last_seen_at=timezone.now())

        # 3) Webhook: chu ky sai, so tien sai -> bi tu choi, khong sinh lenh xit
        o_sig = create_order(machine.pk, slot.pk)
        code, _ = self.webhook({"payment_reference": o_sig.payment_reference, "provider_transaction_id": "X1",
                                "amount": str(o_sig.amount), "currency": "VND", "status": "SUCCESS"}, signature="sai")
        self.check("Webhook sai chu ky bi tu choi (401)", code == 401)
        code, _ = self.pay(o_sig, "X2", amount=o_sig.amount + 1)
        self.check("Webhook sai so tien bi tu choi (400)", code == 400)
        self.check("Hai truong hop tren khong sinh lenh xit",
                   not DispenseTransaction.objects.filter(order=o_sig).exists())

        # 4) Thanh toan thanh cong -> dung 1 lenh xit; webhook trung khong xu ly lai
        code, body = self.pay(order, "T-MAIN")
        self.check("Webhook hop le -> payment_confirmed", code == 200 and body["result"] == "payment_confirmed", str(body))
        n_pay = Payment.objects.filter(order=order, status=Payment.Status.SUCCESS).count()
        n_cmd = DispenseTransaction.objects.filter(order=order).count()
        self.check("Thanh toan thanh cong -> 1 payment, 1 lenh xit", n_pay == 1 and n_cmd == 1, f"{n_pay}/{n_cmd}")
        code, body = self.pay(order, "T-MAIN")
        self.check("Webhook TRUNG (cung ma giao dich) -> duplicate_notification",
                   code == 200 and body["result"] == "duplicate_notification", str(body))
        code, body = self.pay(order, "T-OTHER")
        self.check("Tra tien lan 2 bang ma khac -> bi bo qua",
                   body["result"] == "ignored_order_already_paid", str(body))
        self.check("Sau do van chi co dung 1 lenh xit",
                   DispenseTransaction.objects.filter(order=order).count() == 1)

        # 5) Thiet bi: lenh, chu ky, ack, ket qua
        r = self.dev("GET", serial, "commands/")
        cmds = r.json().get("commands", []) if r.status_code == 200 else []
        mine = [c for c in cmds if c["command_id"] == DispenseTransaction.objects.get(order=order).command_id]
        self.check("May nhan duoc lenh xit cua don", len(mine) == 1)
        c = mine[0]
        exp_sig = sign_command(c["command_id"], serial, c["slot_number"], c["spray_duration"], c["expires_at"])
        self.check("Lenh xit co chu ky hop le", exp_sig == c["signature"])

        other = Machine.objects.exclude(pk=machine.pk).exclude(status=Machine.Status.DISABLED).first()
        r = self.dev("POST", other.serial_number, f"commands/{c['command_id']}/ack/")
        self.check("May KHAC khong ack duoc lenh (gui sai may bi tu choi)", r.status_code == 404, str(r.status_code))
        r = self.client.post(f"/api/device/{serial}/commands/{c['command_id']}/ack/",
                             HTTP_AUTHORIZATION="Bearer sai-token")
        self.check("Token thiet bi sai bi tu choi (401)", r.status_code == 401)

        r = self.dev("POST", serial, f"commands/{c['command_id']}/result/", {"success": True})
        self.check("Bao thanh cong khi CHUA ack bi tu choi", r.status_code == 409, str(r.status_code))
        r = self.dev("POST", serial, f"commands/{c['command_id']}/ack/")
        self.check("Ack lenh lan 1 thanh cong", r.status_code == 200)
        r = self.dev("POST", serial, f"commands/{c['command_id']}/ack/")
        self.check("Ack lenh lan 2 bi tu choi (lenh trung)", r.status_code == 409)
        r = self.dev("POST", serial, f"commands/{c['command_id']}/result/", {"success": True})
        self.check("May bao xit thanh cong", r.status_code == 200)
        order.refresh_from_db()
        self.check("Don chuyen DISPENSED sau khi may bao thanh cong", order.status == Order.Status.DISPENSED)
        slot.refresh_from_db()
        self.check("Ton kho giam dung 1", slot.quantity == qty0 - 1, f"{qty0} -> {slot.quantity}")
        self.check("Co InventoryLog loai SALE gan voi don",
                   InventoryLog.objects.filter(order=order, change_type="SALE").count() == 1)
        r = self.dev("POST", serial, f"commands/{c['command_id']}/result/", {"success": True})
        slot.refresh_from_db()
        self.check("Bao ket qua lan 2 bi tu choi, ton kho khong bi tru lai",
                   r.status_code == 409 and slot.quantity == qty0 - 1)

        # 6) Thanh toan sau khi het han -> REVIEW, khong xit
        o_late = create_order(machine.pk, slot.pk)
        Order.objects.filter(pk=o_late.pk).update(expires_at=timezone.now() - timedelta(seconds=5))
        o_late.refresh_from_db()
        code, body = self.pay(o_late, "T-LATE")
        o_late.refresh_from_db()
        self.check("Tra tien sau khi don het han -> REVIEW, khong sinh lenh xit",
                   o_late.status == Order.Status.REVIEW and not DispenseTransaction.objects.filter(order=o_late).exists(),
                   str(body))

        # 7) Don da huy van nhan duoc tien -> REVIEW
        o_cancel = create_order(machine.pk, slot.pk)
        self.check("Huy don chua thanh toan duoc", cancel_order(o_cancel) is True)
        self.pay(o_cancel, "T-CANCEL")
        o_cancel.refresh_from_db()
        self.check("Don da huy nhung nhan duoc tien -> REVIEW, khong xit",
                   o_cancel.status == Order.Status.REVIEW and not DispenseTransaction.objects.filter(order=o_cancel).exists())

        # 8) Ket qua khong ro (da ack, mat ket qua) -> UNCERTAIN -> REVIEW, khong xit lai
        o_unc = create_order(machine.pk, slot.pk)
        self.pay(o_unc, "T-UNC")
        self.check("Don da tra tien (cho xit) khong huy duoc", cancel_order(o_unc) is False)
        cmd = DispenseTransaction.objects.get(order=o_unc)
        self.dev("POST", serial, f"commands/{cmd.command_id}/ack/")
        DispenseTransaction.objects.filter(pk=cmd.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        expire_stale()
        cmd.refresh_from_db()
        o_unc.refresh_from_db()
        self.check("Mat ket qua sau ack -> lenh UNCERTAIN, don REVIEW",
                   cmd.status == DispenseTransaction.Status.UNCERTAIN and o_unc.status == Order.Status.REVIEW,
                   f"{cmd.status}/{o_unc.status}")
        r = self.dev("POST", serial, f"commands/{cmd.command_id}/result/", {"success": True})
        self.check("Ket qua den tre sau khi da REVIEW bi tu choi, khong tu xit lai",
                   r.status_code == 409 and DispenseTransaction.objects.filter(order=o_unc).count() == 1)

        # 9) Lenh het han khi may chua ack -> FAILED (chac chan chua xit)
        o_exp = create_order(machine.pk, slot.pk)
        self.pay(o_exp, "T-EXP")
        cmd2 = DispenseTransaction.objects.get(order=o_exp)
        DispenseTransaction.objects.filter(pk=cmd2.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        expire_stale()
        cmd2.refresh_from_db()
        o_exp.refresh_from_db()
        self.check("Lenh het han khi may chua ack -> FAILED, don DISPENSE_FAILED",
                   cmd2.status == DispenseTransaction.Status.FAILED and o_exp.status == Order.Status.DISPENSE_FAILED)

        # 10) Don chua tra tien qua han -> EXPIRED
        o_wait = create_order(machine.pk, slot.pk)
        Order.objects.filter(pk=o_wait.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        expire_stale()
        o_wait.refresh_from_db()
        self.check("Don chua tra tien qua han -> EXPIRED", o_wait.status == Order.Status.EXPIRED)

        # 11) Tach du lieu giua cac brand
        brand_a = machine.brand_id
        req_a = SimpleNamespace(user=SimpleNamespace(is_platform_admin=False), active_brand_id=brand_a)
        scoped = scope_queryset(Order.objects.all(), req_a, "machine_slot__machine__brand_id")
        leaked = scoped.exclude(machine_slot__machine__brand_id=brand_a).exists()
        req_admin = SimpleNamespace(user=SimpleNamespace(is_platform_admin=True), active_brand_id=None)
        all_n = scope_queryset(Order.objects.all(), req_admin, "machine_slot__machine__brand_id").count()
        self.check("User brand A chi thay don cua brand A", not leaked and scoped.count() < all_n,
                   f"{scoped.count()} / {all_n}")
        req_none = SimpleNamespace(user=SimpleNamespace(is_platform_admin=False), active_brand_id=None)
        self.check("User khong thuoc brand nao khong thay don nao",
                   scope_queryset(Order.objects.all(), req_none, "machine_slot__machine__brand_id").count() == 0)

import json
from datetime import date, timedelta
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from devices.models import Machine, MachineSlot
from inventory.models import InventoryLog
from reports.models import AuditLog
from sales import portal_services as svc
from sales import reconciliation as recon
from sales.models import DispenseTransaction, Order, Payment
from sales.security import sign_webhook_body
from sales.services import (create_order, device_ack, device_report_result, expire_stale,
                            process_payment_webhook)


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu xu ly giao dich (Nguoi 4): hoan tien, xac nhan thu cong, thu lai, doi chieu. Co ROLLBACK."

    def handle(self, *args, **opts):
        self.results = []
        try:
            with transaction.atomic():
                self._run()
                raise _Rollback()
        except _Rollback:
            pass
        ok = sum(1 for _, p, _ in self.results if p)
        for name, passed, detail in self.results:
            mark = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")
            self.stdout.write(f" [{mark}] {name}" + (f" -> {detail}" if detail and not passed else ""))
        line = f"\n{ok}/{len(self.results)} kiem tra dat."
        self.stdout.write(self.style.SUCCESS(line) if ok == len(self.results) else self.style.ERROR(line))

    def check(self, name, cond, detail=""):
        self.results.append((name, bool(cond), detail))

    def raises(self, fn, *a):
        try:
            fn(*a)
        except PortalError:
            return True
        return False

    def pay(self, order, txn, amount=None):
        body = json.dumps({"payment_reference": order.payment_reference, "provider_transaction_id": txn,
                           "amount": str(amount if amount is not None else order.amount), "currency": order.currency,
                           "status": "SUCCESS", "method": "VIETQR"}, separators=(",", ":")).encode()
        return process_payment_webhook(body, sign_webhook_body(body))

    def failed_order(self, machine, slot, txn):
        o = create_order(machine.pk, slot.pk)
        self.pay(o, txn)
        cmd = DispenseTransaction.objects.get(order=o)
        device_ack(machine, cmd.command_id)
        device_report_result(machine, cmd.command_id, False, "Actuator timeout")
        o = Order.objects.select_related("machine_slot__machine").get(pk=o.pk)
        return o

    def _run(self):
        now = timezone.now()
        slot = MachineSlot.objects.select_related("machine", "perfume").filter(
            status="ACTIVE", quantity__gt=100, perfume__is_active=True).exclude(machine__status="DISABLED").first()
        machine = slot.machine
        Machine.objects.filter(pk=machine.pk).update(status="ONLINE", last_seen_at=now)
        machine.refresh_from_db()
        ops = BrandMember.objects.filter(brand_id=machine.brand_id, brand_role="OPS_MANAGER").select_related("user").first().user

        # 1) Hoan tien
        o1 = self.failed_order(machine, slot, "TX-A")
        self.check("Don xit loi o trang thai DISPENSE_FAILED", o1.status == Order.Status.DISPENSE_FAILED, o1.status)
        self.check("Hoan tien khong ly do bi tu choi", self.raises(svc.refund_order, o1, ops, ""))
        svc.refund_order(o1, ops, "Khach bi loi may")
        o1.refresh_from_db()
        self.check("Hoan tien -> don REFUNDED", o1.status == Order.Status.REFUNDED)
        self.check("Hoan tien -> thanh toan REFUNDED", Payment.objects.filter(order=o1, status="REFUNDED").exists())
        self.check("Hoan tien ghi audit co ly do", AuditLog.objects.filter(action="ORDER_REFUND", entity_id=o1.pk, user_id=ops.pk).exists())
        self.check("Hoan tien lan 2 bi tu choi", self.raises(svc.refund_order, o1, ops, "lan 2"))

        # 2) Thu lai co kiem soat
        o2 = self.failed_order(machine, slot, "TX-B")
        self.check("Don loi co thao tac 'retry' va 'refund'", {a for a, _ in svc.available_actions(o2)} == {"refund", "retry"})
        old_cmd = DispenseTransaction.objects.get(order=o2).command_id
        Machine.objects.filter(pk=machine.pk).update(status="OFFLINE")
        o2 = Order.objects.select_related("machine_slot__machine").get(pk=o2.pk)
        self.check("May offline thi khong thu lai duoc", self.raises(svc.retry_dispense, o2, ops, "thu"))
        Machine.objects.filter(pk=machine.pk).update(status="ONLINE", last_seen_at=timezone.now())
        o2 = Order.objects.select_related("machine_slot__machine").get(pk=o2.pk)
        new_cmd = svc.retry_dispense(o2, ops, "May da on")
        o2.refresh_from_db()
        d2 = DispenseTransaction.objects.get(order=o2)
        self.check("Thu lai: don PENDING, lenh moi PENDING co command_id khac",
                   o2.status == Order.Status.PENDING and d2.status == "PENDING" and d2.command_id == new_cmd != old_cmd)
        self.check("Van chi co DUNG 1 dong lenh xit cho don", DispenseTransaction.objects.filter(order=o2).count() == 1)
        self.check("Thu lai duoc ghi audit", AuditLog.objects.filter(action="DISPENSE_RETRY", entity_id=o2.pk).exists())
        m2 = Machine.objects.get(pk=machine.pk)
        device_ack(m2, new_cmd)
        device_report_result(m2, new_cmd, False, "Van loi")
        o2 = Order.objects.select_related("machine_slot__machine").get(pk=o2.pk)
        self.check("Loi lan 2 -> khong con 'retry' (toi da 1 lan)", "retry" not in {a for a, _ in svc.available_actions(o2)})
        self.check("Thu lai lan 2 bi tu choi", self.raises(svc.retry_dispense, o2, ops, "lan 2"))

        # 3) Don REVIEW (mat ket qua)
        o3 = create_order(machine.pk, slot.pk)
        self.pay(o3, "TX-C")
        c3 = DispenseTransaction.objects.get(order=o3)
        device_ack(m2, c3.command_id)
        DispenseTransaction.objects.filter(pk=c3.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        expire_stale()
        o3 = Order.objects.select_related("machine_slot__machine").get(pk=o3.pk)
        self.check("Mat ket qua -> REVIEW", o3.status == Order.Status.REVIEW)
        self.check("Don REVIEW KHONG co thao tac thu lai", "retry" not in {a for a, _ in svc.available_actions(o3)})
        self.check("Thu lai don REVIEW bi tu choi", self.raises(svc.retry_dispense, o3, ops, "x"))
        qty = MachineSlot.objects.get(pk=slot.pk).quantity
        svc.mark_dispensed(o3, ops, "Da kiem tra thuc te may da xit")
        o3.refresh_from_db()
        self.check("Xac nhan thu cong -> DISPENSED", o3.status == Order.Status.DISPENSED)
        self.check("Xac nhan thu cong -> lenh SUCCESS", DispenseTransaction.objects.get(order=o3).status == "SUCCESS")
        self.check("Xac nhan thu cong -> tru ton kho 1", MachineSlot.objects.get(pk=slot.pk).quantity == qty - 1)
        self.check("Xac nhan thu cong -> co log SALE", InventoryLog.objects.filter(order=o3, change_type="SALE").exists())
        self.check("Sau khi DISPENSED khong hoan tien duoc", self.raises(svc.refund_order, o3, ops, "x"))

        # 4) Tra tien tre (khong co lenh xit): chi hoan tien
        o4 = create_order(machine.pk, slot.pk)
        Order.objects.filter(pk=o4.pk).update(expires_at=timezone.now() - timedelta(seconds=5))
        self.pay(o4, "TX-D")
        o4 = Order.objects.select_related("machine_slot__machine").get(pk=o4.pk)
        self.check("Tra tien tre -> REVIEW khong co lenh xit", o4.status == "REVIEW" and not DispenseTransaction.objects.filter(order=o4).exists())
        self.check("Khong co lenh UNCERTAIN thi khong xac nhan thu cong duoc", self.raises(svc.mark_dispensed, o4, ops, "x"))
        self.check("Don REVIEW tra tre chi co thao tac hoan tien", [a for a, _ in svc.available_actions(o4)] == ["refund"])
        svc.refund_order(o4, ops, "Tra tien sau khi het han")
        self.check("Hoan tien don tra tre thanh cong", Order.objects.get(pk=o4.pk).status == "REFUNDED")

        # 5) Doi chieu nha cung cap
        req = SimpleNamespace(user=SimpleNamespace(is_platform_admin=False), active_brand_id=machine.brand_id)
        d_from, d_to = date.today() - timedelta(days=1), date.today()
        pays = list(Payment.objects.filter(order__machine_slot__machine__brand_id=machine.brand_id,
                                           created_at__gte=d_from, status__in=["SUCCESS", "REFUNDED"]).select_related("order"))
        rows = [{"txn": p.provider_transaction_id, "amount": p.amount, "status": p.status, "reference": p.order.payment_reference} for p in pays]
        res = recon.reconcile(req, rows, d_from, d_to)
        self.check("Du lieu nha cung cap giong het -> tat ca khop, khong lech",
                   len(res["matched"]) == len(pays) and not any(res[k] for k in res if k != "matched"))
        rows2 = [dict(r) for r in rows]
        rows2[0]["amount"] = rows2[0]["amount"] + 1000
        rows2[1]["status"] = "FAILED"
        dropped = rows2.pop()
        rows2.append({"txn": "KHONG-CO", "amount": rows[0]["amount"], "status": "SUCCESS", "reference": ""})
        res2 = recon.reconcile(req, rows2, d_from, d_to)
        self.check("Phat hien lech so tien", len(res2["amount_mismatch"]) == 1)
        self.check("Phat hien lech trang thai", len(res2["status_mismatch"]) == 1)
        self.check("Phat hien thieu o nha cung cap", any(r["txn"] == dropped["txn"] for r in res2["missing_provider"]))
        self.check("Phat hien thieu o he thong", len(res2["missing_internal"]) == 1)

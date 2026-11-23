from datetime import date, timedelta
import io
from types import SimpleNamespace

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import models, transaction
from django.test import RequestFactory, override_settings
from django.utils import timezone

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from devices import alert_services as svc
from devices.models import Alert, Machine, MachineSlot
from inventory.models import InventoryLog
from inventory.services import refill_slot
from maintenance.models import MaintenanceRecord
from reports.models import AuditLog, Notification
from reports import queries
from reports.queries import _downtime_hours
from reports.exports import csv_response
from sales.models import Order


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu canh bao + bao cao (Nguoi 3) tren DB that, co ROLLBACK."

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

    def add_result(self, name, cond, detail=""):
        self.results.append((name, bool(cond), detail))

    def raises(self, fn, *a):
        try:
            fn(*a)
        except PortalError:
            return True
        return False

    def _run(self):
        machine = Machine.objects.order_by("id").first()
        ops = BrandMember.objects.filter(brand_id=machine.brand_id, brand_role="OPS_MANAGER").select_related("user").first().user
        now = timezone.now()

        period_end = now + timedelta(hours=10)
        downtime = _downtime_hours([
            (1, now - timedelta(hours=2), now + timedelta(hours=5)),
            (1, now + timedelta(hours=3), now + timedelta(hours=7)),
            (2, now + timedelta(hours=4), None),
        ], now, period_end)
        self.add_result("Downtime gop khoang trung lap va gioi han vao ky bao cao", downtime == 13)

        def new_alert(sev="HIGH", age_h=0, atype="DOOR_OPEN"):
            a = Alert.objects.create(machine_id=machine.pk, alert_type=atype, severity=sev, status="OPEN",
                                     created_at=now - timedelta(hours=age_h))
            return Alert.objects.select_related("machine").get(pk=a.pk)

        a = new_alert()
        svc.acknowledge_alert(a, ops)
        a = Alert.objects.select_related("machine").get(pk=a.pk)
        self.add_result("Tiep nhan -> ACKNOWLEDGED co thoi diem", a.status == "ACKNOWLEDGED" and a.acknowledged_at is not None)
        self.add_result("Tiep nhan lan 2 bi tu choi", self.raises(svc.acknowledge_alert, a, ops))
        self.add_result("Dong canh bao khong ghi chu bi tu choi", self.raises(svc.resolve_alert, a, ops, ""))
        svc.resolve_alert(a, ops, "Da dong cua may")
        a = Alert.objects.select_related("machine").get(pk=a.pk)
        self.add_result("Dong canh bao -> RESOLVED co thoi diem", a.status == "RESOLVED" and a.resolved_at is not None)
        self.add_result("Thao tac ghi nguoi chiu trach nhiem vao audit",
                   AuditLog.objects.filter(action="ALERT_RESOLVE", entity_id=a.pk, user_id=ops.pk).exists())
        self.add_result("Mo lai can ly do", self.raises(svc.reopen_alert, a, ops, ""))
        svc.reopen_alert(a, ops, "Van con loi")
        a = Alert.objects.select_related("machine").get(pk=a.pk)
        self.add_result("Mo lai -> OPEN, xoa moc tiep nhan/xu ly",
                   a.status == "OPEN" and a.acknowledged_at is None and a.resolved_at is None)
        self.add_result("Chi mo lai duoc canh bao da xu ly", self.raises(svc.reopen_alert, a, ops, "x"))

        self.add_result("HIGH 5 gio chua xu ly -> qua han", svc.is_overdue(new_alert("HIGH", 5)))
        self.add_result("CRITICAL 30 phut -> chua qua han", not svc.is_overdue(new_alert("CRITICAL", 0)))
        self.add_result("Loc DB 'qua han' khop dung",
                   Alert.objects.filter(svc.overdue_q()).filter(pk__in=[new_alert("LOW", 100).pk]).count() == 1)

        try:
            from maintenance.services import create_ticket_from_alert  # noqa: F401
            tech = BrandMember.objects.filter(brand_id=machine.brand_id, brand_role="TECHNICIAN").select_related("user").first().user
            b = new_alert("MEDIUM")
            ticket = svc.assign_alert(b, ops, tech.pk)
            b = Alert.objects.get(pk=b.pk)
            self.add_result("Giao viec tao phieu bao tri gan voi canh bao", ticket.alert_id == b.pk and ticket.assigned_to_id == tech.pk)
            self.add_result("Giao viec tu dong tiep nhan canh bao", b.status == "ACKNOWLEDGED")
            self.add_result("Giao cho nguoi khong phai ky thuat vien bi tu choi", self.raises(svc.assign_alert, new_alert("LOW"), ops, ops.pk))
            closed = new_alert("LOW")
            svc.resolve_alert(closed, ops, "Da xu ly")
            self.add_result("Khong giao viec cho canh bao da xu ly", self.raises(svc.assign_alert, closed, ops, tech.pk))
            # Exercise the same authenticated portal action used by technicians.
            from maintenance.portal_views import ticket_action
            factory = RequestFactory()
            start_request = factory.post(f"/portal/maintenance/{ticket.pk}/action/", {"action": "start"})
            start_request.user = tech
            start_request.active_brand_id = machine.brand_id
            start_request.brand_role = "TECHNICIAN"
            start_request.session = {}
            start_request._messages = FallbackStorage(start_request)
            ticket_action(start_request, ticket.pk)
            ticket.refresh_from_db()
            self.add_result("Ky thuat vien duoc giao co the bat dau phieu", ticket.status == "IN_PROGRESS")

            complete_request = factory.post(
                f"/portal/maintenance/{ticket.pk}/action/", {"action": "complete", "note": "Da kiem tra va sua xong"}
            )
            complete_request.user = tech
            complete_request.active_brand_id = machine.brand_id
            complete_request.brand_role = "TECHNICIAN"
            complete_request.session = {}
            complete_request._messages = FallbackStorage(complete_request)
            ticket_action(complete_request, ticket.pk)
            ticket.refresh_from_db()
            self.add_result("Hoan tat phieu yeu cau ghi ket qua", ticket.status == "COMPLETED" and ticket.completed_at is not None)
        except ImportError:
            self.add_result("(bo qua) Giao viec: chua co module bao tri cua Nguoi 5", True)

        # ---- tồn kho/nạp lại và audit
        refill_candidate = MachineSlot.objects.filter(machine__brand_id=machine.brand_id, quantity__lt=models.F("capacity")).first()
        if refill_candidate:
            before = refill_candidate.quantity
            slot, delta = refill_slot(refill_candidate, ops, 1, "SELFTEST")
            self.add_result("Nap lai khong vuot suc chua va tao InventoryLog",
                            delta == 1 and slot.quantity == before + 1 and
                            InventoryLog.objects.filter(machine_slot=slot, user=ops,
                                change_type=InventoryLog.ChangeType.REFILL,
                                quantity_before=before, quantity_after=slot.quantity).exists())
            self.add_result("Nap lai ghi audit", AuditLog.objects.filter(
                action="INVENTORY_REFILL", entity_id=slot.pk, user=ops).exists())
        else:
            self.add_result("Co slot de kiem tra nap lai", False, "Khong co slot nao con cho trong database.")

        # ---- thông báo trong portal và leo thang SLA idempotent
        from reports.notifications import notify_alert_created
        alert_for_notification = new_alert("MEDIUM")
        with override_settings(ALERT_EMAIL_NOTIFICATIONS=False):
            notify_alert_created(alert_for_notification)
            created_alert_notice = Notification.objects.filter(
                user=ops, event_key=f"alert:{alert_for_notification.pk}:created"
            ).count()
            notify_alert_created(alert_for_notification)
            duplicate_alert_notice = Notification.objects.filter(
                user=ops, event_key=f"alert:{alert_for_notification.pk}:created"
            ).count()
        self.add_result("Canh bao moi tao thong bao trong portal", created_alert_notice == 1)
        self.add_result("Thong bao canh bao khong bi tao trung", duplicate_alert_notice == created_alert_notice)

        overdue = new_alert("HIGH", 5)
        event_key = f"alert:{overdue.pk}:sla-escalated"
        with override_settings(ALERT_EMAIL_NOTIFICATIONS=False):
            call_command("escalate_alerts", stdout=io.StringIO())
            first_count = Notification.objects.filter(user=ops, event_key=event_key).count()
            call_command("escalate_alerts", stdout=io.StringIO())
            second_count = Notification.objects.filter(user=ops, event_key=event_key).count()
        self.add_result("Qua han SLA tao thong bao trong portal", first_count == 1)
        self.add_result("Chay escalation lap lai khong tao thong bao trung", second_count == first_count)

        # ---- bao cao
        req_all = SimpleNamespace(user=SimpleNamespace(is_platform_admin=True), active_brand_id=None, brand_role="PLATFORM_ADMIN",
                                  GET={"from": "2000-01-01", "to": date.today().isoformat()})
        f = queries.parse_filters(req_all)
        data = queries.dashboard_data(req_all, f)
        raw = Order.objects.filter(status="DISPENSED")
        self.add_result("Doanh thu dashboard = tong don DISPENSED", data["revenue"] == int(sum(o.amount for o in raw)), str(data["revenue"]))
        self.add_result("Ti le xit thanh cong nam trong 0-100", data["dispense_rate"] is None or 0 <= data["dispense_rate"] <= 100)
        self.add_result("Super Admin khong chon brand -> co bang doanh thu theo brand", len(data["platform_brands"]) >= 1)

        req_a = SimpleNamespace(user=SimpleNamespace(is_platform_admin=False), active_brand_id=machine.brand_id,
                                brand_role="BRAND_ADMIN", GET=req_all.GET)
        data_a = queries.dashboard_data(req_a, queries.parse_filters(req_a))
        self.add_result("Dashboard cua brand A nho hon toan nen tang", data_a["orders_total"] < data["orders_total"])
        self.add_result("Brand A khong thay bang doanh thu toan nen tang", data_a["platform_brands"] == [])
        n_a = Order.objects.filter(machine_slot__machine__brand_id=machine.brand_id).count()
        self.add_result("So don cua brand A khop truy van truc tiep", data_a["orders_total"] == n_a, f"{data_a['orders_total']} vs {n_a}")

        resp = csv_response("t", ["a", "b"], [[1, None], ["x", 2], ["=1+1", None]])
        body = resp.content.decode("utf-8")
        self.add_result("Xuat CSV co BOM, tieu de va dong du lieu", body.startswith("\ufeffa,b") and "1," in body)
        self.add_result("Xuat CSV vo hieu hoa noi dung co the bi chay nhu cong thuc", "'=1+1" in body)

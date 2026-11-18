from datetime import date, timedelta
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from devices import alert_services as svc
from devices.models import Alert, Machine
from reports import queries
from reports.queries import _downtime_hours
from reports.exports import csv_response
from reports.models import AuditLog
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

    def check(self, name, cond, detail=""):
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
        self.check("Downtime gop khoang trung lap va gioi han vao ky bao cao", downtime == 13)

        def new_alert(sev="HIGH", age_h=0, atype="DOOR_OPEN"):
            a = Alert.objects.create(machine_id=machine.pk, alert_type=atype, severity=sev, status="OPEN",
                                     created_at=now - timedelta(hours=age_h))
            return Alert.objects.select_related("machine").get(pk=a.pk)

        a = new_alert()
        svc.acknowledge_alert(a, ops)
        a = Alert.objects.select_related("machine").get(pk=a.pk)
        self.check("Tiep nhan -> ACKNOWLEDGED co thoi diem", a.status == "ACKNOWLEDGED" and a.acknowledged_at is not None)
        self.check("Tiep nhan lan 2 bi tu choi", self.raises(svc.acknowledge_alert, a, ops))
        self.check("Dong canh bao khong ghi chu bi tu choi", self.raises(svc.resolve_alert, a, ops, ""))
        svc.resolve_alert(a, ops, "Da dong cua may")
        a = Alert.objects.select_related("machine").get(pk=a.pk)
        self.check("Dong canh bao -> RESOLVED co thoi diem", a.status == "RESOLVED" and a.resolved_at is not None)
        self.check("Thao tac ghi nguoi chiu trach nhiem vao audit",
                   AuditLog.objects.filter(action="ALERT_RESOLVE", entity_id=a.pk, user_id=ops.pk).exists())
        self.check("Mo lai can ly do", self.raises(svc.reopen_alert, a, ops, ""))
        svc.reopen_alert(a, ops, "Van con loi")
        a = Alert.objects.select_related("machine").get(pk=a.pk)
        self.check("Mo lai -> OPEN, xoa moc tiep nhan/xu ly",
                   a.status == "OPEN" and a.acknowledged_at is None and a.resolved_at is None)
        self.check("Chi mo lai duoc canh bao da xu ly", self.raises(svc.reopen_alert, a, ops, "x"))

        self.check("HIGH 5 gio chua xu ly -> qua han", svc.is_overdue(new_alert("HIGH", 5)))
        self.check("CRITICAL 30 phut -> chua qua han", not svc.is_overdue(new_alert("CRITICAL", 0)))
        self.check("Loc DB 'qua han' khop dung",
                   Alert.objects.filter(svc.overdue_q()).filter(pk__in=[new_alert("LOW", 100).pk]).count() == 1)

        try:
            from maintenance.services import create_ticket_from_alert  # noqa: F401
            tech = BrandMember.objects.filter(brand_id=machine.brand_id, brand_role="TECHNICIAN").select_related("user").first().user
            b = new_alert("MEDIUM")
            ticket = svc.assign_alert(b, ops, tech.pk)
            b = Alert.objects.get(pk=b.pk)
            self.check("Giao viec tao phieu bao tri gan voi canh bao", ticket.alert_id == b.pk and ticket.assigned_to_id == tech.pk)
            self.check("Giao viec tu dong tiep nhan canh bao", b.status == "ACKNOWLEDGED")
            self.check("Giao cho nguoi khong phai ky thuat vien bi tu choi", self.raises(svc.assign_alert, new_alert("LOW"), ops, ops.pk))
            closed = new_alert("LOW")
            svc.resolve_alert(closed, ops, "Da xu ly")
            self.check("Khong giao viec cho canh bao da xu ly", self.raises(svc.assign_alert, closed, ops, tech.pk))
        except ImportError:
            self.check("(bo qua) Giao viec: chua co module bao tri cua Nguoi 5", True)

        # ---- bao cao
        req_all = SimpleNamespace(user=SimpleNamespace(is_platform_admin=True), active_brand_id=None, brand_role="PLATFORM_ADMIN",
                                  GET={"from": "2000-01-01", "to": date.today().isoformat()})
        f = queries.parse_filters(req_all)
        data = queries.dashboard_data(req_all, f)
        raw = Order.objects.filter(status="DISPENSED")
        self.check("Doanh thu dashboard = tong don DISPENSED", data["revenue"] == int(sum(o.amount for o in raw)), str(data["revenue"]))
        self.check("Ti le xit thanh cong nam trong 0-100", data["dispense_rate"] is None or 0 <= data["dispense_rate"] <= 100)
        self.check("Super Admin khong chon brand -> co bang doanh thu theo brand", len(data["platform_brands"]) >= 1)

        req_a = SimpleNamespace(user=SimpleNamespace(is_platform_admin=False), active_brand_id=machine.brand_id,
                                brand_role="BRAND_ADMIN", GET=req_all.GET)
        data_a = queries.dashboard_data(req_a, queries.parse_filters(req_a))
        self.check("Dashboard cua brand A nho hon toan nen tang", data_a["orders_total"] < data["orders_total"])
        self.check("Brand A khong thay bang doanh thu toan nen tang", data_a["platform_brands"] == [])
        n_a = Order.objects.filter(machine_slot__machine__brand_id=machine.brand_id).count()
        self.check("So don cua brand A khop truy van truc tiep", data_a["orders_total"] == n_a, f"{data_a['orders_total']} vs {n_a}")

        resp = csv_response("t", ["a", "b"], [[1, None], ["x", 2], ["=1+1", None]])
        body = resp.content.decode("utf-8")
        self.check("Xuat CSV co BOM, tieu de va dong du lieu", body.startswith("\ufeffa,b") and "1," in body)
        self.check("Xuat CSV vo hieu hoa noi dung co the bi chay nhu cong thuc", "'=1+1" in body)

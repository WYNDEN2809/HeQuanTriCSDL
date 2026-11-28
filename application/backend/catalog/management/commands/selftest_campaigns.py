from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.test import Client
from django.utils import timezone

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from catalog import campaign_services as cs
from catalog.models import Campaign, Location, Perfume
from devices.models import Machine, MachineSlot
from reports.models import AuditLog
from sales.models import DispenseTransaction, Order, Payment
from sales.services import create_order, order_stage


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu khuyen mai / dung thu mien phi / gia tam thoi / trang QR san pham tren DB that, co ROLLBACK."

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

    def raises(self, fn, *a, **kw):
        try:
            fn(*a, **kw)
        except PortalError:
            return True
        return False

    def mk(self, brand_id, ctype, value=None, perfume=None, location=None, start=None, end=None, active=True, name="TEST"):
        now = timezone.now()
        return Campaign.objects.create(
            brand_id=brand_id, perfume=perfume, location=location, name=name, campaign_type=ctype, value=value,
            starts_at=start or now - timedelta(hours=1), ends_at=end or now + timedelta(hours=1), is_active=active,
            created_at=now)

    def _run(self):
        now = timezone.now()
        slot = (MachineSlot.objects.select_related("machine", "perfume")
                .filter(status=MachineSlot.Status.ACTIVE, quantity__gt=10, perfume__is_active=True)
                .exclude(machine__status=Machine.Status.DISABLED).first())
        machine, brand_id = slot.machine, slot.machine.brand_id
        Machine.objects.filter(pk=machine.pk).update(status=Machine.Status.ONLINE, last_seen_at=now)
        MachineSlot.objects.filter(pk=slot.pk).update(price_per_spray=Decimal("100000"))
        slot = MachineSlot.objects.select_related("machine", "perfume").get(pk=slot.pk)
        other_brand_slot = (MachineSlot.objects.select_related("machine", "perfume")
                            .exclude(machine__brand_id=brand_id).first())
        admin = BrandMember.objects.filter(brand_id=brand_id, brand_role="BRAND_ADMIN").select_related("user").first()
        Campaign.objects.filter(brand_id=brand_id).update(is_active=False)   # don sach de test khong bi nhieu

        # ---- khong co khuyen mai
        price, c = cs.effective_price(slot, now)
        self.check("Khong co khuyen mai -> gia goc", price == Decimal("100000") and c is None)

        # ---- giam %
        pc = self.mk(brand_id, "PERCENT_OFF", Decimal("20"), name="Giam 20")
        price, c = cs.effective_price(slot, now)
        self.check("Giam 20% cua 100.000 = 80.000", price == Decimal("80000") and c.pk == pc.pk)

        # ---- gia tam thoi re hon -> thang
        tp = self.mk(brand_id, "TEMP_PRICE", Decimal("50000"), name="Gia 50k")
        price, c = cs.effective_price(slot, now)
        self.check("Nhieu chuong trinh -> chon gia thap nhat (khong cong don)", price == Decimal("50000") and c.pk == tp.pk)

        # ---- gia tam thoi cao hon gia goc khong lam tang gia
        Campaign.objects.filter(pk=tp.pk).update(value=Decimal("999999"))
        Campaign.objects.filter(pk=pc.pk).update(is_active=False)
        price, c = cs.effective_price(slot, now)
        self.check("Gia tam thoi cao hon gia goc khong duoc ap dung", price == Decimal("100000") and c is None)
        Campaign.objects.filter(pk=tp.pk).update(is_active=False)

        # ---- pham vi / thoi gian / trang thai
        other_perfume = Perfume.objects.filter(brand_id=brand_id).exclude(pk=slot.perfume_id).first()
        other_loc = Location.objects.filter(brand_id=brand_id).exclude(pk=machine.location_id).first()
        if other_perfume:
            self.mk(brand_id, "PERCENT_OFF", Decimal("50"), perfume=other_perfume)
            self.check("Khuyen mai cua nuoc hoa khac khong ap dung", cs.effective_price(slot, now)[1] is None)
        if other_loc:
            self.mk(brand_id, "PERCENT_OFF", Decimal("50"), location=other_loc)
            self.check("Khuyen mai o dia diem khac khong ap dung", cs.effective_price(slot, now)[1] is None)
        self.mk(brand_id, "PERCENT_OFF", Decimal("50"), start=now - timedelta(days=3), end=now - timedelta(days=1))
        self.mk(brand_id, "PERCENT_OFF", Decimal("50"), start=now + timedelta(days=1), end=now + timedelta(days=2))
        self.mk(brand_id, "PERCENT_OFF", Decimal("50"), active=False)
        self.check("Het han / chua bat dau / dang tat -> khong ap dung", cs.effective_price(slot, now)[1] is None)
        self.mk(brand_id, "PERCENT_OFF", Decimal("30"), perfume=slot.perfume, location=machine.location, name="Dung pham vi")
        self.check("Dung nuoc hoa + dia diem + thoi gian -> ap dung", cs.effective_price(slot, now)[0] == Decimal("70000"))

        # ---- tach brand
        if other_brand_slot:
            self.check("Khuyen mai cua brand nay khong ap dung cho brand khac",
                       cs.effective_price(other_brand_slot, now)[1] is None
                       or cs.effective_price(other_brand_slot, now)[1].brand_id != brand_id)

        # ---- don hang chot gia khuyen mai
        order = create_order(machine.pk, slot.pk)
        self.check("Don chot gia khuyen mai: amount=70.000, unit_price=100.000, co CampaignID",
                   order.amount == Decimal("70000") and order.unit_price == Decimal("100000") and order.campaign_id is not None)
        self.check("Don co gia > 0 van cho thanh toan (chua sinh lenh xit)",
                   order.status == Order.Status.PENDING and not DispenseTransaction.objects.filter(order=order).exists()
                   and order_stage(order) == "WAITING_PAYMENT")
        Campaign.objects.filter(brand_id=brand_id).update(is_active=False)
        order.refresh_from_db()
        self.check("Tat khuyen mai sau do khong doi gia don cu", order.amount == Decimal("70000"))

        # ---- dung thu mien phi
        self.mk(brand_id, "FREE_TRIAL", None, name="Free trial")
        order = create_order(machine.pk, slot.pk)
        pays = list(Payment.objects.filter(order=order))
        self.check("Free-trial: don 0 dong, backend tu xac nhan (Payment SUCCESS, method FREE_TRIAL)",
                   order.amount == 0 and len(pays) == 1 and pays[0].status == Payment.Status.SUCCESS
                   and pays[0].method == "FREE_TRIAL" and pays[0].amount == 0)
        self.check("Free-trial: dung 1 lenh xit, trang thai hien thi DISPENSING",
                   DispenseTransaction.objects.filter(order=order).count() == 1 and order_stage(order) == "DISPENSING")

        # ---- kiem tra dau vao khi luu
        base = dict(name="Test", campaign_type="PERCENT_OFF", value=Decimal("10"), perfume=None, location=None,
                    starts_at=now, ends_at=now + timedelta(days=1), is_active=True)
        self.check("% giam > 100 bi tu choi", self.raises(cs.save_campaign, brand_id, admin.user, {**base, "value": Decimal("150")}))
        self.check("% giam = 0 bi tu choi", self.raises(cs.save_campaign, brand_id, admin.user, {**base, "value": Decimal("0")}))
        self.check("Thieu gia tri bi tu choi", self.raises(cs.save_campaign, brand_id, admin.user, {**base, "value": None}))
        self.check("Ket thuc truoc bat dau bi tu choi",
                   self.raises(cs.save_campaign, brand_id, admin.user, {**base, "ends_at": now - timedelta(hours=1)}))
        foreign = Perfume.objects.exclude(brand_id=brand_id).first()
        self.check("Nuoc hoa cua brand khac bi tu choi",
                   self.raises(cs.save_campaign, brand_id, admin.user, {**base, "perfume": foreign}))
        saved = cs.save_campaign(brand_id, admin.user, {**base, "name": "Ten co dau: Khuyến mãi"})
        self.check("Luu hop le + ghi audit CAMPAIGN_CREATE",
                   saved.pk and AuditLog.objects.filter(action="CAMPAIGN_CREATE", entity_id=saved.pk).exists())
        cs.set_campaign_active(saved, admin.user, False)
        self.check("Tat chuong trinh ghi audit CAMPAIGN_DISABLE",
                   AuditLog.objects.filter(action="CAMPAIGN_DISABLE", entity_id=saved.pk).exists()
                   and not Campaign.objects.get(pk=saved.pk).is_active)

        # ---- kiosk: trang may + trang thong tin QR
        client = Client(HTTP_HOST="localhost")
        r1 = client.get(f"/kiosk/m/{machine.pk}/")
        r2 = client.get(f"/kiosk/info/{slot.pk}/")
        self.check("Man hinh kiosk hien thi (200) va co ma QR san pham", r1.status_code == 200 and b"slot-qr" in r1.content,
                   f"status={r1.status_code}")
        self.check("Trang thong tin san pham (quet QR) mo duoc, khong can dang nhap",
                   r2.status_code == 200 and slot.perfume.name.encode() in r2.content, f"status={r2.status_code}")
        self.check("Trang thong tin cua slot khong ton tai -> 404", client.get("/kiosk/info/99999999/").status_code == 404)

        # ---- portal: Brand Admin xem va mo form khuyen mai
        client.force_login(admin.user)
        p1 = client.get("/portal/catalog/")
        p2 = client.get("/portal/catalog/campaigns/new/")
        self.check("Portal danh muc co muc khuyen mai (200)", p1.status_code == 200 and "Khuyến mãi".encode() in p1.content,
                   f"status={p1.status_code}")
        self.check("Form them khuyen mai mo duoc (200)", p2.status_code == 200, f"status={p2.status_code}")

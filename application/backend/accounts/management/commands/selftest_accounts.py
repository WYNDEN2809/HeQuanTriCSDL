from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts import portal_services as svc
from accounts.models import BrandMember, User
from accounts.portal_utils import PortalError, ascii_text
from catalog import portal_services as cat
from catalog import tenant_services as ten
from catalog.models import Brand, Perfume
from reports.models import AuditLog


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu quan ly nhan vien / tenant / danh muc (Nguoi 1) tren DB that, co ROLLBACK."

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

    def _run(self):
        brand = Brand.objects.order_by("id").first()
        other = Brand.objects.exclude(pk=brand.pk).order_by("id").first()
        admin = BrandMember.objects.filter(brand=brand, brand_role="BRAND_ADMIN").select_related("user").first()
        super_admin = User.objects.filter(role="SUPER_ADMIN").first()

        # ---- nhan vien
        self.check("Mat khau ngan bi tu choi", self.raises(svc.create_member, brand.pk, admin.user, "nv_test", "nv@x.vn", "123", "VIEWER"))
        self.check("Ten dang nhap co dau/khoang trang bi tu choi", self.raises(svc.create_member, brand.pk, admin.user, "nv test", "nv@x.vn", "Abcdef12", "VIEWER"))
        self.check("Vai tro la bi tu choi", self.raises(svc.create_member, brand.pk, admin.user, "nv_test", "nv@x.vn", "Abcdef12", "BOSS"))
        m = svc.create_member(brand.pk, admin.user, "nv_test", "nv@x.vn", "Abcdef12", "VIEWER")
        self.check("Tao nhan vien -> User + BrandMember dung brand", m.brand_id == brand.pk and m.user.check_password("Abcdef12"))
        self.check("Mat khau luu dang hash cua Django (khong luu ro)", m.user.password != "Abcdef12" and "$" in m.user.password)
        self.check("Tao nhan vien ghi audit", AuditLog.objects.filter(action="USER_CREATE", entity_id=m.user_id).exists())
        self.check("Trung ten dang nhap bi tu choi", self.raises(svc.create_member, brand.pk, admin.user, "NV_TEST", "khac@x.vn", "Abcdef12", "VIEWER"))
        self.check("Trung email bi tu choi", self.raises(svc.create_member, brand.pk, admin.user, "nv_test2", "nv@x.vn", "Abcdef12", "VIEWER"))

        self.check("Khong tu doi vai tro cua chinh minh", self.raises(svc.change_role, admin, "VIEWER", admin.user))
        svc.change_role(m, "TECHNICIAN", admin.user)
        m.refresh_from_db()
        self.check("Doi vai tro -> TECHNICIAN", m.brand_role == "TECHNICIAN")
        self.check("Doi vai tro ghi audit truoc/sau", AuditLog.objects.filter(action="ROLE_CHANGE", entity_id=m.pk).exists())
        self.check("Khong ha vai tro Brand Admin cuoi cung", self.raises(svc.change_role, admin, "VIEWER", m.user))
        self.check("Khong go Brand Admin cuoi cung", self.raises(svc.remove_member, admin, m.user))

        # ---- khoa tai khoan + thu hoi phien
        s = SessionStore()
        s["_auth_user_id"] = str(m.user_id)
        s.create()
        self.check("Phien dang nhap ton tai truoc khi khoa", Session.objects.filter(pk=s.session_key).exists())
        svc.set_active(m, False, admin.user)
        m.user.refresh_from_db()
        self.check("Khoa tai khoan -> is_active = False", m.user.is_active is False)
        self.check("Khoa tai khoan -> thu hoi moi phien dang nhap", not Session.objects.filter(pk=s.session_key).exists())
        self.check("Khoa lan 2 bi tu choi", self.raises(svc.set_active, m, False, admin.user))
        svc.set_active(m, True, admin.user)
        m.user.refresh_from_db()
        self.check("Mo khoa tai khoan", m.user.is_active is True)

        s2 = SessionStore()
        s2["_auth_user_id"] = str(m.user_id)
        s2.create()
        pwd = svc.reset_password(m, admin.user)
        m.user.refresh_from_db()
        self.check("Dat lai mat khau: mat khau moi dung, cu sai", m.user.check_password(pwd) and not m.user.check_password("Abcdef12"))
        self.check("Dat lai mat khau thu hoi phien", not Session.objects.filter(pk=s2.session_key).exists())
        self.check("Audit dat lai mat khau KHONG chua mat khau", not AuditLog.objects.filter(action="PASSWORD_RESET", new_value__contains=pwd).exists())

        # nhan vien thuoc 2 brand: khong khoa duoc, chi go
        BrandMember.objects.create(user=m.user, brand=other, brand_role="VIEWER")
        self.check("Tai khoan thuoc nhieu brand khong khoa duoc (chi go)", self.raises(svc.set_active, m, False, admin.user))
        svc.remove_member(m, admin.user)
        self.check("Go khoi brand -> mat BrandMember cua brand do", not BrandMember.objects.filter(user=m.user, brand=brand).exists())
        self.check("Van con thanh vien o brand kia", BrandMember.objects.filter(user=m.user, brand=other).exists())

        # ---- tenant
        t = ten.create_tenant(super_admin, "Thuong Hieu Test", "mo ta", "", "ba_test", "ba@x.vn", "Abcdef12")
        self.check("Tao tenant kem Brand Admin", BrandMember.objects.filter(brand=t, brand_role="BRAND_ADMIN", user__username="ba_test").exists())
        self.check("Trung ten tenant bi tu choi", self.raises(ten.create_tenant, super_admin, "thuong hieu test", "", "", "ba2", "ba2@x.vn", "Abcdef12"))
        ba = BrandMember.objects.get(brand=t, user__username="ba_test")
        s3 = SessionStore()
        s3["_auth_user_id"] = str(ba.user_id)
        s3.create()
        ten.set_tenant_active(t, False, super_admin)
        t.refresh_from_db()
        self.check("Tam ngung tenant -> is_active = False", t.is_active is False)
        self.check("Tam ngung tenant -> thu hoi phien nguoi chi thuoc brand do", not Session.objects.filter(pk=s3.session_key).exists())
        self.check("Tam ngung tenant ghi audit", AuditLog.objects.filter(action="TENANT_SUSPEND", entity_id=t.pk).exists())
        ten.set_tenant_active(t, True, super_admin)

        # ---- danh muc
        p = cat.save_perfume(brand.pk, admin.user, "Hoa Lan Đêm", "Hương hoa lan", 12000, True)
        self.check("Ten nuoc hoa tieng Viet duoc bo dau khi luu (cot VARCHAR)", p.name == "Hoa Lan Dem")
        self.check("Gia am bi tu choi", self.raises(cat.save_perfume, brand.pk, admin.user, "X", "", -1, True))
        self.check("Trung ten nuoc hoa trong brand bi tu choi", self.raises(cat.save_perfume, brand.pk, admin.user, "hoa lan dem", "", 1000, True))
        cat.save_perfume(brand.pk, admin.user, "Hoa Lan Dem", "Hương hoa lan", 15000, True, p)
        self.check("Doi gia ghi audit rieng co gia cu va moi",
                   AuditLog.objects.filter(action="PERFUME_PRICE_CHANGE", entity_id=p.pk, old_value__contains="12000", new_value__contains="15000").exists())
        self.check("Khong thay doi gi bi tu choi", self.raises(cat.save_perfume, brand.pk, admin.user, "Hoa Lan Dem", "Hương hoa lan", 15000, True, Perfume.objects.get(pk=p.pk)))
        loc = cat.save_location(brand.pk, admin.user, "Cửa hàng Quận 1", "1 Lê Lợi", "", True)
        self.check("Ten dia diem duoc bo dau", loc.name == "Cua hang Quan 1")
        self.check("Logo khong phai http(s) bi tu choi", self.raises(cat.update_brand_profile, brand, admin.user, "mo ta", "ftp://x"))
        self.check("ascii_text bo dau tieng Viet", ascii_text("Nạp định kỳ Đ") == "Nap dinh ky D")

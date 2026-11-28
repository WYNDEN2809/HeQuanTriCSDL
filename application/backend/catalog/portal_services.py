"""CRUD danh muc nuoc hoa / dia diem / thong tin thuong hieu (Nguoi 1, Buoc 4)."""
from decimal import Decimal

from accounts.portal_utils import PortalError, ascii_text
from reports.audit import log_action

from .models import Brand, Location, Perfume


def save_perfume(brand_id, user, name, description, price, is_active, perfume=None):
    name = ascii_text((name or "").strip(), 150)   # cot VARCHAR: luu khong dau
    if not name:
        raise PortalError("Tên nước hoa không được để trống.")
    price = Decimal(price)
    if price < 0 or price > Decimal("99999999"):
        raise PortalError("Giá không hợp lệ.")
    if Perfume.objects.filter(brand_id=brand_id, name__iexact=name).exclude(pk=perfume.pk if perfume else None).exists():
        raise PortalError("Thương hiệu đã có nước hoa trùng tên.")
    desc = ascii_text((description or "").strip(), 500) or None
    if perfume is None:
        p = Perfume.objects.create(brand_id=brand_id, name=name, description=desc, is_active=bool(is_active), price_per_spray=price)
        log_action(user, "PERFUME_CREATE", "Perfume", p.pk, brand_id,
                   new_value={"name": name, "price": str(price), "is_active": bool(is_active)})
        return p
    old = {"name": perfume.name, "price": str(perfume.price_per_spray), "is_active": perfume.is_active}
    new = {"name": name, "price": str(price), "is_active": bool(is_active)}
    if old == new and (perfume.description or None) == desc:
        raise PortalError("Không có thay đổi nào.")
    Perfume.objects.filter(pk=perfume.pk).update(name=name, description=desc, is_active=bool(is_active), price_per_spray=price)
    action = "PERFUME_PRICE_CHANGE" if old["price"] != new["price"] else "PERFUME_UPDATE"
    log_action(user, action, "Perfume", perfume.pk, brand_id, old_value=old, new_value=new)
    return perfume


def save_location(brand_id, user, name, address, description, is_active, location=None):
    name = ascii_text((name or "").strip(), 100)
    if not name:
        raise PortalError("Tên địa điểm không được để trống.")
    addr = ascii_text((address or "").strip(), 255) or None
    desc = ascii_text((description or "").strip(), 500) or None
    if location is None:
        loc = Location.objects.create(brand_id=brand_id, name=name, address=addr, description=desc, is_active=bool(is_active))
        log_action(user, "LOCATION_CREATE", "Location", loc.pk, brand_id, new_value={"name": name, "address": addr})
        return loc
    old = {"name": location.name, "address": location.address, "is_active": location.is_active}
    Location.objects.filter(pk=location.pk).update(name=name, address=addr, description=desc, is_active=bool(is_active))
    log_action(user, "LOCATION_UPDATE", "Location", location.pk, brand_id, old_value=old,
               new_value={"name": name, "address": addr, "is_active": bool(is_active)})
    return location


def update_brand_profile(brand, user, description, logo_url):
    desc = ascii_text((description or "").strip(), 500) or None
    logo = (logo_url or "").strip()[:255] or None
    if logo and not logo.lower().startswith(("http://", "https://")):
        raise PortalError("Địa chỉ logo phải bắt đầu bằng http:// hoặc https://")
    old = {"description": brand.description, "logo_url": brand.logo_url}
    Brand.objects.filter(pk=brand.pk).update(description=desc, logo_url=logo)
    log_action(user, "BRAND_PROFILE_UPDATE", "Brand", brand.pk, brand.pk, old_value=old,
               new_value={"description": desc, "logo_url": logo})

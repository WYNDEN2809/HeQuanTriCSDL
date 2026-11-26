"""
Khuyen mai / dung thu mien phi / gia tam thoi (Brand Administrator).

Quy tac:
  * Chi chuong trinh dang bat (is_active), nam trong khoang starts_at..ends_at va dung brand moi duoc ap dung.
  * perfume rong = ap dung moi nuoc hoa cua brand; location rong = ap dung moi dia diem cua brand.
  * Nhieu chuong trinh cung hop le -> chon chuong trinh cho GIA THAP NHAT (khong cong don).
  * Gia cuoi cung duoc CHOT vao don luc tao don (Orders.amount, Orders.CampaignID); doi chuong trinh sau do khong anh huong don cu.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.utils import timezone

from accounts.portal_utils import PortalError, ascii_text
from reports.audit import log_action

from .models import Campaign, Location, Perfume

ZERO = Decimal("0")


def campaign_price(campaign, base_price):
    """Gia sau khi ap dung mot chuong trinh len gia goc (khong am, lam tron den dong)."""
    base = Decimal(base_price)
    if campaign.campaign_type == Campaign.Type.FREE_TRIAL:
        price = ZERO
    elif campaign.campaign_type == Campaign.Type.PERCENT_OFF:
        percent = Decimal(campaign.value or 0)
        price = base * (Decimal(100) - percent) / Decimal(100)
    else:  # TEMP_PRICE
        price = Decimal(campaign.value if campaign.value is not None else base)
    price = price.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(price, ZERO)


def applicable_campaigns(brand_id, perfume_id, location_id, now=None):
    now = now or timezone.now()
    qs = Campaign.objects.filter(
        Q(perfume_id=perfume_id) | Q(perfume__isnull=True),
        Q(location_id=location_id) | Q(location__isnull=True),
        brand_id=brand_id, is_active=True, starts_at__lte=now, ends_at__gt=now,
    )
    return list(qs)


def effective_price(slot, now=None):
    """
    Tra ve (gia_cuoi, campaign|None) cho mot MachineSlot (slot.machine, slot.perfume da duoc nap).
    Neu khong co chuong trinh nao re hon gia goc thi tra ve (gia_goc, None).
    """
    base = Decimal(slot.price_per_spray)
    best_price, best = base, None
    for c in applicable_campaigns(slot.machine.brand_id, slot.perfume_id, slot.machine.location_id, now):
        price = campaign_price(c, base)
        if price < best_price:
            best_price, best = price, c
    return best_price, best


def describe(campaign):
    """Mo ta ngan gon, dung trong portal."""
    if campaign.campaign_type == Campaign.Type.FREE_TRIAL:
        return "Dùng thử miễn phí"
    if campaign.campaign_type == Campaign.Type.PERCENT_OFF:
        return f"Giảm {Decimal(campaign.value or 0):.0f}%"
    return f"Giá tạm thời {Decimal(campaign.value or 0):,.0f} ₫"


def save_campaign(brand_id, user, data, campaign=None):
    """Tao/sua chuong trinh. data: name, campaign_type, value, perfume, location, starts_at, ends_at, is_active."""
    name = ascii_text((data["name"] or "").strip(), 100)
    if not name:
        raise PortalError("Tên chương trình không được để trống.")
    ctype = data["campaign_type"]
    if ctype not in Campaign.Type.values:
        raise PortalError("Loại chương trình không hợp lệ.")
    value = data.get("value")
    if ctype == Campaign.Type.FREE_TRIAL:
        value = None
    elif value is None:
        raise PortalError("Hãy nhập giá trị cho chương trình.")
    else:
        value = Decimal(value)
        if ctype == Campaign.Type.PERCENT_OFF and not (Decimal("1") <= value <= Decimal("100")):
            raise PortalError("Phần trăm giảm phải từ 1 đến 100.")
        if ctype == Campaign.Type.TEMP_PRICE and not (ZERO <= value <= Decimal("99999999")):
            raise PortalError("Giá tạm thời không hợp lệ.")
    starts_at, ends_at = data["starts_at"], data["ends_at"]
    if ends_at <= starts_at:
        raise PortalError("Thời điểm kết thúc phải sau thời điểm bắt đầu.")
    perfume, location = data.get("perfume"), data.get("location")
    # perfume/location phai thuoc DUNG brand nay (chan truyen id cua brand khac)
    if perfume is not None and not Perfume.objects.filter(pk=perfume.pk, brand_id=brand_id).exists():
        raise PortalError("Nước hoa không thuộc thương hiệu này.")
    if location is not None and not Location.objects.filter(pk=location.pk, brand_id=brand_id).exists():
        raise PortalError("Địa điểm không thuộc thương hiệu này.")

    fields = dict(name=name, campaign_type=ctype, value=value, perfume=perfume, location=location,
                  starts_at=starts_at, ends_at=ends_at, is_active=bool(data.get("is_active")))
    snapshot = lambda c: {  # noqa: E731
        "name": c.name, "type": c.campaign_type, "value": str(c.value) if c.value is not None else None,
        "perfume_id": c.perfume_id, "location_id": c.location_id,
        "starts_at": str(c.starts_at), "ends_at": str(c.ends_at), "is_active": c.is_active,
    }
    if campaign is None:
        obj = Campaign.objects.create(brand_id=brand_id, created_at=timezone.now(), **fields)
        log_action(user, "CAMPAIGN_CREATE", "Campaign", obj.pk, brand_id, new_value=snapshot(obj))
        return obj
    old = snapshot(campaign)
    for k, v in fields.items():
        setattr(campaign, k, v)
    campaign.save()
    log_action(user, "CAMPAIGN_UPDATE", "Campaign", campaign.pk, brand_id, old_value=old, new_value=snapshot(campaign))
    return campaign


def set_campaign_active(campaign, user, active):
    if campaign.is_active == bool(active):
        raise PortalError("Chương trình đã ở trạng thái này.")
    Campaign.objects.filter(pk=campaign.pk).update(is_active=bool(active))
    log_action(user, "CAMPAIGN_ENABLE" if active else "CAMPAIGN_DISABLE", "Campaign", campaign.pk, campaign.brand_id,
               old_value={"is_active": campaign.is_active}, new_value={"is_active": bool(active)})

"""Quan ly thuong hieu (tenant) - chi Platform Super Administrator (Nguoi 1, Buoc 4)."""
from django.db import transaction

from accounts import portal_services as people
from accounts.models import BrandMember
from accounts.portal_utils import PortalError, ascii_text
from reports.audit import log_action

from .models import Brand


def _clean_name(name, exclude_pk=None):
    name = ascii_text((name or "").strip(), 100)
    if not name:
        raise PortalError("Tên thương hiệu không được để trống.")
    if Brand.objects.filter(name__iexact=name).exclude(pk=exclude_pk).exists():
        raise PortalError("Tên thương hiệu đã tồn tại.")
    return name


def create_tenant(by_user, name, description, logo_url, admin_username, admin_email, admin_password):
    name = _clean_name(name)
    with transaction.atomic():
        brand = Brand.objects.create(name=name, description=ascii_text(description, 500) or None,
                                     logo_url=(logo_url or "").strip()[:255] or None, is_active=True)
        people.create_member(brand.pk, by_user, admin_username, admin_email, admin_password, "BRAND_ADMIN")
        log_action(by_user, "TENANT_CREATE", "Brand", brand.pk, brand.pk, new_value={"name": name})
    return brand


def update_tenant(brand, by_user, name, description, logo_url):
    name = _clean_name(name, brand.pk)
    old = {"name": brand.name, "description": brand.description, "logo_url": brand.logo_url}
    Brand.objects.filter(pk=brand.pk).update(name=name, description=ascii_text(description, 500) or None,
                                             logo_url=(logo_url or "").strip()[:255] or None)
    log_action(by_user, "TENANT_UPDATE", "Brand", brand.pk, brand.pk, old_value=old, new_value={"name": name})


def set_tenant_active(brand, active, by_user):
    """Tam ngung / kich hoat lai thuong hieu. Tam ngung: nguoi dung chi thuoc brand nay bi dang xuat ngay."""
    if bool(brand.is_active) == bool(active):
        raise PortalError("Thương hiệu đã ở trạng thái này.")
    Brand.objects.filter(pk=brand.pk).update(is_active=bool(active))
    revoked = 0
    if not active:
        for m in BrandMember.objects.filter(brand_id=brand.pk):
            if not BrandMember.objects.filter(user_id=m.user_id).exclude(brand_id=brand.pk).exists():
                revoked += people.revoke_user_sessions(m.user_id)
    log_action(by_user, "TENANT_ACTIVATE" if active else "TENANT_SUSPEND", "Brand", brand.pk, brand.pk,
               old_value={"is_active": not active}, new_value={"is_active": bool(active), "sessions_revoked": revoked})

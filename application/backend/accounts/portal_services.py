"""Quan ly nhan vien va vai tro trong thuong hieu (Nguoi 1, Buoc 4)."""
import secrets
import string

from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from catalog.models import Brand
from reports.audit import log_action

from .models import BrandMember, User
from .portal_utils import PortalError

ROLE_VALUES = BrandMember.BrandRole.values


def generate_temp_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length)) + "!1"


def revoke_user_sessions(user_id):
    """Cham dut moi phien dang nhap cua tai khoan (khi khoa tai khoan / doi mat khau / bi go khoi brand)."""
    n = 0
    for s in Session.objects.filter(expire_date__gte=timezone.now()):
        try:
            if s.get_decoded().get("_auth_user_id") == str(user_id):
                s.delete()
                n += 1
        except Exception:
            continue
    return n


def _admin_count(brand_id):
    return BrandMember.objects.filter(brand_id=brand_id, brand_role="BRAND_ADMIN", user__is_active=True).count()


def _validate_new_user(username, email, password):
    username = (username or "").strip()
    email = (email or "").strip().lower()
    if not username or not username.replace("_", "").replace(".", "").isalnum() or not username.isascii():
        raise PortalError("Tên đăng nhập chỉ gồm chữ không dấu, số, dấu chấm và gạch dưới.")
    if len(password or "") < 8:
        raise PortalError("Mật khẩu phải có ít nhất 8 ký tự.")
    if User.objects.filter(username__iexact=username).exists():
        raise PortalError("Tên đăng nhập đã tồn tại.")
    if User.objects.filter(email__iexact=email).exists():
        raise PortalError("Email đã được sử dụng.")
    return username, email


def create_member(brand_id, by_user, username, email, password, brand_role):
    if brand_role not in ROLE_VALUES:
        raise PortalError("Vai trò không hợp lệ.")
    if not Brand.objects.filter(pk=brand_id).exists():
        raise PortalError("Thương hiệu không tồn tại.")
    username, email = _validate_new_user(username, email, password)
    with transaction.atomic():
        user = User.objects.create_user(username, email, password)
        member = BrandMember.objects.create(user=user, brand_id=brand_id, brand_role=brand_role)
        log_action(by_user, "USER_CREATE", "User", user.pk, brand_id,
                   new_value={"username": username, "email": email, "brand_role": brand_role})
    return member


def change_role(member, new_role, by_user):
    if new_role not in ROLE_VALUES:
        raise PortalError("Vai trò không hợp lệ.")
    if member.user_id == by_user.pk:
        raise PortalError("Không thể tự đổi vai trò của chính mình.")
    if new_role == member.brand_role:
        raise PortalError("Vai trò không thay đổi.")
    if member.brand_role == "BRAND_ADMIN" and _admin_count(member.brand_id) <= 1:
        raise PortalError("Thương hiệu phải còn ít nhất một Brand Administrator.")
    old = member.brand_role
    BrandMember.objects.filter(pk=member.pk).update(brand_role=new_role)
    log_action(by_user, "ROLE_CHANGE", "BrandMember", member.pk, member.brand_id,
               old_value={"user": member.user.username, "brand_role": old}, new_value={"brand_role": new_role})


def remove_member(member, by_user):
    if member.user_id == by_user.pk:
        raise PortalError("Không thể tự gỡ chính mình khỏi thương hiệu.")
    if member.brand_role == "BRAND_ADMIN" and _admin_count(member.brand_id) <= 1:
        raise PortalError("Thương hiệu phải còn ít nhất một Brand Administrator.")
    user_id, brand_id, username = member.user_id, member.brand_id, member.user.username
    member_pk, role = member.pk, member.brand_role   # delete() se dat member.pk = None
    with transaction.atomic():
        member.delete()
        log_action(by_user, "MEMBER_REMOVE", "BrandMember", member_pk, brand_id,
                   old_value={"user": username, "brand_role": role})
        if not BrandMember.objects.filter(user_id=user_id).exists():
            revoke_user_sessions(user_id)


def set_active(member, active, by_user):
    """Kich hoat / khoa tai khoan. Chi ap dung duoc khi tai khoan chi thuoc thuong hieu nay."""
    user = member.user
    if user.pk == by_user.pk:
        raise PortalError("Không thể tự khóa tài khoản của chính mình.")
    if BrandMember.objects.filter(user_id=user.pk).exclude(brand_id=member.brand_id).exists():
        raise PortalError("Tài khoản thuộc nhiều thương hiệu: hãy gỡ khỏi thương hiệu này thay vì khóa.")
    if bool(user.is_active) == bool(active):
        raise PortalError("Tài khoản đã ở trạng thái này.")
    if not active and member.brand_role == "BRAND_ADMIN" and _admin_count(member.brand_id) <= 1:
        raise PortalError("Thương hiệu phải còn ít nhất một Brand Administrator đang hoạt động.")
    User.objects.filter(pk=user.pk).update(is_active=bool(active))
    revoked = revoke_user_sessions(user.pk) if not active else 0
    log_action(by_user, "ACCOUNT_ACTIVATE" if active else "ACCOUNT_DEACTIVATE", "User", user.pk, member.brand_id,
               old_value={"is_active": not active}, new_value={"is_active": bool(active), "sessions_revoked": revoked})


def reset_password(member, by_user, new_password=None):
    user = member.user
    if user.is_platform_admin:
        raise PortalError("Không thể đặt lại mật khẩu của Super Admin tại đây.")
    pwd = new_password or generate_temp_password()
    if len(pwd) < 8:
        raise PortalError("Mật khẩu phải có ít nhất 8 ký tự.")
    user.set_password(pwd)
    User.objects.filter(pk=user.pk).update(password=user.password)
    revoked = revoke_user_sessions(user.pk)
    log_action(by_user, "PASSWORD_RESET", "User", user.pk, member.brand_id, new_value={"sessions_revoked": revoked})
    return pwd

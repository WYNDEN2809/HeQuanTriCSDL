"""
Cong cu phan quyen da thuong hieu (multi-tenant).

Quy tac cot loi cua de tai: nguoi dung brand nay KHONG duoc thay du lieu brand khac.
=> Moi truy van lay du lieu nghiep vu deu phai di qua scope_queryset().
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def scope_queryset(qs, request, brand_field="brand_id"):
    """
    Loc queryset theo brand cua nguoi dung.

    brand_field la duong dan toi cot BrandID, vi du:
      Machine           -> "brand_id"
      MachineSlot       -> "machine__brand_id"
      Order             -> "machine_slot__machine__brand_id"
    """
    user = request.user
    if user.is_platform_admin:
        if request.active_brand_id:
            return qs.filter(**{brand_field: request.active_brand_id})
        return qs
    if not request.active_brand_id:
        return qs.none()
    return qs.filter(**{brand_field: request.active_brand_id})


def brand_role_required(*roles):
    """Decorator cho view: chi cho phep cac brand_role duoc liet ke (super admin luon duoc)."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not user.is_platform_admin and request.brand_role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


class BrandScopedQuerysetMixin:
    """Mixin cho class-based view: tu dong loc get_queryset() theo brand."""

    brand_field = "brand_id"

    def get_queryset(self):
        return scope_queryset(super().get_queryset(), self.request, self.brand_field)

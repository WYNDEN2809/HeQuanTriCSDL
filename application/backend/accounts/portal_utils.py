<<<<<<< HEAD
=======
<<<<<<< HEAD
"""Shared helpers for brand-scoped portal pages."""

from django.core.paginator import Paginator

=======
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89
"""Tien ich dung chung cho cac man hinh portal."""
import unicodedata

from django import forms
from django.core.paginator import Paginator

from . import roles
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89
from .permissions import scope_queryset


class PortalError(Exception):
<<<<<<< HEAD
=======
<<<<<<< HEAD
    """An expected validation or workflow error safe to show to portal users."""


def scoped_for_role(request, queryset, brand_field, platform_scope_field=None):
    """Scope rows to the active brand (the view decorator enforces role access)."""
    return scope_queryset(queryset, request, brand_field)
=======
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89
    """Loi nghiep vu co thong diep hien thi duoc cho nguoi dung."""


def ascii_text(value, max_len=None):
    """
    Bo dau tieng Viet de luu vao cac cot VARCHAR (cot VARCHAR se mat dau thanh '?').
    Noi dung day du, co dau, nen luu o AuditLog (cot NVARCHAR).
    """
    if value is None:
        return None
    text = str(value).replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.encode("ascii", "ignore").decode("ascii")
    return text[:max_len] if max_len else text
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89


def paginate(request, queryset, per_page=25):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))
<<<<<<< HEAD
=======
<<<<<<< HEAD
=======
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89


def require_brand_context(request):
    """Cac thao tac tao/sua can biet brand: Super Admin phai chon 1 thuong hieu o thanh tren cung."""
    if not request.active_brand_id:
        raise PortalError("Hãy chọn một thương hiệu ở thanh trên cùng trước khi thao tác.")
    return request.active_brand_id


def technician_machine_ids(user):
    """May dang co phieu bao tri chua dong duoc giao cho ky thuat vien nay."""
    from maintenance.models import MaintenanceRecord

    return list(
        MaintenanceRecord.objects.filter(
            assigned_to_id=user.pk,
            status__in=[MaintenanceRecord.Status.OPEN, MaintenanceRecord.Status.IN_PROGRESS],
        ).values_list("machine_id", flat=True).distinct()
    )


def scoped_for_role(request, queryset, brand_field, machine_lookup=None):
    """
    Loc theo brand (scope_queryset). Voi Technician: chi thay du lieu cua may duoc giao phieu bao tri.
    machine_lookup la duong dan loc theo may, vi du 'id__in' (Machine) hoac 'machine_id__in' (Alert).
    """
    qs = scope_queryset(queryset, request, brand_field)
    if machine_lookup and not request.user.is_platform_admin and request.brand_role == roles.TECH:
        qs = qs.filter(**{machine_lookup: technician_machine_ids(request.user)})
    return qs


def style_form(form):
    """Gan class Bootstrap cho moi truong cua form."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs.setdefault("class", "form-check-input")
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            widget.attrs.setdefault("class", "form-select")
        else:
            widget.attrs.setdefault("class", "form-control")
    return form


class StyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_form(self)


class PasswordConfirmForm(StyledForm):
    """Xac nhan lai mat khau cho thao tac nhay cam (hoan tien, xit thu, cau hinh lai...)."""

    confirm_password = forms.CharField(
        label="Nhập lại mật khẩu của bạn để xác nhận",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_confirm_password(self):
        pwd = self.cleaned_data["confirm_password"]
        if self.user is None or not self.user.check_password(pwd):
            raise forms.ValidationError("Mật khẩu không đúng.")
        return pwd
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts import portal_services as people
from accounts.models import BrandMember
from accounts.permissions import brand_role_required
from accounts.portal_forms import MemberCreateForm
from accounts.portal_utils import PortalError

from . import tenant_services as svc
from .models import Brand
from .portal_forms import TenantCreateForm, TenantForm


@brand_role_required()   # khong vai tro nao => chi Super Admin
def tenant_list(request):
    brands = Brand.objects.annotate(
        n_members=Count("members", distinct=True), n_machines=Count("machines", distinct=True),
        n_perfumes=Count("perfumes", distinct=True), n_locations=Count("locations", distinct=True),
    ).order_by("name")
    return render(request, "portal/tenants/list.html", {"brands": brands})


@brand_role_required()
def tenant_create(request):
    form = TenantCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            brand = svc.create_tenant(request.user, d["name"], d["description"], d["logo_url"],
                                      d["admin_username"], d["admin_email"], d["admin_password"])
            messages.success(request, f"Đã tạo thương hiệu {brand.name} và tài khoản Brand Admin.")
            return redirect("tenant_detail", pk=brand.pk)
        except PortalError as exc:
            messages.error(request, str(exc))
    return render(request, "portal/tenants/create.html", {"form": form})


@brand_role_required()
def tenant_detail(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    form = TenantForm(initial={"name": brand.name, "description": brand.description, "logo_url": brand.logo_url})
    return render(request, "portal/tenants/detail.html", {
        "brand": brand, "form": form, "admin_form": MemberCreateForm(initial={"brand_role": "BRAND_ADMIN"}),
        "admins": BrandMember.objects.filter(brand=brand, brand_role="BRAND_ADMIN").select_related("user"),
        "n_members": BrandMember.objects.filter(brand=brand).count(),
    })


@brand_role_required()
@require_POST
def tenant_action(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    action = request.POST.get("action", "")
    try:
        if action == "update":
            f = TenantForm(request.POST)
            if not f.is_valid():
                raise PortalError("Dữ liệu không hợp lệ.")
            svc.update_tenant(brand, request.user, f.cleaned_data["name"], f.cleaned_data["description"], f.cleaned_data["logo_url"])
        elif action in ("suspend", "activate"):
            svc.set_tenant_active(brand, action == "activate", request.user)
        elif action == "add_admin":
            f = MemberCreateForm(request.POST)
            if not f.is_valid():
                raise PortalError("Dữ liệu tài khoản không hợp lệ.")
            d = f.cleaned_data
            people.create_member(brand.pk, request.user, d["username"], d["email"], d["password"], "BRAND_ADMIN")
        else:
            raise PortalError("Thao tác không hợp lệ.")
        messages.success(request, "Đã cập nhật thương hiệu.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("tenant_detail", pk=pk)

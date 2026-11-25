from django.contrib import messages
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import PortalError, require_brand_context

from . import campaign_services as camp_svc
from . import portal_services as svc
from .models import Brand, Campaign, Location, Perfume
from .portal_forms import BrandProfileForm, CampaignForm, LocationForm, PerfumeForm


@brand_role_required(*roles.CATALOG_VIEW)
def catalog_home(request):
    brand = Brand.objects.filter(pk=request.active_brand_id).first()
    campaigns = list(scope_queryset(Campaign.objects.select_related("brand", "perfume", "location"), request, "brand_id")
                     .order_by("-starts_at")[:100])
    now = timezone.now()
    for c in campaigns:
        c.summary = camp_svc.describe(c)
        c.running = c.is_active and c.starts_at <= now < c.ends_at
    return render(request, "portal/catalog/home.html", {
        "campaigns": campaigns,
        "perfumes": scope_queryset(Perfume.objects.select_related("brand"), request, "brand_id").order_by("brand_id", "name"),
        "locations": scope_queryset(Location.objects.select_related("brand"), request, "brand_id").order_by("brand_id", "name"),
        "brand": brand, "can_manage": roles.can(request, roles.CATALOG_MANAGE),
        "show_brand": not request.active_brand_id,
    })


def _form_page(request, form, title, back="catalog_home"):
    return render(request, "portal/catalog/form.html", {"form": form, "title": title})


@brand_role_required(*roles.CATALOG_MANAGE)
def perfume_edit(request, pk=None):
    obj = get_object_or_404(scope_queryset(Perfume.objects.all(), request, "brand_id"), pk=pk) if pk else None
    initial = {"name": obj.name, "description": obj.description, "price_per_spray": obj.price_per_spray,
               "is_active": obj.is_active} if obj else None
    form = PerfumeForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            brand_id = obj.brand_id if obj else require_brand_context(request)
            svc.save_perfume(brand_id, request.user, d["name"], d["description"], d["price_per_spray"], d["is_active"], obj)
            messages.success(request, "Đã lưu nước hoa.")
            return redirect("catalog_home")
        except PortalError as exc:
            messages.error(request, str(exc))
    return _form_page(request, form, "Sửa nước hoa" if obj else "Thêm nước hoa")


@brand_role_required(*roles.CATALOG_MANAGE)
def location_edit(request, pk=None):
    obj = get_object_or_404(scope_queryset(Location.objects.all(), request, "brand_id"), pk=pk) if pk else None
    initial = {"name": obj.name, "address": obj.address, "description": obj.description, "is_active": obj.is_active} if obj else None
    form = LocationForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            brand_id = obj.brand_id if obj else require_brand_context(request)
            svc.save_location(brand_id, request.user, d["name"], d["address"], d["description"], d["is_active"], obj)
            messages.success(request, "Đã lưu địa điểm.")
            return redirect("catalog_home")
        except PortalError as exc:
            messages.error(request, str(exc))
    return _form_page(request, form, "Sửa địa điểm" if obj else "Thêm địa điểm")


@brand_role_required(*roles.CATALOG_MANAGE)
def brand_profile(request):
    try:
        require_brand_context(request)
    except PortalError as exc:
        messages.error(request, str(exc))
        return redirect("catalog_home")
    brand = get_object_or_404(Brand, pk=request.active_brand_id)
    form = BrandProfileForm(request.POST or None, initial={"description": brand.description, "logo_url": brand.logo_url})
    if request.method == "POST" and form.is_valid():
        try:
            svc.update_brand_profile(brand, request.user, form.cleaned_data["description"], form.cleaned_data["logo_url"])
            messages.success(request, "Đã lưu thông tin thương hiệu.")
            return redirect("catalog_home")
        except PortalError as exc:
            messages.error(request, str(exc))
    return _form_page(request, form, f"Thông tin thương hiệu {brand.name}")


@brand_role_required(*roles.CATALOG_MANAGE)
def campaign_edit(request, pk=None):
    obj = get_object_or_404(scope_queryset(Campaign.objects.all(), request, "brand_id"), pk=pk) if pk else None
    try:
        brand_id = obj.brand_id if obj else require_brand_context(request)
    except PortalError as exc:
        messages.error(request, str(exc))
        return redirect("catalog_home")
    initial = None
    if obj:
        initial = {"name": obj.name, "campaign_type": obj.campaign_type, "value": obj.value, "perfume": obj.perfume_id,
                   "location": obj.location_id, "starts_at": obj.starts_at, "ends_at": obj.ends_at, "is_active": obj.is_active}
    form = CampaignForm(request.POST or None, initial=initial, brand_id=brand_id)
    if request.method == "POST" and form.is_valid():
        try:
            camp_svc.save_campaign(brand_id, request.user, form.cleaned_data, obj)
            messages.success(request, "Đã lưu chương trình khuyến mãi.")
            return redirect("catalog_home")
        except PortalError as exc:
            messages.error(request, str(exc))
    return _form_page(request, form, "Sửa khuyến mãi" if obj else "Thêm khuyến mãi")


@require_POST
@brand_role_required(*roles.CATALOG_MANAGE)
def campaign_toggle(request, pk):
    obj = get_object_or_404(scope_queryset(Campaign.objects.all(), request, "brand_id"), pk=pk)
    try:
        camp_svc.set_campaign_active(obj, request.user, not obj.is_active)
        messages.success(request, "Đã bật chương trình." if not obj.is_active else "Đã tắt chương trình.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("catalog_home")

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import PortalError, paginate, scoped_for_role
from catalog.models import Location

from . import machine_services as svc
from .machine_forms import ReasonForm, SlotConfigForm
from .models import Machine, MachineSlot
from .services import machine_connectivity


def _machines(request):
    return scoped_for_role(request, Machine.objects.select_related("brand", "location"), "brand_id", "id__in")


@brand_role_required(*roles.MACHINES_VIEW)
def machine_list(request):
    qs = _machines(request)
    status = request.GET.get("status", "")
    location = request.GET.get("location", "")
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if location.isdigit():
        qs = qs.filter(location_id=int(location))
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(serial_number__icontains=q))

    counts = list(_machines(request).order_by().values("status").annotate(n=Count("id")).order_by("status"))
    page_obj = paginate(request, qs.order_by("id"), 20)
    for m in page_obj:
        m.connectivity = machine_connectivity(m)
    return render(request, "portal/machines/list.html", {
        "page_obj": page_obj, "counts": counts, "status": status, "q": q, "location": location,
        "statuses": Machine.Status.choices,
        "locations": scope_queryset(Location.objects.all(), request, "brand_id").order_by("name"),
    })


@brand_role_required(*roles.MACHINES_VIEW)
def machine_detail(request, pk):
    machine = get_object_or_404(_machines(request), pk=pk)
    return render(request, "portal/machines/detail.html", {
        "machine": machine,
        "connectivity": machine_connectivity(machine),
        "slots": machine.slots.select_related("perfume").order_by("slot_number"),
        "events": machine.events.order_by("-created_at")[:15],
        "alerts": machine.alerts.exclude(status="RESOLVED").order_by("-created_at")[:10],
        "tickets": machine.maintenance_records.order_by("-created_at")[:10],
        "can_toggle": roles.can(request, roles.MACHINES_TOGGLE),
        "can_config": roles.can(request, roles.MACHINES_CONFIG),
        "can_maint": roles.can(request, roles.MACHINES_MAINTENANCE_MODE),
    })


_ACTION_ROLES = {
    "disable": roles.MACHINES_TOGGLE,
    "enable": roles.MACHINES_TOGGLE,
    "maintenance_on": roles.MACHINES_MAINTENANCE_MODE,
    "maintenance_off": roles.MACHINES_MAINTENANCE_MODE,
}


@brand_role_required(*roles.MACHINES_VIEW)
@require_POST
def machine_action(request, pk):
    machine = get_object_or_404(_machines(request), pk=pk)
    action = request.POST.get("action", "")
    if action not in _ACTION_ROLES or not roles.can(request, _ACTION_ROLES[action]):
        messages.error(request, "Bạn không có quyền thực hiện thao tác này.")
        return redirect("machine_detail", pk=pk)
    reason = ReasonForm(request.POST)
    reason.is_valid()
    text = reason.cleaned_data.get("reason", "") if hasattr(reason, "cleaned_data") else ""
    try:
        if action == "disable":
            svc.disable_machine(machine, request.user, text)
        elif action == "enable":
            svc.enable_machine(machine, request.user, text)
        elif action == "maintenance_on":
            svc.enter_maintenance(machine, request.user, text)
        else:
            svc.exit_maintenance(machine, request.user, text)
        messages.success(request, "Đã cập nhật trạng thái máy.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("machine_detail", pk=pk)


def _slot(request, slot_pk):
    return get_object_or_404(
        scoped_for_role(request, MachineSlot.objects.select_related("machine", "perfume"),
                        "machine__brand_id", "machine_id__in"),
        pk=slot_pk,
    )


@brand_role_required(*roles.MACHINES_VIEW)
@require_POST
def slot_action(request, slot_pk):
    slot = _slot(request, slot_pk)
    if not roles.can(request, roles.MACHINES_TOGGLE):
        messages.error(request, "Bạn không có quyền bật/tắt slot.")
        return redirect("machine_detail", pk=slot.machine_id)
    reason = ReasonForm(request.POST)
    reason.is_valid()
    text = reason.cleaned_data.get("reason", "") if hasattr(reason, "cleaned_data") else ""
    try:
        svc.set_slot_enabled(slot, request.POST.get("action") == "enable", request.user, text)
        messages.success(request, "Đã cập nhật slot.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("machine_detail", pk=slot.machine_id)


@brand_role_required(*roles.MACHINES_CONFIG)
def slot_config(request, slot_pk):
    slot = _slot(request, slot_pk)
    initial = {"price_per_spray": slot.price_per_spray, "low_stock_threshold": slot.low_stock_threshold,
               "spray_duration": slot.spray_duration}
    form = SlotConfigForm(request.POST or None, initial=initial, user=request.user)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            svc.configure_slot(slot, request.user, d["price_per_spray"], d["low_stock_threshold"],
                               d["spray_duration"], d.get("reason", ""))
            messages.success(request, "Đã lưu cấu hình slot.")
            return redirect("machine_detail", pk=slot.machine_id)
        except PortalError as exc:
            messages.error(request, str(exc))
    return render(request, "portal/machines/slot_form.html", {"slot": slot, "form": form})

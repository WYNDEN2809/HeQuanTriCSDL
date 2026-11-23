from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import PortalError, paginate
from devices.models import MachineSlot
from .models import InventoryLog
from .services import refill_slot


@brand_role_required(roles.BRAND_ADMIN, roles.OPS_MANAGER, roles.INV, roles.VIEWER)
def report(request):
    slots = scope_queryset(
        MachineSlot.objects.select_related("machine__location", "perfume"), request, "machine__brand_id"
    )
    low_slots = slots.filter(status__in=[MachineSlot.Status.LOW_STOCK, MachineSlot.Status.EMPTY])
    logs = scope_queryset(
        InventoryLog.objects.select_related("machine_slot__machine", "machine_slot__perfume", "user"),
        request, "machine_slot__machine__brand_id",
    )
    q = request.GET.get("q", "").strip()
    if q:
        low_slots = low_slots.filter(Q(machine__name__icontains=q) | Q(perfume__name__icontains=q))
        logs = logs.filter(Q(machine_slot__machine__name__icontains=q) | Q(machine_slot__perfume__name__icontains=q))
    return render(request, "portal/inventory/report.html", {
        "low_slots": paginate(request, low_slots.order_by("quantity", "machine__name")),
        "logs": paginate(request, logs.order_by("-created_at")), "q": q,
    })


class RefillForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=100000)
    reason = forms.CharField(max_length=30, required=False)


@brand_role_required(roles.BRAND_ADMIN, roles.OPS_MANAGER, roles.INV)
@require_POST
def refill(request, pk):
    form = RefillForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Số lượng nạp không hợp lệ.")
        return redirect("inv_report")
    slot = get_object_or_404(scope_queryset(MachineSlot.objects.all(), request, "machine__brand_id"), pk=pk)
    try:
        slot, delta = refill_slot(slot, request.user, form.cleaned_data["quantity"], form.cleaned_data["reason"])
    except PortalError as exc:
        messages.warning(request, str(exc))
        return redirect("inv_report")
    messages.success(request, f"Đã nạp thêm {delta} lượt cho khe {slot.slot_number}.")
    return redirect("inv_report")

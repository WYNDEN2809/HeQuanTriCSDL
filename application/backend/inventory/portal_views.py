from datetime import date, datetime, timedelta

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts import roles
from accounts.permissions import brand_role_required
from accounts.portal_utils import PortalError, paginate, scoped_for_role

from . import services
from .forms import AdjustForm, RefillForm, ReplaceForm
from .models import InventoryLog
from devices.models import Machine, MachineSlot


def _slots(request):
    return scoped_for_role(
        request, MachineSlot.objects.select_related("machine", "perfume"), "machine__brand_id", "machine_id__in"
    )


def _parse_date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def _export(request, filename, headers, rows):
    from reports.exports import export_response  # Nguoi 3 viet (ham dung chung)

    return export_response(request, filename, headers, rows)


@brand_role_required(*roles.INVENTORY_VIEW)
def slot_overview(request):
    qs = _slots(request)
    status = request.GET.get("status", "")
    machine = request.GET.get("machine", "")
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(status=status)
    if machine.isdigit():
        qs = qs.filter(machine_id=int(machine))
    if q:
        qs = qs.filter(Q(perfume__name__icontains=q) | Q(machine__name__icontains=q))
    page_obj = paginate(request, qs.order_by("machine_id", "slot_number"), 25)
    for s in page_obj:
        s.pct = int(100 * s.quantity / s.capacity) if s.capacity else 0
    machines = scoped_for_role(request, Machine.objects.all(), "brand_id", "id__in").order_by("name")
    return render(request, "portal/inventory/slots.html", {
        "page_obj": page_obj, "status": status, "machine": machine, "q": q, "machines": machines,
        "statuses": MachineSlot.Status.choices, "can_manage": roles.can(request, roles.INVENTORY_MANAGE),
    })


def _slot_form_view(request, slot_pk, form_cls, title, service, form_kwargs=None, initial=None):
    slot = get_object_or_404(_slots(request), pk=slot_pk)
    kwargs = form_kwargs(slot) if form_kwargs else {}
    form = form_cls(request.POST or None, initial=initial(slot) if initial else None, **kwargs)
    if request.method == "POST" and form.is_valid():
        try:
            service(slot, request.user, form.cleaned_data)
            messages.success(request, "Đã ghi nhận thay đổi tồn kho.")
            return redirect("inv_slots")
        except PortalError as exc:
            messages.error(request, str(exc))
    return render(request, "portal/inventory/form.html", {"slot": slot, "form": form, "title": title})


@brand_role_required(*roles.INVENTORY_MANAGE)
def refill(request, slot_pk):
    return _slot_form_view(
        request, slot_pk, RefillForm, "Nạp thêm nước hoa",
        lambda s, u, d: services.refill_slot(s, u, d["new_quantity"], d["reason"]),
        initial=lambda s: {"new_quantity": s.capacity},
    )


@brand_role_required(*roles.INVENTORY_MANAGE)
def replace(request, slot_pk):
    return _slot_form_view(
        request, slot_pk, ReplaceForm, "Thay chai",
        lambda s, u, d: services.replace_bottle(s, u, d["perfume"], d["new_quantity"], d["reason"]),
        form_kwargs=lambda s: {"brand_id": s.machine.brand_id},
        initial=lambda s: {"perfume": s.perfume_id, "new_quantity": s.capacity},
    )


@brand_role_required(*roles.INVENTORY_MANAGE)
def adjust(request, slot_pk):
    return _slot_form_view(
        request, slot_pk, AdjustForm, "Đối chiếu và điều chỉnh tồn kho",
        lambda s, u, d: services.adjust_inventory(s, u, d["measured_quantity"], d["reason"]),
        initial=lambda s: {"measured_quantity": s.quantity},
    )


@brand_role_required(*roles.INVENTORY_VIEW)
def movements(request):
    qs = scoped_for_role(
        request, InventoryLog.objects.select_related("machine_slot__machine", "machine_slot__perfume", "user"),
        "machine_slot__machine__brand_id", "machine_slot__machine_id__in",
    )
    ctype = request.GET.get("type", "")
    machine = request.GET.get("machine", "")
    today = date.today()
    d_from = _parse_date(request.GET.get("from"), today - timedelta(days=7))
    d_to = _parse_date(request.GET.get("to"), today)
    qs = qs.filter(created_at__gte=d_from, created_at__lt=d_to + timedelta(days=1))
    if ctype:
        qs = qs.filter(change_type=ctype)
    if machine.isdigit():
        qs = qs.filter(machine_slot__machine_id=int(machine))
    qs = qs.order_by("-created_at")

    if request.GET.get("export"):
        rows = (
            [l.created_at.strftime("%Y-%m-%d %H:%M:%S"), l.machine_slot.machine.name, l.machine_slot.slot_number,
             l.machine_slot.perfume.name, l.change_type, l.quantity_before, l.quantity_after, l.change_amount,
             l.reason or "", l.user.username if l.user else ""]
            for l in qs[:50000]
        )
        return _export(request, "inventory_movements",
                       ["Thoi gian", "May", "Slot", "Mui huong", "Loai", "Truoc", "Sau", "Thay doi", "Ly do", "Nguoi lam"], rows)

    page_obj = paginate(request, qs, 30)
    machines = scoped_for_role(request, Machine.objects.all(), "brand_id", "id__in").order_by("name")
    return render(request, "portal/inventory/movements.html", {
        "page_obj": page_obj, "type": ctype, "machine": machine, "machines": machines,
        "d_from": d_from.isoformat(), "d_to": d_to.isoformat(), "types": InventoryLog.ChangeType.choices,
    })


@brand_role_required(*roles.INVENTORY_REPORTS)
def report(request):
    """Bao cao ton kho: tong hop theo mui huong, theo may va danh sach slot can nap."""
    days = 30
    since = timezone.now() - timedelta(days=days)
    slots_qs = _slots(request)

    sale = Q(inventory_logs__change_type="SALE", inventory_logs__created_at__gte=since)
    refill = Q(inventory_logs__change_type__in=["REFILL", "REPLACE"], inventory_logs__created_at__gte=since)
    rows = []
    for s in slots_qs.annotate(sold=Sum("inventory_logs__change_amount", filter=sale),
                               refilled=Sum("inventory_logs__change_amount", filter=refill)).order_by("machine_id", "slot_number"):
        sold = -(s.sold or 0)
        daily = sold / days
        rows.append({
            "slot": s, "sold": sold, "refilled": s.refilled or 0, "daily": round(daily, 1),
            "days_left": round(s.quantity / daily, 1) if daily > 0 else None,
            "need": s.status in (MachineSlot.Status.LOW_STOCK, MachineSlot.Status.EMPTY),
        })

    by_perfume = {}
    for r in rows:
        key = r["slot"].perfume.name
        d = by_perfume.setdefault(key, {"name": key, "quantity": 0, "sold": 0})
        d["quantity"] += r["slot"].quantity
        d["sold"] += r["sold"]
    perfume_rows = sorted(by_perfume.values(), key=lambda x: -x["sold"])

    if request.GET.get("export"):
        data = (
            [r["slot"].machine.name, r["slot"].slot_number, r["slot"].perfume.name, r["slot"].quantity,
             r["slot"].capacity, r["slot"].status, r["sold"], r["daily"], r["days_left"] if r["days_left"] is not None else ""]
            for r in rows
        )
        return _export(request, "inventory_report",
                       ["May", "Slot", "Mui huong", "Ton uoc tinh", "Suc chua", "Trang thai",
                        f"Da ban {days} ngay", "Trung binh/ngay", "Du dung (ngay)"], data)

    return render(request, "portal/inventory/report.html", {
        "rows": rows, "perfume_rows": perfume_rows, "days": days,
        "need_refill": [r for r in rows if r["need"] or (r["days_left"] is not None and r["days_left"] < 3)],
    })

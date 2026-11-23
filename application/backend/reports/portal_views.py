from django.shortcuts import redirect, render

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from catalog.models import Location, Perfume
from devices.models import Machine

from . import queries
from .exports import export_response

ALLOWED = roles.REPORTS_VIEW + (roles.INV,)


def _filter_lists(request):
    return {
        "machines": scope_queryset(Machine.objects.all(), request, "brand_id").order_by("name"),
        "locations": scope_queryset(Location.objects.all(), request, "brand_id").order_by("name"),
        "perfumes": scope_queryset(Perfume.objects.all(), request, "brand_id").order_by("name"),
    }


@brand_role_required(*ALLOWED)
def dashboard(request):
    # Inventory Staff chi duoc xem bao cao ton kho
    if not request.user.is_platform_admin and request.brand_role == roles.INV:
        return redirect("inv_report")
    f = queries.parse_filters(request)
    ctx = queries.dashboard_data(request, f)
    ctx.update(_filter_lists(request))
    ctx.update({"f": f, "d_from": f["d_from"].isoformat(), "d_to": f["d_to"].isoformat()})
    return render(request, "portal/dashboard/index.html", ctx)


@brand_role_required(*roles.REPORTS_VIEW)
def export(request, kind):
    f = queries.parse_filters(request)
    orders = queries.orders_qs(request, f).select_related(
        "perfume", "machine_slot__machine__location", "machine_slot__machine__brand")

    if kind == "transactions":
        rows = (
            [o.created_at.strftime("%Y-%m-%d %H:%M:%S"), o.payment_reference, o.machine_slot.machine.brand.name,
             o.machine_slot.machine.name, o.machine_slot.machine.location.name, o.perfume.name, o.amount,
             o.currency, o.status]
            for o in orders.order_by("-created_at")[:50000]
        )
        return export_response(request, "transactions",
                               ["Thoi gian", "Ma don", "Thuong hieu", "May", "Dia diem", "Mui huong", "So tien",
                                "Tien te", "Trang thai"], rows)
    data = queries.dashboard_data(request, f)
    if kind == "daily":
        rows = ([str(r["d"]), r["n"], int(r["rev"] or 0)] for r in data["daily"])
        return export_response(request, "daily_summary", ["Ngay", "So don", "Doanh thu (don da xit)"], rows)
    if kind == "perfumes":
        rows = ([r["perfume__name"], r["n"]] for r in data["top_perfumes"])
        return export_response(request, "top_perfumes", ["Mui huong", "So lan xit"], rows)
    if kind == "machines":
        rows = ([r["machine_slot__machine__name"], r["n"], int(r["rev"] or 0)] for r in data["by_machine"])
        return export_response(request, "revenue_by_machine", ["May", "So lan xit", "Doanh thu"], rows)
    return redirect("report_dashboard")

"""Truy van tong hop cho dashboard va bao cao (Nguoi 3). Moi truy van deu qua scope_queryset (loc theo brand)."""
from datetime import date, datetime, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate

from accounts.permissions import scope_queryset
from devices.models import Alert, Machine, MachineSlot
from sales.models import DispenseTransaction, Order

ORDER_BRAND = "machine_slot__machine__brand_id"


def _date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def parse_filters(request):
    today = date.today()
    f = {
        "d_from": _date(request.GET.get("from"), today - timedelta(days=29)),
        "d_to": _date(request.GET.get("to"), today),
        "machine": request.GET.get("machine", ""),
        "location": request.GET.get("location", ""),
        "perfume": request.GET.get("perfume", ""),
    }
    if f["d_from"] > f["d_to"]:
        f["d_from"], f["d_to"] = f["d_to"], f["d_from"]
    return f


def orders_qs(request, f):
    qs = scope_queryset(Order.objects.all(), request, ORDER_BRAND)
    qs = qs.filter(created_at__gte=f["d_from"], created_at__lt=f["d_to"] + timedelta(days=1))
    if str(f["machine"]).isdigit():
        qs = qs.filter(machine_slot__machine_id=int(f["machine"]))
    if str(f["location"]).isdigit():
        qs = qs.filter(machine_slot__machine__location_id=int(f["location"]))
    if str(f["perfume"]).isdigit():
        qs = qs.filter(perfume_id=int(f["perfume"]))
    return qs


def _hours(delta):
    return delta.total_seconds() / 3600.0


def dashboard_data(request, f):
    orders = orders_qs(request, f)
    delivered = orders.filter(status=Order.Status.DISPENSED)
    disp = DispenseTransaction.objects.filter(order__in=orders)

    disp_total = disp.count()
    disp_ok = disp.filter(status=DispenseTransaction.Status.SUCCESS).count()
    revenue = delivered.aggregate(t=Sum("amount"))["t"] or 0

    daily = list(
        orders.annotate(d=TruncDate("created_at")).values("d")
        .annotate(n=Count("id"), rev=Sum("amount", filter=Q(status=Order.Status.DISPENSED))).order_by("d")
    )
    status_rows = list(orders.values("status").annotate(n=Count("id")).order_by("-n"))
    top_perfumes = list(delivered.values("perfume__name").annotate(n=Count("id")).order_by("-n")[:8])
    by_machine = list(delivered.values("machine_slot__machine__name")
                      .annotate(n=Count("id"), rev=Sum("amount")).order_by("-rev")[:10])
    by_location = list(delivered.values("machine_slot__machine__location__name")
                       .annotate(n=Count("id"), rev=Sum("amount")).order_by("-rev")[:10])

    machines = scope_queryset(Machine.objects.all(), request, "brand_id")
    machine_status = list(machines.values("status").annotate(n=Count("id")).order_by("status"))
    low_slots = scope_queryset(MachineSlot.objects.filter(
        status__in=[MachineSlot.Status.LOW_STOCK, MachineSlot.Status.EMPTY]), request, "machine__brand_id").count()

    alerts = scope_queryset(Alert.objects.all(), request, "machine__brand_id").filter(
        created_at__gte=f["d_from"], created_at__lt=f["d_to"] + timedelta(days=1))
    alert_types = list(alerts.values("alert_type").annotate(n=Count("id")).order_by("-n"))
    resolved = list(alerts.filter(resolved_at__isnull=False).values_list("created_at", "resolved_at")[:20000])
    avg_resolution_h = round(sum(_hours(r - c) for c, r in resolved) / len(resolved), 1) if resolved else None
    offline = list(alerts.filter(alert_type=Alert.Type.MACHINE_OFFLINE, resolved_at__isnull=False)
                   .values_list("created_at", "resolved_at")[:20000])
    downtime_h = round(sum(_hours(r - c) for c, r in offline), 1)
    period_h = ((f["d_to"] - f["d_from"]).days + 1) * 24
    n_machines = machines.count()
    uptime_pct = round(max(0.0, 100.0 * (1 - downtime_h / (period_h * n_machines))), 1) if n_machines and period_h else None

    critical_open = list(
        scope_queryset(Alert.objects.select_related("machine"), request, "machine__brand_id")
        .filter(severity=Alert.Severity.CRITICAL).exclude(status=Alert.Status.RESOLVED).order_by("-created_at")[:5]
    )

    platform_brands = []
    if request.user.is_platform_admin and not request.active_brand_id:
        platform_brands = list(delivered.values("machine_slot__machine__brand__name")
                               .annotate(n=Count("id"), rev=Sum("amount")).order_by("-rev"))

    return {
        "orders_total": orders.count(), "revenue": int(revenue), "delivered": delivered.count(),
        "dispense_total": disp_total, "dispense_ok": disp_ok,
        "dispense_rate": round(100.0 * disp_ok / disp_total, 1) if disp_total else None,
        "unconfirmed": orders.filter(payments__status="SUCCESS",
                                     status__in=[Order.Status.DISPENSE_FAILED, Order.Status.REVIEW]).distinct().count(),
        "daily": daily, "status_rows": status_rows, "top_perfumes": top_perfumes,
        "by_machine": by_machine, "by_location": by_location,
        "machine_status": machine_status, "low_slots": low_slots, "alert_types": alert_types,
        "avg_resolution_h": avg_resolution_h, "downtime_h": downtime_h, "uptime_pct": uptime_pct,
        "critical_open": critical_open, "platform_brands": platform_brands,
        "chart": {
            "labels": [str(r["d"]) for r in daily],
            "orders": [r["n"] for r in daily],
            "revenue": [int(r["rev"] or 0) for r in daily],
            "perfume_labels": [r["perfume__name"] for r in top_perfumes],
            "perfume_counts": [r["n"] for r in top_perfumes],
        },
    }

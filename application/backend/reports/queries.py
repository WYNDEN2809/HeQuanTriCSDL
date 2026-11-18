"""Truy van tong hop cho dashboard va bao cao (Nguoi 3). Moi truy van deu qua scope_queryset (loc theo brand)."""
from datetime import date, datetime, time, timedelta

from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.permissions import scope_queryset
from devices.models import Alert, Machine, MachineSlot
from sales.models import DispenseTransaction, Order, Payment

ORDER_BRAND = "machine_slot__machine__brand_id"


def _date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def parse_filters(request):
    today = timezone.localdate()
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
    start, end = _period_bounds(f["d_from"], f["d_to"])
    qs = qs.filter(created_at__gte=start, created_at__lt=end)
    return _apply_asset_filters(
        qs, f,
        machine_field="machine_slot__machine_id",
        location_field="machine_slot__machine__location_id",
        perfume_field="perfume_id",
    )


def _apply_asset_filters(qs, f, *, machine_field=None, location_field=None, perfume_field=None):
    """Apply selected machine/location/perfume filters consistently to a scoped queryset."""
    for key, field in (("machine", machine_field), ("location", location_field), ("perfume", perfume_field)):
        value = f.get(key, "")
        if field and str(value).isdigit():
            qs = qs.filter(**{field: int(value)})
    return qs.distinct()


def _selected_alerts(request, f):
    qs = scope_queryset(Alert.objects.all(), request, "machine__brand_id")
    qs = _apply_asset_filters(
        qs, f, machine_field="machine_id", location_field="machine__location_id",
    )
    perfume = f.get("perfume", "")
    if str(perfume).isdigit():
        # A machine-level alert has no slot; keep it for machines that contain the selected perfume.
        qs = qs.filter(
            Q(machine_slot__perfume_id=int(perfume))
            | Q(machine_slot__isnull=True, machine__slots__perfume_id=int(perfume))
        )
    return qs.distinct()


def _period_bounds(d_from, d_to):
    """Return timezone-aware [start, end) bounds for inclusive local calendar dates."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(d_from, time.min), tz)
    end = timezone.make_aware(datetime.combine(d_to + timedelta(days=1), time.min), tz)
    return start, end


def _downtime_hours(offline_alerts, period_start, period_end):
    """Sum per-machine downtime, clipping to the report period and merging overlapping alerts."""
    by_machine = {}
    for machine_id, created_at, resolved_at in offline_alerts:
        start = max(created_at, period_start)
        end = min(resolved_at or period_end, period_end)
        if end > start:
            by_machine.setdefault(machine_id, []).append((start, end))

    total_seconds = 0
    for intervals in by_machine.values():
        intervals.sort(key=lambda interval: interval[0])
        merged_start, merged_end = intervals[0]
        for start, end in intervals[1:]:
            if start <= merged_end:
                merged_end = max(merged_end, end)
            else:
                total_seconds += (merged_end - merged_start).total_seconds()
                merged_start, merged_end = start, end
        total_seconds += (merged_end - merged_start).total_seconds()
    return total_seconds / 3600.0


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

    machines = _apply_asset_filters(
        scope_queryset(Machine.objects.all(), request, "brand_id"), f,
        machine_field="id", location_field="location_id", perfume_field="slots__perfume_id",
    )
    machine_status = list(machines.values("status").annotate(n=Count("id")).order_by("status"))
    low_slot_qs = scope_queryset(MachineSlot.objects.filter(
        status__in=[MachineSlot.Status.LOW_STOCK, MachineSlot.Status.EMPTY]), request, "machine__brand_id")
    low_slots = _apply_asset_filters(
        low_slot_qs, f, machine_field="machine_id", location_field="machine__location_id",
        perfume_field="perfume_id",
    ).count()

    selected_alerts = _selected_alerts(request, f)
    period_start, period_end = _period_bounds(f["d_from"], f["d_to"])
    alerts = selected_alerts.filter(created_at__gte=period_start, created_at__lt=period_end)
    alert_types = list(alerts.values("alert_type").annotate(n=Count("id")).order_by("-n"))
    resolved = alerts.filter(resolved_at__isnull=False).values_list("created_at", "resolved_at").iterator(chunk_size=2000)
    resolution_seconds = 0
    resolution_count = 0
    for created_at, resolved_at in resolved:
        resolution_seconds += (resolved_at - created_at).total_seconds()
        resolution_count += 1
    avg_resolution_h = round(resolution_seconds / resolution_count / 3600, 1) if resolution_count else None
    offline = selected_alerts.filter(alert_type=Alert.Type.MACHINE_OFFLINE).filter(
        created_at__lt=period_end,
    ).filter(Q(resolved_at__isnull=True) | Q(resolved_at__gt=period_start)).values_list(
        "machine_id", "created_at", "resolved_at",
    ).iterator(chunk_size=2000)
    downtime_total_h = _downtime_hours(offline, period_start, period_end)
    downtime_h = round(downtime_total_h, 1)
    period_h = (period_end - period_start).total_seconds() / 3600.0
    n_machines = machines.count()
    total_machine_h = period_h * n_machines
    uptime_pct = round(max(0.0, 100.0 * (1 - downtime_total_h / total_machine_h)), 1) if total_machine_h else None

    critical_open = list(
        _selected_alerts(request, f).select_related("machine")
        .filter(severity=Alert.Severity.CRITICAL).exclude(status=Alert.Status.RESOLVED).order_by("-created_at")[:5]
    )

    platform_brands = []
    if request.user.is_platform_admin and not request.active_brand_id:
        platform_brands = list(delivered.values("machine_slot__machine__brand__name")
                               .annotate(n=Count("id"), rev=Sum("amount")).order_by("-rev"))

    successful_payment = Payment.objects.filter(
        order_id=OuterRef("pk"), status=Payment.Status.SUCCESS,
    )
    unconfirmed_orders = orders.filter(
        status__in=[Order.Status.DISPENSE_FAILED, Order.Status.REVIEW],
    ).filter(Exists(successful_payment))

    return {
        "orders_total": orders.count(), "revenue": int(revenue), "delivered": delivered.count(),
        "dispense_total": disp_total, "dispense_ok": disp_ok,
        "dispense_rate": round(100.0 * disp_ok / disp_total, 1) if disp_total else None,
        "unconfirmed": unconfirmed_orders.aggregate(amount=Sum("amount"))["amount"] or 0,
        "unconfirmed_count": unconfirmed_orders.count(),
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

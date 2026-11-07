from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render

from accounts.permissions import scope_queryset
from devices.models import Alert, Machine, MachineSlot
from sales.models import Order


@login_required
def home(request):
    """Trang chu: so lieu tong quan, da loc theo brand cua nguoi dung."""
    machines = scope_queryset(Machine.objects.all(), request, "brand_id")
    orders = scope_queryset(Order.objects.all(), request, "machine_slot__machine__brand_id")
    slots = scope_queryset(MachineSlot.objects.all(), request, "machine__brand_id")
    alerts = scope_queryset(Alert.objects.all(), request, "machine__brand_id")

    revenue = orders.filter(status=Order.Status.DISPENSED).aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "machine_total": machines.count(),
        "machine_status": list(machines.values("status").annotate(n=Count("id")).order_by("status")),
        "order_total": orders.count(),
        "order_status": list(orders.values("status").annotate(n=Count("id")).order_by("-n")),
        "revenue": int(revenue),
        "problem_orders": orders.filter(
            status__in=[Order.Status.DISPENSE_FAILED, Order.Status.REVIEW]
        ).count(),
        "open_alerts": alerts.exclude(status=Alert.Status.RESOLVED).count(),
        "recent_orders": list(
            orders.select_related("perfume", "machine_slot__machine").order_by("-created_at")[:15]
        ),
        "low_stock_slots": slots.filter(
            status__in=[MachineSlot.Status.LOW_STOCK, MachineSlot.Status.EMPTY]
        ).count(),
    }
    return render(request, "home.html", context)

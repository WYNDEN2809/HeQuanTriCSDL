from datetime import date, datetime, timedelta

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import PortalError, paginate
from catalog.models import Location, Perfume
from devices.models import Alert, Machine
from inventory.models import InventoryLog
from reports.models import AuditLog

from . import portal_services as svc
from . import reconciliation as recon
from .models import DispenseTransaction, Order, Payment
from .portal_forms import ActionForm, ReconcileForm

BRAND = "machine_slot__machine__brand_id"


def _orders(request):
    return scope_queryset(
        Order.objects.select_related("perfume", "machine_slot__machine__location", "machine_slot__machine__brand"),
        request, BRAND)


def _date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


@brand_role_required(*roles.TRANSACTIONS_VIEW)
def tx_list(request):
    today = date.today()
    d_from = _date(request.GET.get("from"), today - timedelta(days=29))
    d_to = _date(request.GET.get("to"), today)
    status = request.GET.get("status", "")
    pstatus = request.GET.get("pstatus", "")
    machine = request.GET.get("machine", "")
    location = request.GET.get("location", "")
    perfume = request.GET.get("perfume", "")
    q = request.GET.get("q", "").strip()
    problem = request.GET.get("problem") == "1"

    qs = _orders(request).filter(created_at__gte=d_from, created_at__lt=d_to + timedelta(days=1))
    if problem:
        qs = qs.filter(status__in=[Order.Status.DISPENSE_FAILED, Order.Status.REVIEW])
    if status:
        qs = qs.filter(status=status)
    if machine.isdigit():
        qs = qs.filter(machine_slot__machine_id=int(machine))
    if location.isdigit():
        qs = qs.filter(machine_slot__machine__location_id=int(location))
    if perfume.isdigit():
        qs = qs.filter(perfume_id=int(perfume))
    if pstatus:
        qs = qs.filter(payments__status=pstatus)
    if q:
        qs = qs.filter(Q(payment_reference__icontains=q) | Q(payments__provider_transaction_id__icontains=q))
    if pstatus or q:
        qs = qs.distinct()
    qs = qs.order_by("-created_at")

    if request.GET.get("export"):
        from reports.exports import export_response  # Nguoi 3

        rows = (
            [o.created_at.strftime("%Y-%m-%d %H:%M:%S"), o.payment_reference, o.machine_slot.machine.name,
             o.machine_slot.machine.location.name, o.perfume.name, o.amount, o.currency, o.status]
            for o in qs[:50000]
        )
        return export_response(request, "transactions_search",
                               ["Thoi gian", "Ma don", "May", "Dia diem", "Mui huong", "So tien", "Tien te", "Trang thai"], rows)

    counts = list(qs.order_by().values("status").annotate(n=Count("id", distinct=True)).order_by("status"))
    page_obj = paginate(request, qs, 25)
    page_obj_ids = [o.pk for o in page_obj]
    paid = {p["order_id"]: p["status"] for p in
            Payment.objects.filter(order_id__in=page_obj_ids).order_by("id").values("order_id", "status")}
    for o in page_obj:
        o.payment_status = paid.get(o.pk, "-")
    return render(request, "portal/transactions/list.html", {
        "page_obj": page_obj, "counts": counts, "d_from": d_from.isoformat(), "d_to": d_to.isoformat(),
        "status": status, "pstatus": pstatus, "machine": machine, "location": location, "perfume": perfume,
        "q": q, "problem": problem,
        "order_statuses": Order.Status.choices, "payment_statuses": Payment.Status.choices,
        "machines": scope_queryset(Machine.objects.all(), request, "brand_id").order_by("name"),
        "locations": scope_queryset(Location.objects.all(), request, "brand_id").order_by("name"),
        "perfumes": scope_queryset(Perfume.objects.all(), request, "brand_id").order_by("name"),
        "can_manage": roles.can(request, roles.TRANSACTIONS_MANAGE),
    })


@brand_role_required(*roles.TRANSACTIONS_VIEW)
def tx_detail(request, pk, form=None):
    order = get_object_or_404(_orders(request), pk=pk)
    dispense = DispenseTransaction.objects.filter(order_id=order.pk).first()
    entity_ids = [order.pk]
    trail = AuditLog.objects.filter(entity_type="Orders", entity_id=order.pk)
    if dispense:
        trail = trail | AuditLog.objects.filter(entity_type="DispenseTransaction", entity_id=dispense.pk)
    can_manage = roles.can(request, roles.TRANSACTIONS_MANAGE)
    actions = svc.available_actions(order) if can_manage else []
    return render(request, "portal/transactions/detail.html", {
        "order": order, "dispense": dispense,
        "payments": order.payments.order_by("created_at"),
        "inventory_logs": InventoryLog.objects.filter(order_id=order.pk).order_by("created_at"),
        "alerts": Alert.objects.filter(machine_slot_id=order.machine_slot_id, alert_type="DISPENSE_FAILURE",
                                       created_at__gte=order.created_at - timedelta(hours=1),
                                       created_at__lte=order.created_at + timedelta(days=1)),
        "trail": trail.select_related("user").order_by("created_at"),
        "actions": actions, "retries": svc.retry_count(order),
        "form": form or ActionForm(user=request.user),
    })


@brand_role_required(*roles.TRANSACTIONS_MANAGE)
@require_POST
def tx_action(request, pk):
    order = get_object_or_404(_orders(request), pk=pk)
    action = request.POST.get("action", "")
    form = ActionForm(request.POST, user=request.user)
    if action not in dict(svc.available_actions(order)):
        messages.error(request, "Thao tác không hợp lệ với trạng thái hiện tại của đơn.")
        return redirect("tx_detail", pk=pk)
    if not form.is_valid():
        messages.error(request, "Cần nhập lý do và mật khẩu đúng để xác nhận.")
        return tx_detail(request, pk, form=form)
    try:
        svc.perform(action, order, request.user, form.cleaned_data["reason"])
        messages.success(request, "Đã xử lý đơn hàng.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("tx_detail", pk=pk)


_SESSION_KEY = "recon_rows"


@brand_role_required(*roles.TRANSACTIONS_MANAGE)
def reconcile_view(request):
    today = date.today()
    form = ReconcileForm(request.POST or None, request.FILES or None,
                         initial={"d_from": today - timedelta(days=29), "d_to": today})
    result = None
    summary = []
    if request.method == "POST" and form.is_valid():
        try:
            rows = recon.parse_provider_csv(form.cleaned_data["file"])
            result = recon.reconcile(request, rows, form.cleaned_data["d_from"], form.cleaned_data["d_to"])
            summary = [(k, recon.LABELS[k], len(v)) for k, v in result.items()]
            request.session[_SESSION_KEY] = recon.flatten_mismatches(result)[:2000]
        except PortalError as exc:
            messages.error(request, str(exc))
    return render(request, "portal/transactions/reconcile.html", {
        "form": form, "result": result, "summary": summary, "labels": recon.LABELS,
        "has_export": bool(request.session.get(_SESSION_KEY)),
    })


@brand_role_required(*roles.TRANSACTIONS_MANAGE)
def reconcile_export(request):
    from reports.exports import export_response  # Nguoi 3

    rows = request.session.get(_SESSION_KEY, [])
    return export_response(request, "reconciliation_mismatches",
                           ["Nhom", "Ma giao dich", "Ma don", "So tien (he thong)", "Trang thai (he thong)",
                            "So tien (nha cung cap)", "Trang thai (nha cung cap)"], rows)

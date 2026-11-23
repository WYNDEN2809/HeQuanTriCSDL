from datetime import timedelta

from django import forms
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.permissions import brand_role_required
from accounts.portal_utils import PortalError, paginate, scoped_for_role
from reports.models import AuditLog

from . import alert_services as svc
from .models import Alert


def _alerts(request):
    return scoped_for_role(
        request, Alert.objects.select_related("machine__location", "machine_slot__perfume"),
        "machine__brand_id", "machine_id__in",
    )


@brand_role_required(*roles.ALERTS_VIEW)
def alert_list(request):
    qs = _alerts(request)
    status = request.GET.get("status", "active")
    severity = request.GET.get("severity", "")
    atype = request.GET.get("type", "")
    q = request.GET.get("q", "").strip()
    overdue = request.GET.get("overdue") == "1"

    if status == "active":
        qs = qs.exclude(status=Alert.Status.RESOLVED)
    elif status in dict(Alert.Status.choices):
        qs = qs.filter(status=status)
    if severity:
        qs = qs.filter(severity=severity)
    if atype:
        qs = qs.filter(alert_type=atype)
    if q:
        qs = qs.filter(Q(machine__name__icontains=q) | Q(machine__serial_number__icontains=q))
    if overdue:
        qs = qs.filter(svc.overdue_q())

    counts = {r["status"]: r["n"] for r in
              _alerts(request).order_by().values("status").annotate(n=Count("id"))}
    n_overdue = _alerts(request).filter(svc.overdue_q()).count()
    page_obj = paginate(request, qs.order_by("-created_at"), 25)
    now = timezone.now()
    for a in page_obj:
        a.overdue = svc.is_overdue(a, now)
    return render(request, "portal/alerts/list.html", {
        "page_obj": page_obj, "counts": counts, "n_overdue": n_overdue, "status": status, "severity": severity,
        "type": atype, "q": q, "overdue": overdue,
        "types": Alert.Type.choices, "severities": Alert.Severity.choices, "statuses": Alert.Status.choices,
    })


@brand_role_required(*roles.ALERTS_VIEW)
def alert_detail(request, pk):
    alert = get_object_or_404(_alerts(request), pk=pk)
    return render(request, "portal/alerts/detail.html", {
        "alert": alert, "overdue": svc.is_overdue(alert), "deadline": svc.sla_deadline(alert),
        "tickets": alert.maintenance_records.order_by("-created_at"),
        "history": AuditLog.objects.filter(entity_type="Alert", entity_id=alert.pk).select_related("user").order_by("-created_at")[:20],
        "technicians": svc.technicians_for(alert),
        "can_ack": roles.can(request, roles.ALERTS_ACK), "can_manage": roles.can(request, roles.ALERTS_MANAGE),
    })


class NoteForm(forms.Form):
    note = forms.CharField(required=False, max_length=500)
    technician = forms.IntegerField(required=False)


@brand_role_required(*roles.ALERTS_VIEW)
@require_POST
def alert_action(request, pk):
    alert = get_object_or_404(_alerts(request), pk=pk)
    action = request.POST.get("action", "")
    needed = roles.ALERTS_ACK if action == "ack" else roles.ALERTS_MANAGE
    if action not in ("ack", "resolve", "reopen", "assign") or not roles.can(request, needed):
        messages.error(request, "Bạn không có quyền thực hiện thao tác này.")
        return redirect("alert_detail", pk=pk)
    form = NoteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Ghi chú hoặc mã kỹ thuật viên không hợp lệ.")
        return redirect("alert_detail", pk=pk)
    data = form.cleaned_data
    try:
        if action == "ack":
            svc.acknowledge_alert(alert, request.user)
        elif action == "resolve":
            svc.resolve_alert(alert, request.user, data.get("note"))
        elif action == "reopen":
            svc.reopen_alert(alert, request.user, data.get("note"))
        else:
            if not data.get("technician"):
                raise PortalError("Hãy chọn kỹ thuật viên.")
            ticket = svc.assign_alert(alert, request.user, data["technician"])
            messages.info(request, f"Đã tạo phiếu bảo trì #{ticket.pk}.")
        messages.success(request, "Đã cập nhật cảnh báo.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("alert_detail", pk=pk)

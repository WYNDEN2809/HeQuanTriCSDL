from django import forms
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import PortalError, paginate
from reports.audit import log_action

from .models import MaintenanceRecord


def _tickets(request):
    return scope_queryset(
        MaintenanceRecord.objects.select_related("machine__location", "assigned_to", "created_by", "alert"),
        request, "machine__brand_id",
    )


@brand_role_required(roles.BRAND_ADMIN, roles.OPS_MANAGER, roles.TECHNICIAN, roles.VIEWER)
def ticket_list(request):
    qs = _tickets(request)
    status = request.GET.get("status", "OPEN")
    if status in dict(MaintenanceRecord.Status.choices):
        qs = qs.filter(status=status)
    elif status == "all":
        pass
    else:
        status = "OPEN"
        qs = qs.filter(status=status)
    return render(request, "portal/maintenance/list.html", {
        "page_obj": paginate(request, qs.order_by("-created_at")), "status": status,
        "statuses": MaintenanceRecord.Status.choices,
    })


@brand_role_required(roles.BRAND_ADMIN, roles.OPS_MANAGER, roles.TECHNICIAN, roles.VIEWER)
def ticket_detail(request, pk):
    ticket = get_object_or_404(_tickets(request), pk=pk)
    can_manage = request.user.is_platform_admin or request.brand_role in (roles.BRAND_ADMIN, roles.OPS_MANAGER)
    can_work = can_manage or (request.brand_role == roles.TECHNICIAN and ticket.assigned_to_id == request.user.pk)
    return render(request, "portal/maintenance/detail.html", {"ticket": ticket, "can_work": can_work})


class TicketActionForm(forms.Form):
    action = forms.ChoiceField(choices=(("start", "Bắt đầu"), ("complete", "Hoàn tất"), ("cancel", "Hủy")))
    note = forms.CharField(required=False, max_length=500)


@brand_role_required(roles.BRAND_ADMIN, roles.OPS_MANAGER, roles.TECHNICIAN)
@require_POST
def ticket_action(request, pk):
    form = TicketActionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Thao tác phiếu bảo trì không hợp lệ.")
        return redirect("maintenance_detail", pk=pk)
    try:
        with transaction.atomic():
            ticket = get_object_or_404(_tickets(request).select_for_update(), pk=pk)
            can_manage = request.user.is_platform_admin or request.brand_role in (roles.BRAND_ADMIN, roles.OPS_MANAGER)
            if not can_manage and ticket.assigned_to_id != request.user.pk:
                raise PortalError("Bạn chỉ được cập nhật phiếu đã giao cho mình.")
            action = form.cleaned_data["action"]
            old = ticket.status
            now = timezone.now()
            if action == "start" and ticket.status == MaintenanceRecord.Status.OPEN:
                ticket.status = MaintenanceRecord.Status.IN_PROGRESS
            elif action == "complete" and ticket.status == MaintenanceRecord.Status.IN_PROGRESS:
                if not form.cleaned_data["note"].strip():
                    raise PortalError("Cần ghi kết quả xử lý trước khi hoàn tất phiếu.")
                ticket.status = MaintenanceRecord.Status.COMPLETED
                ticket.completed_at = now
                ticket.description = ((ticket.description or "")[:300] + "\nKết quả: "
                                     + form.cleaned_data["note"].strip()[:190])[:500]
            elif action == "cancel" and can_manage and ticket.status in (MaintenanceRecord.Status.OPEN, MaintenanceRecord.Status.IN_PROGRESS):
                ticket.status = MaintenanceRecord.Status.CANCELLED
                ticket.description = ((ticket.description or "")[:300] + "\nLý do hủy: "
                                     + (form.cleaned_data["note"].strip() or "Không nêu")[:190])[:500]
            else:
                raise PortalError("Không thể thực hiện thao tác này với trạng thái hiện tại.")
            ticket.save(update_fields=["status", "completed_at", "description"])
            log_action(request.user, "MAINTENANCE_" + action.upper(), "MaintenanceRecord", ticket.pk,
                       ticket.machine.brand_id, old_value={"status": old},
                       new_value={"status": ticket.status, "note": form.cleaned_data["note"]})
    except PortalError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Đã cập nhật phiếu bảo trì.")
    return redirect("maintenance_detail", pk=pk)

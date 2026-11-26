from datetime import date

from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_GET

from accounts import roles
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import paginate

from .exports import export_response
from .models import AuditLog


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@brand_role_required(*roles.AUDIT_VIEW)
@require_GET
def audit_list(request):
    logs = scope_queryset(
        AuditLog.objects.select_related("user", "brand"), request, "brand_id"
    )
    filters = {
        "q": request.GET.get("q", "").strip(),
        "action": request.GET.get("action", "").strip(),
        "entity_type": request.GET.get("entity_type", "").strip(),
        "date_from": request.GET.get("from", "").strip(),
        "date_to": request.GET.get("to", "").strip(),
    }

    if filters["action"]:
        logs = logs.filter(action__icontains=filters["action"][:100])
    if filters["entity_type"]:
        logs = logs.filter(entity_type__icontains=filters["entity_type"][:50])
    if filters["q"]:
        query = Q(action__icontains=filters["q"]) | Q(entity_type__icontains=filters["q"])
        query |= Q(user__username__icontains=filters["q"])
        if filters["q"].isdigit():
            query |= Q(entity_id=int(filters["q"]))
        logs = logs.filter(query)

    start_date = _parse_date(filters["date_from"])
    end_date = _parse_date(filters["date_to"])
    if start_date:
        logs = logs.filter(created_at__date__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__date__lte=end_date)

    logs = logs.order_by("-created_at", "-pk")
    if request.GET.get("format", "").lower() in {"csv", "xlsx"}:
        rows = (
            [
                entry.created_at,
                entry.user.get_username() if entry.user_id else "",
                entry.brand.name if entry.brand_id else "",
                entry.action,
                entry.entity_type or "",
                entry.entity_id,
                entry.old_value or "",
                entry.new_value or "",
            ]
            for entry in logs[:50000]
        )
        return export_response(
            request,
            "audit_logs",
            ["Thời gian", "Người dùng", "Thương hiệu", "Hành động", "Loại đối tượng", "Mã đối tượng", "Giá trị cũ", "Giá trị mới"],
            rows,
        )

    page_obj = paginate(request, logs, 50)
    return render(
        request,
        "portal/audit/list.html",
        {
            "page_obj": page_obj,
            "filters": filters,
        },
    )

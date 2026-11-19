from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts import roles
from accounts.models import User
from accounts.permissions import brand_role_required, scope_queryset
from accounts.portal_utils import PortalError, paginate, require_brand_context
from devices.models import Machine, MachineSlot
from reports.models import AuditLog

from . import services as svc
from .models import MaintenanceChecklistItem as Item
from .models import MaintenanceRecord as Record
from .portal_forms import PRIORITY_CHOICES, SimpleNoteForm, SprayConfirmForm, TicketForm, technician_choices


def _tickets(request):
    qs = scope_queryset(Record.objects.select_related("machine__location", "alert", "assigned_to", "created_by"),
                        request, "machine__brand_id")
    if not request.user.is_platform_admin and request.brand_role == roles.TECH:
        qs = qs.filter(assigned_to_id=request.user.pk)   # ky thuat vien chi thay phieu duoc giao
    return qs


def priority_q(p):
    """Loc theo do uu tien: tien to [P:x] hoac (khong co tien to) theo muc do canh bao, mac dinh MEDIUM."""
    explicit = Q(description__startswith=f"[P:{p}]")
    no_prefix = ~Q(description__startswith="[P:")
    from_alert = Q(alert__severity=p)
    q = explicit | (no_prefix & from_alert)
    if p == "MEDIUM":
        q |= no_prefix & Q(alert__isnull=True)
    return q


@brand_role_required(*roles.MAINT_VIEW)
def ticket_list(request):
    qs = _tickets(request)
    status = request.GET.get("status", "open")
    mtype = request.GET.get("type", "")
    priority = request.GET.get("priority", "")
    machine = request.GET.get("machine", "")
    mine = request.GET.get("mine") == "1"
    if status == "open":
        qs = qs.filter(status__in=svc.OPEN_STATUSES)
    elif status in Record.Status.values:
        qs = qs.filter(status=status)
    if mtype:
        qs = qs.filter(maintenance_type=mtype)
    if priority in svc.PRIORITIES:
        qs = qs.filter(priority_q(priority))
    if machine.isdigit():
        qs = qs.filter(machine_id=int(machine))
    if mine:
        qs = qs.filter(assigned_to_id=request.user.pk)
    page_obj = paginate(request, qs.order_by("-created_at"), 25)
    now = timezone.now()
    for t in page_obj:
        t.priority = svc.priority_of(t)
        t.overdue = svc.is_overdue(t, now)
        t.text = svc.clean_description(t)
    return render(request, "portal/maintenance/list.html", {
        "page_obj": page_obj, "status": status, "type": mtype, "priority": priority, "machine": machine, "mine": mine,
        "types": Record.Type.choices, "statuses": Record.Status.choices, "priorities": PRIORITY_CHOICES,
        "machines": scope_queryset(Machine.objects.all(), request, "brand_id").order_by("name"),
        "can_manage": roles.can(request, roles.MAINT_MANAGE),
    })


@brand_role_required(*roles.MAINT_MANAGE)
def ticket_create(request):
    machines = list(scope_queryset(Machine.objects.all(), request, "brand_id").order_by("name"))
    form = TicketForm(request.POST or None, machines=machines)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        machine = next((m for m in machines if m.pk == int(d["machine"])), None)
        try:
            tech = User.objects.get(pk=int(d["assigned_to"])) if d["assigned_to"] else None
            rec = svc.create_ticket(machine, request.user, d["maintenance_type"], d["description"], d["priority"], tech)
            messages.success(request, f"Đã tạo phiếu bảo trì #{rec.pk}.")
            return redirect("mt_detail", pk=rec.pk)
        except (PortalError, User.DoesNotExist) as exc:
            messages.error(request, str(exc) if isinstance(exc, PortalError) else "Kỹ thuật viên không tồn tại.")
    return render(request, "portal/maintenance/create.html", {"form": form})


def _can_execute(request, ticket):
    if request.user.is_platform_admin:
        return True
    return roles.can(request, roles.MAINT_EXECUTE) and ticket.assigned_to_id in (None, request.user.pk)


@brand_role_required(*roles.MAINT_VIEW)
def ticket_detail(request, pk, spray_form=None):
    ticket = get_object_or_404(_tickets(request), pk=pk)
    items = list(ticket.checklist_items.all())
    phases = {}
    for it in items:
        phases.setdefault(it.get_phase_display(), []).append(it)
    done = sum(1 for i in items if i.is_done)
    machine = ticket.machine
    return render(request, "portal/maintenance/detail.html", {
        "ticket": ticket, "priority": svc.priority_of(ticket), "text": svc.clean_description(ticket),
        "due": svc.due_at(ticket), "overdue": svc.is_overdue(ticket), "phases": phases,
        "progress": int(100 * done / len(items)) if items else 0, "done": done, "total": len(items),
        "result_item": next((i for i in items if i.phase == Item.Phase.RESULT), None),
        "slots": MachineSlot.objects.filter(machine_id=machine.pk).order_by("slot_number"),
        "history": AuditLog.objects.filter(entity_type="MaintenanceRecord", entity_id=ticket.pk)
                   .select_related("user").order_by("-created_at")[:25],
        "technicians": technician_choices(brand_id=machine.brand_id),
        "priorities": PRIORITY_CHOICES, "post_test_text": svc.POST_TEST_TEXT,
        "can_manage": roles.can(request, roles.MAINT_MANAGE), "can_execute": _can_execute(request, ticket),
        "is_open": ticket.status in svc.OPEN_STATUSES,
        "spray_form": spray_form or SprayConfirmForm(user=request.user),
    })


@brand_role_required(*roles.MAINT_VIEW)
@require_POST
def ticket_action(request, pk):
    ticket = get_object_or_404(_tickets(request), pk=pk)
    action = request.POST.get("action", "")
    manage = ("assign", "priority", "cancel")
    execute = ("start", "item", "result", "spray", "complete")
    if action in manage and not roles.can(request, roles.MAINT_MANAGE):
        messages.error(request, "Bạn không có quyền quản lý phiếu.")
        return redirect("mt_detail", pk=pk)
    if action in execute and not _can_execute(request, ticket):
        messages.error(request, "Chỉ kỹ thuật viên được giao mới thực hiện được thao tác này.")
        return redirect("mt_detail", pk=pk)
    if action not in manage + execute:
        messages.error(request, "Thao tác không hợp lệ.")
        return redirect("mt_detail", pk=pk)

    form = SimpleNoteForm(request.POST)
    form.is_valid()
    d = getattr(form, "cleaned_data", {})
    try:
        if action == "assign":
            tech = User.objects.filter(pk=d.get("technician") or 0).first()
            if tech is None:
                raise PortalError("Hãy chọn kỹ thuật viên.")
            svc.assign_ticket(ticket, tech, request.user)
        elif action == "priority":
            svc.set_priority(ticket, d.get("priority"), request.user)
        elif action == "cancel":
            svc.cancel_ticket(ticket, request.user, d.get("note"))
        elif action == "start":
            svc.start_ticket(ticket, request.user)
        elif action == "item":
            svc.set_item(ticket, d.get("item_id"), d.get("done"), request.user, d.get("note", ""))
        elif action == "result":
            svc.record_result(ticket, request.user, d.get("text"))
        elif action == "spray":
            confirm = SprayConfirmForm(request.POST, user=request.user)
            if not confirm.is_valid():
                messages.error(request, "Cần nhập đúng mật khẩu để xác nhận xịt thử.")
                return ticket_detail(request, pk, spray_form=confirm)
            svc.test_spray(ticket, request.user, d.get("slot"), d.get("purpose") or "diag", d.get("passed"), d.get("note", ""))
        elif action == "complete":
            svc.complete_ticket(ticket, request.user)
        messages.success(request, "Đã cập nhật phiếu bảo trì.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("mt_detail", pk=pk)

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts import roles

from . import portal_services as svc
from .models import BrandMember
from .permissions import brand_role_required
from .portal_forms import MemberActionForm, MemberCreateForm
from .portal_utils import PortalError, require_brand_context


def _members(request):
    return BrandMember.objects.filter(brand_id=request.active_brand_id).select_related("user", "brand")


@brand_role_required(*roles.PEOPLE_MANAGE)
def people_list(request):
    q = request.GET.get("q", "").strip()
    members = []
    if request.active_brand_id:
        qs = _members(request).order_by("brand_role", "user__username")
        if q:
            qs = qs.filter(Q(user__username__icontains=q) | Q(user__email__icontains=q))
        members = list(qs)
        for m in members:
            m.other_brands = BrandMember.objects.filter(user_id=m.user_id).exclude(brand_id=m.brand_id).count()
    return render(request, "portal/people/list.html", {
        "members": members, "q": q, "role_choices": BrandMember.BrandRole.choices, "me": request.user.pk,
    })


@brand_role_required(*roles.PEOPLE_MANAGE)
def people_create(request):
    form = MemberCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            brand_id = require_brand_context(request)
            m = svc.create_member(brand_id, request.user, d["username"], d["email"], d["password"], d["brand_role"])
            messages.success(request, f"Đã tạo tài khoản {m.user.username}.")
            return redirect("people_list")
        except PortalError as exc:
            messages.error(request, str(exc))
    return render(request, "portal/people/create.html", {"form": form})


@brand_role_required(*roles.PEOPLE_MANAGE)
@require_POST
def people_action(request, pk):
    member = get_object_or_404(_members(request), pk=pk)   # chi thao tac tren thanh vien cua brand dang chon
    action = request.POST.get("action", "")
    form = MemberActionForm(request.POST)
    form.is_valid()
    d = getattr(form, "cleaned_data", {})
    try:
        if action == "role":
            svc.change_role(member, d.get("brand_role"), request.user)
            messages.success(request, "Đã đổi vai trò.")
        elif action == "remove":
            svc.remove_member(member, request.user)
            messages.success(request, "Đã gỡ khỏi thương hiệu.")
        elif action in ("activate", "deactivate"):
            svc.set_active(member, action == "activate", request.user)
            messages.success(request, "Đã cập nhật trạng thái tài khoản.")
        elif action == "reset":
            pwd = svc.reset_password(member, request.user, d.get("new_password") or None)
            messages.warning(request, f"Mật khẩu mới của {member.user.username}: {pwd} (chỉ hiện một lần; đã đăng xuất mọi phiên).")
        else:
            raise PortalError("Thao tác không hợp lệ.")
    except PortalError as exc:
        messages.error(request, str(exc))
    return redirect("people_list")

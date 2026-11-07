from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .middleware import SESSION_KEY


@login_required
@require_POST
def switch_brand(request):
    """Doi brand dang lam viec. Super admin co the chon '' = tat ca brand."""
    raw = request.POST.get("brand_id", "")
    if raw == "" and request.user.is_platform_admin:
        request.session.pop(SESSION_KEY, None)
    else:
        try:
            brand_id = int(raw)
        except ValueError:
            raise PermissionDenied
        if not any(b.id == brand_id for b in request.available_brands):
            raise PermissionDenied
        request.session[SESSION_KEY] = brand_id

    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("home")

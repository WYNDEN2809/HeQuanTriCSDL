from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(user=request.user).select_related("brand")
    return render(request, "portal/notifications/list.html", {"page_obj": qs[:100]})


@login_required
@require_POST
def notification_read(request, pk):
    item = get_object_or_404(Notification, pk=pk, user=request.user)
    if item.read_at is None:
        item.read_at = timezone.now()
        item.save(update_fields=["read_at"])
    messages.success(request, "Đã đánh dấu đã đọc.")
    return redirect(item.target_url or "notification_list")

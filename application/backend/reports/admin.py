from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit log chi doc: nguoi dung thuong khong duoc sua/xoa (yeu cau cua de tai)."""

    list_display = ("id", "created_at", "user", "brand", "action", "entity_type", "entity_id")
    list_filter = ("action", "brand")
    search_fields = ("action", "entity_type")
    show_full_result_count = False
    list_select_related = ("user", "brand")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

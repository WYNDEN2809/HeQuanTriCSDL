from django.contrib import admin

from .models import MaintenanceChecklistItem, MaintenanceRecord


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "maintenance_type", "status", "assigned_to", "created_at", "completed_at")
    list_filter = ("status", "maintenance_type")
    list_select_related = ("machine", "assigned_to")


@admin.register(MaintenanceChecklistItem)
class MaintenanceChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("id", "record", "phase", "item_text", "is_done", "done_at")
    list_filter = ("phase", "is_done")

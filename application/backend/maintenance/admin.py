from django.contrib import admin

from .models import MaintenanceRecord


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "maintenance_type", "status", "assigned_to", "created_at", "completed_at")
    list_filter = ("status", "maintenance_type")
    list_select_related = ("machine", "assigned_to")

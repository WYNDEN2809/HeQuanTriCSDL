from django.contrib import admin

from .models import InventoryLog


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ("id", "machine_slot", "change_type", "quantity_before", "quantity_after", "reason", "created_at")
    list_filter = ("change_type",)
    show_full_result_count = False
    list_select_related = ("machine_slot__machine",)

from django.contrib import admin

from .models import Alert, DeviceEvent, Machine, MachineSlot


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "serial_number", "brand", "location", "status", "last_seen_at")
    list_filter = ("brand", "status")
    search_fields = ("name", "serial_number")


@admin.register(MachineSlot)
class MachineSlotAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "slot_number", "perfume", "quantity", "capacity", "status")
    list_filter = ("status", "machine__brand")
    list_select_related = ("machine", "perfume")


@admin.register(DeviceEvent)
class DeviceEventAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "event_type", "created_at")
    list_filter = ("event_type",)
    show_full_result_count = False
    list_select_related = ("machine",)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("id", "machine", "alert_type", "severity", "status", "created_at")
    list_filter = ("severity", "status", "alert_type")
    show_full_result_count = False
    list_select_related = ("machine",)

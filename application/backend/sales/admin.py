from django.contrib import admin

from .models import DispenseTransaction, Order, Payment


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "payment_reference", "machine_slot", "perfume", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("payment_reference",)
    show_full_result_count = False
    list_select_related = ("machine_slot__machine", "perfume")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "method", "amount", "status", "paid_at")
    list_filter = ("method", "status")
    search_fields = ("provider_transaction_id",)
    show_full_result_count = False


@admin.register(DispenseTransaction)
class DispenseTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "command_id", "status", "error_message", "executed_at")
    list_filter = ("status",)
    search_fields = ("command_id",)
    show_full_result_count = False

from django.conf import settings
from django.db import models
from django.utils import timezone


class InventoryLog(models.Model):
    class ChangeType(models.TextChoices):
        SALE = "SALE", "Ban hang (xit)"
        REFILL = "REFILL", "Nap lai chai"
        ADJUSTMENT = "ADJUSTMENT", "Dieu chinh ton kho"

    id = models.AutoField(primary_key=True, db_column="InventoryLogID")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, db_column="UserID", related_name="inventory_logs",
        blank=True, null=True,
    )
    machine_slot = models.ForeignKey(
        "devices.MachineSlot", models.PROTECT, db_column="MachineSlotID", related_name="inventory_logs"
    )
    order = models.ForeignKey(
        "sales.Order", models.SET_NULL, db_column="OrderID", related_name="inventory_logs", blank=True, null=True
    )
    change_type = models.CharField(max_length=30, choices=ChangeType.choices)
    quantity_before = models.IntegerField()
    quantity_after = models.IntegerField()
    change_amount = models.IntegerField()
    reason = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "InventoryLog"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.change_type} {self.change_amount} (slot {self.machine_slot_id})"

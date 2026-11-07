from django.conf import settings
from django.db import models
from django.utils import timezone


class MaintenanceRecord(models.Model):
    class Type(models.TextChoices):
        INSPECTION = "INSPECTION", "Kiem tra"
        REPAIR = "REPAIR", "Sua chua"
        REFILL_SUPPORT = "REFILL_SUPPORT", "Ho tro nap chai"
        PART_REPLACEMENT = "PART_REPLACEMENT", "Thay linh kien"
        CALIBRATION = "CALIBRATION", "Hieu chuan"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Moi"
        IN_PROGRESS = "IN_PROGRESS", "Dang xu ly"
        COMPLETED = "COMPLETED", "Hoan thanh"
        CANCELLED = "CANCELLED", "Da huy"

    id = models.AutoField(primary_key=True, db_column="MaintenanceRecordID")
    alert = models.ForeignKey(
        "devices.Alert", models.SET_NULL, db_column="AlertID", related_name="maintenance_records",
        blank=True, null=True,
    )
    machine = models.ForeignKey(
        "devices.Machine", models.PROTECT, db_column="MachineID", related_name="maintenance_records"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.PROTECT, db_column="CreatedByUserID", related_name="created_tickets"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, db_column="AssignedToUserID", related_name="assigned_tickets",
        blank=True, null=True,
    )
    maintenance_type = models.CharField(max_length=30, choices=Type.choices)
    description = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "MaintenanceRecord"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Ticket {self.id} ({self.maintenance_type}) - {self.status}"

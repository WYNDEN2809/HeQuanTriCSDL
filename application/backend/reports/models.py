from django.conf import settings
from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    id = models.AutoField(primary_key=True, db_column="AuditLogID")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, db_column="UserID", related_name="audit_logs",
        blank=True, null=True,
    )
    brand = models.ForeignKey(
        "catalog.Brand", models.SET_NULL, db_column="BrandID", related_name="audit_logs", blank=True, null=True
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50, blank=True, null=True)
    entity_id = models.IntegerField(blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "AuditLog"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"

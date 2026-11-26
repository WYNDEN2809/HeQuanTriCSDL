# Generated for the existing SQL Server AuditLog table. The model is unmanaged,
# so this migration records Django's model state without creating the table.
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.AutoField(db_column="AuditLogID", primary_key=True, serialize=False)),
                (
                    "action",
                    models.CharField(max_length=100),
                ),
                ("entity_type", models.CharField(blank=True, max_length=50, null=True)),
                ("entity_id", models.IntegerField(blank=True, null=True)),
                ("old_value", models.TextField(blank=True, null=True)),
                ("new_value", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "brand",
                    models.ForeignKey(
                        blank=True,
                        db_column="BrandID",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to="catalog.brand",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_column="UserID",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "AuditLog", "managed": False, "ordering": ["-created_at"]},
        ),
    ]

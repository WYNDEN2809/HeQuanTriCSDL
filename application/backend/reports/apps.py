from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "reports"
    verbose_name = "Bao cao va audit"

    def ready(self):
        from . import signals  # noqa: F401  (dang ky ghi audit log khi dang nhap/dang xuat)

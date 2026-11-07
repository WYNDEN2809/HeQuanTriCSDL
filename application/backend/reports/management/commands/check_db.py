from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

PROJECT_APPS = ["accounts", "catalog", "devices", "sales", "inventory", "maintenance", "reports"]


class Command(BaseCommand):
    help = "Kiem tra ket noi SQL Server va dem so dong cua 15 bang ScentStation (doi chieu model <-> bang that)."

    def handle(self, *args, **opts):
        with connection.cursor() as cur:
            cur.execute("SELECT DB_NAME()")
            self.stdout.write(f"Da ket noi database: {cur.fetchone()[0]}\n")

        ok = True
        total_models = 0
        for label in PROJECT_APPS:
            for model in apps.get_app_config(label).get_models():
                total_models += 1
                try:
                    n = model.objects.count()
                    self.stdout.write(f"  {model._meta.db_table:<22} {n:>8} dong")
                except Exception as exc:  # cot/bang khong khop
                    ok = False
                    self.stdout.write(self.style.ERROR(f"  {model._meta.db_table:<22} LOI: {exc}"))

        if ok:
            self.stdout.write(self.style.SUCCESS(f"\nOK - {total_models} model khop voi bang trong database."))
        else:
            self.stdout.write(self.style.ERROR("\nCo model khong khop voi bang that. Xem loi o tren."))

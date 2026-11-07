from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = (
        "Dat lai mat khau cho TAT CA user mau bang co che hash cua Django "
        "(mat khau mau trong SQL la SHA-256 nen Django khong dang nhap duoc)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--password", default="ScentStation@2026", help="Mat khau moi cho moi user")

    def handle(self, *args, **opts):
        password = opts["password"]
        count = 0
        for user_id in User.objects.values_list("id", flat=True):
            User.objects.filter(pk=user_id).update(password=make_password(password))
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Da dat lai mat khau cho {count} user thanh: {password}"))

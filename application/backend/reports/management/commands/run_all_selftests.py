import io

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

COMMANDS = [
    ("selftest_sales", "Ban hang, webhook, lenh xit (Buoc 2)"),
    ("selftest_machines", "May va slot"),
    ("selftest_inventory", "Ton kho va refill"),
    ("selftest_alerts", "Canh bao va bao cao"),
    ("selftest_transactions", "Giao dich: hoan tien, review, thu lai, doi chieu"),
    ("selftest_maintenance", "Phieu bao tri va checklist"),
    ("selftest_accounts", "Nhan vien, vai tro, tenant, danh muc"),
]


class Command(BaseCommand):
    help = "Chay tat ca cac lenh selftest_* va in tong ket (moi lenh deu rollback, khong de lai du lieu)."

    def handle(self, *args, **opts):
        total_pass = total_fail = 0
        failed_cmds = []
        for name, label in COMMANDS:
            buf = io.StringIO()
            try:
                call_command(name, stdout=buf, no_color=True)
            except CommandError as exc:
                self.stdout.write(f"- {name:<24} BO QUA ({exc})")
                continue
            except Exception as exc:  # loi bat ngo trong luc test
                self.stdout.write(self.style.ERROR(f"- {name:<24} LOI: {exc!r}"))
                failed_cmds.append(name)
                continue
            text = buf.getvalue()
            p, f = text.count("[PASS]"), text.count("[FAIL]")
            total_pass += p
            total_fail += f
            status = self.style.SUCCESS("OK  ") if f == 0 and p else self.style.ERROR("LOI ")
            self.stdout.write(f"- {name:<24} {status} {p} dat, {f} loi   ({label})")
            if f or not p:
                failed_cmds.append(name)
                for line in text.splitlines():
                    if "[FAIL]" in line:
                        self.stdout.write("      " + line.strip())
        summary = f"\nTONG: {total_pass} dat, {total_fail} loi."
        ok = total_fail == 0 and not failed_cmds
        self.stdout.write(self.style.SUCCESS(summary) if ok else self.style.ERROR(summary))

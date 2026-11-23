from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from devices import machine_services as svc
from devices.models import Machine, MachineSlot
from maintenance.models import MaintenanceRecord
from reports.models import AuditLog


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu nghiep vu may/slot (Nguoi 2) tren DB that, co ROLLBACK."

    def handle(self, *args, **opts):
        self.results = []
        try:
            with transaction.atomic():
                self._run()
                raise _Rollback()
        except _Rollback:
            pass
        ok = sum(1 for _, p, _ in self.results if p)
        for name, passed, detail in self.results:
            mark = self.style.SUCCESS("PASS") if passed else self.style.ERROR("FAIL")
            self.stdout.write(f" [{mark}] {name}" + (f" -> {detail}" if detail and not passed else ""))
        line = f"\n{ok}/{len(self.results)} kiem tra dat."
        self.stdout.write(self.style.SUCCESS(line) if ok == len(self.results) else self.style.ERROR(line))

    def check(self, name, cond, detail=""):
        self.results.append((name, bool(cond), detail))

    def raises(self, fn, *a, **kw):
        try:
            fn(*a, **kw)
        except PortalError:
            return True
        return False

    def _run(self):
        machine = Machine.objects.exclude(status=Machine.Status.DISABLED).order_by("id").first()
        user = BrandMember.objects.filter(brand_id=machine.brand_id, brand_role="OPS_MANAGER").select_related("user").first().user
        Machine.objects.filter(pk=machine.pk).update(status=Machine.Status.ONLINE)
        machine.refresh_from_db()
        # Du lieu mau co san nhieu phieu dang mo -> huy tam (se rollback) de kiem tra quy tac ra khoi bao tri
        MaintenanceRecord.objects.filter(machine_id=machine.pk, status__in=["OPEN", "IN_PROGRESS"]).update(status="CANCELLED")

        self.check("Tat may ma khong co ly do bi tu choi", self.raises(svc.disable_machine, machine, user, ""))
        svc.disable_machine(machine, user, "kiem thu")
        machine.refresh_from_db()
        self.check("Tat may -> DISABLED", machine.status == Machine.Status.DISABLED)
        self.check("Tat may duoc ghi audit", AuditLog.objects.filter(action="MACHINE_STATUS_CHANGE", entity_id=machine.pk).exists())
        self.check("Tat may lan 2 bi tu choi", self.raises(svc.disable_machine, machine, user, "x"))
        svc.enable_machine(machine, user)
        machine.refresh_from_db()
        self.check("Bat lai may -> OFFLINE (cho heartbeat)", machine.status == Machine.Status.OFFLINE)
        self.check("Khong bat lai may dang khong tat", self.raises(svc.enable_machine, machine, user))

        svc.enter_maintenance(machine, user, "kiem thu")
        machine.refresh_from_db()
        self.check("Vao che do bao tri -> MAINTENANCE", machine.status == Machine.Status.MAINTENANCE)
        ticket = MaintenanceRecord.objects.create(
            machine_id=machine.pk, created_by=user, maintenance_type="INSPECTION", description="test", status="OPEN")
        self.check("Con phieu bao tri chua dong thi KHONG ra khoi bao tri", self.raises(svc.exit_maintenance, machine, user))
        MaintenanceRecord.objects.filter(pk=ticket.pk).update(status="COMPLETED")
        svc.exit_maintenance(machine, user)
        machine.refresh_from_db()
        self.check("Het phieu mo -> ra khoi bao tri", machine.status == Machine.Status.OFFLINE)

        slot = MachineSlot.objects.select_related("machine").filter(machine_id=machine.pk).order_by("slot_number").first()
        MachineSlot.objects.filter(pk=slot.pk).update(quantity=500, capacity=1000, low_stock_threshold=50, status="ACTIVE")
        slot.refresh_from_db()
        slot.machine = machine
        self.check("Gia am bi tu choi", self.raises(svc.configure_slot, slot, user, -1, 50, 400))
        self.check("Nguong vuot suc chua bi tu choi", self.raises(svc.configure_slot, slot, user, 20000, 5000, 400))
        self.check("Thoi gian xit ngoai khoang bi tu choi", self.raises(svc.configure_slot, slot, user, 20000, 50, 10))
        self.check("Khong thay doi gi bi tu choi",
                   self.raises(svc.configure_slot, slot, user, slot.price_per_spray, slot.low_stock_threshold, slot.spray_duration))
        svc.configure_slot(slot, user, 33000, 600, 450, "doi gia")
        slot.refresh_from_db()
        self.check("Doi gia/nguong duoc luu", int(slot.price_per_spray) == 33000 and slot.low_stock_threshold == 600)
        self.check("Ton 500 <= nguong 600 -> LOW_STOCK", slot.status == MachineSlot.Status.LOW_STOCK, slot.status)
        self.check("Doi gia duoc ghi audit (co gia cu/moi)",
                   AuditLog.objects.filter(action="SLOT_CONFIG_CHANGE", entity_id=slot.pk).exists())
        slot.machine = machine
        self.check("Tat slot khong ly do bi tu choi", self.raises(svc.set_slot_enabled, slot, False, user, ""))
        svc.set_slot_enabled(slot, False, user, "kiem thu")
        slot.refresh_from_db()
        self.check("Tat slot -> DISABLED", slot.status == MachineSlot.Status.DISABLED)
        slot.machine = machine
        svc.set_slot_enabled(slot, True, user)
        slot.refresh_from_db()
        self.check("Bat slot -> tinh lai theo ton kho", slot.status == MachineSlot.Status.LOW_STOCK, slot.status)

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from catalog.models import Perfume
from devices.models import Alert, Machine, MachineSlot
from inventory import services
from inventory.models import InventoryLog
from reports.models import AuditLog


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu ton kho/refill (Nguoi 2) tren DB that, co ROLLBACK."

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

    def raises(self, fn, *a):
        try:
            fn(*a)
        except PortalError:
            return True
        return False

    def fresh(self, slot):
        return MachineSlot.objects.select_related("machine", "perfume").get(pk=slot.pk)

    def _run(self):
        slot = MachineSlot.objects.select_related("machine", "perfume").order_by("id").first()
        user = BrandMember.objects.filter(brand_id=slot.machine.brand_id, brand_role="INVENTORY_STAFF").select_related("user").first().user
        MachineSlot.objects.filter(pk=slot.pk).update(quantity=500, capacity=1000, low_stock_threshold=50, status="ACTIVE")
        slot = self.fresh(slot)

        self.check("Nap khong co ly do bi tu choi", self.raises(services.refill_slot, slot, user, 800, ""))
        self.check("Nap so luong nho hon ton hien tai bi tu choi", self.raises(services.refill_slot, slot, user, 400, "x"))
        self.check("Nap vuot suc chua bi tu choi", self.raises(services.refill_slot, slot, user, 1500, "x"))

        Alert.objects.create(machine_id=slot.machine_id, machine_slot_id=slot.pk, alert_type="LOW_STOCK", severity="MEDIUM", status="OPEN")
        services.refill_slot(slot, user, 800, "Nạp định kỳ")
        slot = self.fresh(slot)
        self.check("Nap -> ton kho 800", slot.quantity == 800)
        self.check("Co InventoryLog REFILL dung truoc/sau",
                   InventoryLog.objects.filter(machine_slot=slot, change_type="REFILL", quantity_before=500, quantity_after=800, change_amount=300).exists())
        self.check("Nap duoc ghi audit", AuditLog.objects.filter(action="REFILL_SLOT", entity_id=slot.pk).exists())
        self.check("Nap dong canh bao LOW_STOCK dang mo",
                   not Alert.objects.filter(machine_slot_id=slot.pk, alert_type="LOW_STOCK").exclude(status="RESOLVED").exists())

        other_brand = Perfume.objects.exclude(brand_id=slot.machine.brand_id).first()
        self.check("Thay chai bang mui huong cua brand khac bi tu choi",
                   self.raises(services.replace_bottle, slot, user, other_brand.pk, 900, "x"))
        same = Perfume.objects.filter(brand_id=slot.machine.brand_id, is_active=True).exclude(pk=slot.perfume_id).first()
        services.replace_bottle(slot, user, same.pk, 900, "Thay chai moi")
        slot = self.fresh(slot)
        self.check("Thay chai doi mui huong va ton kho", slot.perfume_id == same.pk and slot.quantity == 900)
        self.check("Co InventoryLog REPLACE", InventoryLog.objects.filter(machine_slot=slot, change_type="REPLACE").exists())

        self.check("Doi chieu bang dung ton hien tai bi tu choi", self.raises(services.adjust_inventory, slot, user, 900, "x"))
        loss = services.adjust_inventory(slot, user, 300, "Hao hut bat thuong")
        slot = self.fresh(slot)
        self.check("Doi chieu -> ton kho 300 va chenh lech 600", slot.quantity == 300 and loss == 600)
        self.check("Co InventoryLog ADJUSTMENT", InventoryLog.objects.filter(machine_slot=slot, change_type="ADJUSTMENT").exists())
        self.check("Hao hut lon -> canh bao LEAKAGE_SUSPECTED",
                   Alert.objects.filter(machine_slot_id=slot.pk, alert_type="LEAKAGE_SUSPECTED").exclude(status="RESOLVED").exists())
        services.adjust_inventory(slot, user, 10, "Do lai")
        self.check("Ton 10 <= nguong 50 -> LOW_STOCK", self.fresh(slot).status == "LOW_STOCK")
        services.adjust_inventory(self.fresh(slot), user, 0, "Het hang")
        self.check("Ton 0 -> EMPTY", self.fresh(slot).status == "EMPTY")
        self.check("Ly do tieng Viet duoc bo dau khi luu vao cot VARCHAR",
                   InventoryLog.objects.filter(machine_slot=slot, reason="Nap dinh ky").exists())

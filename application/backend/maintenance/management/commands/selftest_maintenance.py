from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import BrandMember
from accounts.portal_utils import PortalError
from devices.models import Alert, Machine, MachineSlot
from devices.services import can_accept_orders, raise_alert
from inventory.models import InventoryLog
from maintenance import services as svc
from maintenance.checklists import POST_TEST_TEXT
from maintenance.models import MaintenanceChecklistItem as Item
from maintenance.models import MaintenanceRecord as Record
from reports.models import AuditLog
from django.utils import timezone


class _Rollback(Exception):
    pass


class Command(BaseCommand):
    help = "Tu kiem thu vong doi phieu bao tri (Nguoi 5) tren DB that, co ROLLBACK."

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

    def fresh(self, model, pk):
        return model.objects.select_related("machine").get(pk=pk) if model is Record else model.objects.get(pk=pk)

    def _run(self):
        machine = Machine.objects.exclude(status="DISABLED").order_by("id").first()
        Machine.objects.filter(pk=machine.pk).update(status="ONLINE", last_seen_at=timezone.now())
        machine = Machine.objects.get(pk=machine.pk)
        # Du lieu mau co san nhieu phieu dang mo -> huy tam (se rollback) de kiem tra viec tra may ve hoat dong
        Record.objects.filter(machine_id=machine.pk, status__in=["OPEN", "IN_PROGRESS"]).update(status="CANCELLED")
        members = BrandMember.objects.filter(brand_id=machine.brand_id).select_related("user")
        ops = members.filter(brand_role="OPS_MANAGER").first().user
        techs = [m.user for m in members.filter(brand_role="TECHNICIAN")]
        tech, other_tech = techs[0], techs[1]
        inv_user = members.filter(brand_role="INVENTORY_STAFF").first().user
        slot = MachineSlot.objects.filter(machine_id=machine.pk).order_by("slot_number").first()
        MachineSlot.objects.filter(pk=slot.pk).update(quantity=500, status="ACTIVE")

        # 1) Tao phieu + checklist
        t = svc.create_ticket(machine, ops, "REPAIR", "May bi ket dau phun / máy kẹt đầu phun", "MEDIUM")
        t = self.fresh(Record, t.pk)
        items = list(Item.objects.filter(record_id=t.pk))
        self.check("Tao phieu -> OPEN, uu tien MEDIUM, mo ta khong dau", t.status == "OPEN" and svc.priority_of(t) == "MEDIUM" and "ẹ" not in t.description)
        self.check("Phieu co checklist day du (co muc test sau bao tri va muc ket qua)",
                   any(i.item_text == POST_TEST_TEXT for i in items) and any(i.phase == "RESULT" for i in items) and len(items) >= 8)
        self.check("Tao phieu duoc ghi audit", AuditLog.objects.filter(action="TICKET_CREATE", entity_id=t.pk).exists())
        self.check("Giao cho nguoi khong phai ky thuat vien bi tu choi", self.raises(svc.assign_ticket, t, ops, ops))
        svc.assign_ticket(t, tech, ops)
        t = self.fresh(Record, t.pk)
        self.check("Giao viec cho ky thuat vien", t.assigned_to_id == tech.pk)
        self.check("Bat dau bao tri bi tu choi neu la ky thuat vien khac", self.raises(svc.start_ticket, t, other_tech))

        # 2) Bat dau -> may vao che do bao tri
        self.check("Chua bat dau thi khong tick duoc checklist", self.raises(svc.set_item, t, items[0].pk, True, tech))
        svc.start_ticket(t, tech)
        t = self.fresh(Record, t.pk)
        m = Machine.objects.get(pk=machine.pk)
        self.check("Bat dau -> phieu IN_PROGRESS va may MAINTENANCE", t.status == "IN_PROGRESS" and m.status == "MAINTENANCE")
        self.check("May dang bao tri khong nhan don moi", not can_accept_orders(m))

        # 3) Khong the dong khi thieu
        self.check("Dong phieu khi checklist chua xong bi tu choi", self.raises(svc.complete_ticket, t, tech))
        post = next(i for i in items if i.item_text == POST_TEST_TEXT)
        self.check("Khong tick tay muc 'xit thu sau bao tri'", self.raises(svc.set_item, t, post.pk, True, tech))
        result_item = next(i for i in items if i.phase == "RESULT")
        self.check("Khong tick tay muc ket qua", self.raises(svc.set_item, t, result_item.pk, True, tech))
        for it in items:
            if it.phase not in ("RESULT",) and it.item_text != POST_TEST_TEXT:
                svc.set_item(t, it.pk, True, tech, "ok")
        self.check("Tick xong cac muc thuong van chua dong duoc (thieu test sau bao tri)", self.raises(svc.complete_ticket, t, tech))

        # 4) Xit thu ghi rieng
        qty0 = MachineSlot.objects.get(pk=slot.pk).quantity
        other_slot = MachineSlot.objects.exclude(machine_id=machine.pk).first()
        self.check("Xit thu o slot cua may khac bi tu choi", self.raises(svc.test_spray, t, tech, other_slot.pk, "diag"))
        svc.test_spray(t, tech, slot.pk, "diag", True, "kiem tra")
        self.check("Xit thu chan doan tru ton kho 1", MachineSlot.objects.get(pk=slot.pk).quantity == qty0 - 1)
        self.check("Xit thu ghi rieng loai DIAGNOSTIC_SPRAY, khong gan don hang",
                   InventoryLog.objects.filter(machine_slot_id=slot.pk, change_type="DIAGNOSTIC_SPRAY", order__isnull=True).exists())
        self.check("Xit thu khong tao log SALE", not InventoryLog.objects.filter(machine_slot_id=slot.pk, change_type="SALE", created_at__gte=t.created_at).exists())
        self.check("Xit thu duoc ghi audit", AuditLog.objects.filter(action="DIAGNOSTIC_SPRAY", entity_id=t.pk).exists())
        svc.test_spray(t, tech, slot.pk, "post", False, "chua dat")
        self.check("Xit thu sau bao tri KHONG dat -> muc chua duoc tick", not Item.objects.get(pk=post.pk).is_done)
        self.check("Chua dat thi khong dong phieu duoc", self.raises(svc.complete_ticket, t, tech))
        svc.test_spray(t, tech, slot.pk, "post", True, "dat")
        self.check("Xit thu sau bao tri dat -> tick muc test", Item.objects.get(pk=post.pk).is_done)

        # 5) Ket qua bat buoc
        self.check("Ghi ket qua rong bi tu choi", self.raises(svc.record_result, t, tech, ""))
        self.check("Dong phieu khi chua ghi ket qua bi tu choi", self.raises(svc.complete_ticket, t, tech))
        svc.record_result(t, tech, "Thay dau phun, da hieu chuan")
        svc.complete_ticket(t, tech)
        t = self.fresh(Record, t.pk)
        m = Machine.objects.get(pk=machine.pk)
        self.check("Dong phieu -> COMPLETED co thoi diem hoan thanh", t.status == "COMPLETED" and t.completed_at is not None)
        self.check("Het phieu mo -> may tra ve OFFLINE (cho heartbeat)", m.status == "OFFLINE")
        self.check("Phieu hoan thanh duoc ghi audit", AuditLog.objects.filter(action="TICKET_COMPLETE", entity_id=t.pk).exists())
        self.check("Dong phieu lan 2 bi tu choi", self.raises(svc.complete_ticket, t, tech))

        # 6) Phieu CRITICAL khoa may
        Machine.objects.filter(pk=machine.pk).update(status="ONLINE", last_seen_at=timezone.now())
        machine = Machine.objects.get(pk=machine.pk)
        crit = svc.create_ticket(machine, ops, "REPAIR", "Ro ri nghiem trong", "CRITICAL", tech)
        m = Machine.objects.get(pk=machine.pk)
        self.check("Phieu CRITICAL -> may ERROR, khong nhan don moi", m.status == "ERROR" and not can_accept_orders(m))
        svc.cancel_ticket(self.fresh(Record, crit.pk), ops, "Nhap nham")
        m = Machine.objects.get(pk=machine.pk)
        self.check("Huy phieu CRITICAL (khong con phieu mo) -> may OFFLINE", m.status == "OFFLINE")
        self.check("Huy phieu da dong bi tu choi", self.raises(svc.cancel_ticket, self.fresh(Record, crit.pk), ops, "x"))

        # 7) Tu dong tao phieu tu canh bao
        Machine.objects.filter(pk=machine.pk).update(status="ONLINE", last_seen_at=timezone.now())
        alert = Alert.objects.create(machine_id=machine.pk, alert_type="SENSOR_FAILURE", severity="HIGH", status="OPEN")
        t1 = svc.create_ticket_from_alert(alert, created_by=ops)
        t2 = svc.create_ticket_from_alert(alert, created_by=ops)
        self.check("Tao phieu tu canh bao khong bi trung", t1.pk == t2.pk)
        self.check("Loai bao tri suy ra tu loai canh bao", t1.maintenance_type == "PART_REPLACEMENT")
        self.check("Uu tien suy ra tu muc do canh bao (HIGH)", svc.priority_of(self.fresh(Record, t1.pk)) == "HIGH")
        Machine.objects.filter(pk=machine.pk).update(status="ONLINE")
        created = raise_alert(machine.pk, "LEAKAGE_SUSPECTED", "CRITICAL", slot.pk)
        auto = Record.objects.filter(alert_id=created.pk).first() if created else None
        self.check("Canh bao CRITICAL (ro ri) tu dong tao phieu bao tri", auto is not None)
        self.check("Phieu tu dong khoa may (ERROR)", Machine.objects.get(pk=machine.pk).status == "ERROR")
        self.check("Giao cho ky thuat vien khac brand bi tu choi", self.raises(svc.assign_ticket, self.fresh(Record, t1.pk), BrandMember.objects.exclude(brand_id=machine.brand_id).filter(brand_role="TECHNICIAN").first().user, ops))

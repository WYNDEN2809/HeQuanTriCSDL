import hmac
import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime

from django.core.management.base import BaseCommand

from devices.models import Machine, MachineSlot
from devices.services import mark_stale_machines_offline
from sales.security import device_token, sign_command
from sales.services import expire_stale


class Command(BaseCommand):
    help = (
        "Gia lap cac may kiosk: gui heartbeat, nhan lenh xit qua HTTP API, kiem tra an toan "
        "(chu ky, han lenh, cua, ton kho, bao tri), xac nhan roi tra ket qua. Phai chay song song voi 'runserver'."
    )

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default="http://127.0.0.1:8000")
        parser.add_argument("--machines", nargs="*", help="Serial cac may can gia lap (mac dinh: may dang ONLINE)")
        parser.add_argument("--limit", type=int, default=6, help="So may toi da khi khong chi dinh --machines")
        parser.add_argument("--interval", type=float, default=1.0, help="Chu ky hoi lenh (giay)")
        parser.add_argument("--fail-rate", type=float, default=0.05, help="Ti le xit loi co khi (0-1)")
        parser.add_argument("--uncertain-rate", type=float, default=0.02, help="Ti le mat ket qua sau khi ack (0-1)")
        parser.add_argument("--door-open-rate", type=float, default=0.03, help="Ti le cua dang mo (0-1)")
        parser.add_argument("--no-monitor", action="store_true", help="Khong chay giam sat heartbeat/het han")

    # ------------------------------------------------------------ HTTP
    def _call(self, method, path, token, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            self.base_url + path, data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            try:
                body = json.loads(exc.read().decode("utf-8") or "{}")
            except ValueError:
                body = {}
            return exc.code, body

    def log(self, serial, msg):
        self.stdout.write(f"[{datetime.now():%H:%M:%S}] {serial}: {msg}")

    # ------------------------------------------------------------ main
    def handle(self, *args, **o):
        self.base_url = o["base_url"].rstrip("/")
        self.opts = o
        if o["machines"]:
            serials = o["machines"]
        else:
            serials = list(
                Machine.objects.filter(status=Machine.Status.ONLINE).order_by("id")
                .values_list("serial_number", flat=True)[: o["limit"]]
            )
        if not serials:
            self.stdout.write(self.style.ERROR("Khong co may nao de gia lap."))
            return
        self.stdout.write(self.style.SUCCESS(f"Dang gia lap {len(serials)} may: {', '.join(serials)}  (Ctrl+C de dung)"))

        last_monitor = 0.0
        try:
            while True:
                for serial in serials:
                    try:
                        self._tick(serial)
                    except urllib.error.URLError:
                        self.log(serial, "KHONG ket noi duoc server - 'runserver' da chay chua?")
                if not o["no_monitor"] and time.time() - last_monitor >= 5:
                    last_monitor = time.time()
                    n = mark_stale_machines_offline()
                    expire_stale()
                    if n:
                        self.stdout.write(f"[monitor] {n} may mat heartbeat -> OFFLINE")
                time.sleep(o["interval"])
        except KeyboardInterrupt:
            self.stdout.write("\nDa dung gia lap.")

    # ------------------------------------------------------------ mot vong cua 1 may
    def _tick(self, serial):
        token = device_token(serial)
        code, _ = self._call("POST", f"/api/device/{serial}/heartbeat/", token, {})
        if code != 200:
            self.log(serial, f"heartbeat bi tu choi (HTTP {code})")
            return
        code, body = self._call("GET", f"/api/device/{serial}/commands/", token)
        if code != 200:
            return
        for cmd in body.get("commands", []):
            self._handle_command(serial, token, cmd)

    def _handle_command(self, serial, token, cmd):
        cid = cmd["command_id"]
        base = f"/api/device/{serial}/commands/{cid}"
        o = self.opts

        def reject(reason):
            self.log(serial, f"TU CHOI lenh {cid[:12]}...: {reason}")
            self._call("POST", f"{base}/result/", token, {"success": False, "error": reason})

        # 1) chu ky lenh
        expected = sign_command(cid, serial, cmd["slot_number"], cmd["spray_duration"], cmd["expires_at"])
        if not hmac.compare_digest(expected, cmd.get("signature", "")):
            return reject("Invalid command signature")
        # 2) han lenh
        if datetime.fromisoformat(cmd["expires_at"]) <= datetime.now():
            return reject("Command expired")
        # 3) che do bao tri / cua mo
        machine = Machine.objects.get(serial_number=serial)
        if machine.status == Machine.Status.MAINTENANCE:
            return reject("Machine is in maintenance mode")
        if random.random() < o["door_open_rate"]:
            return reject("Door is open")
        # 4) cam bien ton kho cua slot
        slot = MachineSlot.objects.filter(machine=machine, slot_number=cmd["slot_number"]).first()
        if slot is None or slot.quantity <= 0:
            return reject("Slot is empty")
        # 5) xac nhan lenh truoc khi thuc thi
        code, _ = self._call("POST", f"{base}/ack/", token, {})
        if code != 200:
            self.log(serial, f"ack bi tu choi (HTTP {code}) - bo qua lenh")
            return
        # 6) mo phong mat ket qua (server se danh dau UNCERTAIN -> REVIEW, khong xit lai)
        if random.random() < o["uncertain_rate"]:
            self.log(serial, f"da ack lenh {cid[:12]}... nhung MAT KET QUA (mo phong mang loi)")
            return
        # 7) xit dung 1 chu ky
        time.sleep(min(cmd["spray_duration"], 2000) / 1000.0)
        if random.random() < o["fail_rate"]:
            self._call("POST", f"{base}/result/", token, {"success": False, "error": "Actuator timeout"})
            self.log(serial, f"slot {cmd['slot_number']}: XIT LOI (Actuator timeout)")
        else:
            self._call("POST", f"{base}/result/", token, {"success": True})
            self.log(serial, f"slot {cmd['slot_number']}: xit thanh cong")

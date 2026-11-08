"""API cho thiet bi kiosk (xac thuc bang Bearer token = HMAC(secret, serial))."""
import json
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from sales.security import verify_device_token
from sales.services import device_ack, device_report_result, pending_commands_for, serialize_command

from .models import Machine
from .services import record_heartbeat


def device_api(view):
    """Tu choi thiet bi chua dang ky, token sai, hoac da bi thu hoi (may DISABLED)."""

    @wraps(view)
    def wrapper(request, serial, *args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        machine = Machine.objects.filter(serial_number=serial).first()
        if machine is None or not verify_device_token(serial, token):
            return JsonResponse({"result": "unauthorized"}, status=401)
        if machine.status == Machine.Status.DISABLED:
            return JsonResponse({"result": "device_revoked"}, status=403)
        return view(request, machine, *args, **kwargs)

    return csrf_exempt(wrapper)


def _json_body(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
        return data if isinstance(data, dict) else {}
    except (ValueError, UnicodeDecodeError):
        return {}


@device_api
@require_POST
def heartbeat(request, machine):
    now = record_heartbeat(machine)
    return JsonResponse({"result": "ok", "server_time": now.isoformat()})


@device_api
@require_GET
def commands(request, machine):
    return JsonResponse({"commands": [serialize_command(c, machine) for c in pending_commands_for(machine)]})


@device_api
@require_POST
def ack(request, machine, command_id):
    code, body = device_ack(machine, command_id)
    return JsonResponse(body, status=code)


@device_api
@require_POST
def result(request, machine, command_id):
    data = _json_body(request)
    code, body = device_report_result(
        machine, command_id, success=bool(data.get("success")), error=str(data.get("error") or "")
    )
    return JsonResponse(body, status=code)

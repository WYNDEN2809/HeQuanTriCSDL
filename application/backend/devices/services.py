import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import Alert, DeviceEvent, Machine

logger = logging.getLogger(__name__)


def machine_connectivity(machine, now=None):
    """'online' / 'unstable' / 'offline' dua tren heartbeat gan nhat."""
    now = now or timezone.now()
    if machine.last_seen_at is None:
        return "offline"
    age = (now - machine.last_seen_at).total_seconds()
    if age <= settings.HEARTBEAT_ONLINE_SECONDS:
        return "online"
    if age <= settings.HEARTBEAT_OFFLINE_SECONDS:
        return "unstable"
    return "offline"


def can_accept_orders(machine):
    return machine.status == Machine.Status.ONLINE and machine_connectivity(machine) == "online"


def raise_alert(machine_id, alert_type, severity, slot_id=None):
    """Tao canh bao, KHONG tao trung neu van con canh bao cung loai chua xu ly."""
    exists = (
        Alert.objects.filter(machine_id=machine_id, alert_type=alert_type, machine_slot_id=slot_id)
        .exclude(status=Alert.Status.RESOLVED)
        .exists()
    )
    if exists:
        return None
    alert = Alert.objects.create(
        machine_id=machine_id,
        machine_slot_id=slot_id,
        alert_type=alert_type,
        severity=severity,
        status=Alert.Status.OPEN,
        created_at=timezone.now(),
    )
    _auto_ticket(alert)
    from reports.notifications import notify_alert_created
    notify_alert_created(alert)
    return alert


# Loai canh bao nghiem trong tu dong tao phieu bao tri (co the cau hinh bang AUTO_TICKET_ALERT_TYPES trong settings)
DEFAULT_AUTO_TICKET_TYPES = ("LEAKAGE_SUSPECTED", "ACTUATOR_FAILURE", "SENSOR_FAILURE")


def _auto_ticket(alert):
    """Canh bao CRITICAL thuoc loai da cau hinh -> tu dong tao phieu bao tri (dich vu cua module bao tri)."""
    types = getattr(settings, "AUTO_TICKET_ALERT_TYPES", DEFAULT_AUTO_TICKET_TYPES)
    if alert.severity != Alert.Severity.CRITICAL or alert.alert_type not in types:
        return None
    try:
        from maintenance.services import create_ticket_from_alert
    except ImportError:  # module bao tri chua duoc cai
        return None
    try:
        return create_ticket_from_alert(alert)
    except Exception:  # khong de loi tao phieu lam hong luong chinh
        logger.exception("Khong tu dong tao duoc phieu bao tri cho canh bao %s", alert.pk)
        return None


def record_heartbeat(machine):
    """Cap nhat heartbeat. May OFFLINE ket noi lai se tro thanh ONLINE va dong canh bao mat ket noi."""
    now = timezone.now()
    fields = {"last_seen_at": now}
    reconnected = machine.status == Machine.Status.OFFLINE
    if reconnected:
        fields["status"] = Machine.Status.ONLINE
    Machine.objects.filter(pk=machine.pk).update(**fields)
    if reconnected:
        DeviceEvent.objects.create(
            machine_id=machine.pk, event_type=DeviceEvent.EventType.RECONNECT,
            message="Machine reconnected", created_at=now,
        )
        Alert.objects.filter(machine_id=machine.pk, alert_type=Alert.Type.MACHINE_OFFLINE).exclude(
            status=Alert.Status.RESOLVED
        ).update(status=Alert.Status.RESOLVED, resolved_at=now)
    return now


def mark_stale_machines_offline(now=None):
    """May ONLINE ma khong con heartbeat qua han -> OFFLINE + su kien + canh bao. Tra ve so may bi doi."""
    now = now or timezone.now()
    cutoff = now - timedelta(seconds=settings.HEARTBEAT_OFFLINE_SECONDS)
    stale = list(
        Machine.objects.filter(status=Machine.Status.ONLINE).filter(
            Q(last_seen_at__lt=cutoff) | Q(last_seen_at__isnull=True)
        )
    )
    changed = 0
    for m in stale:
        n = Machine.objects.filter(pk=m.pk, status=Machine.Status.ONLINE).update(status=Machine.Status.OFFLINE)
        if n:
            changed += 1
            DeviceEvent.objects.create(
                machine_id=m.pk, event_type=DeviceEvent.EventType.HEARTBEAT_LOST,
                message="No heartbeat received", created_at=now,
            )
            raise_alert(m.pk, Alert.Type.MACHINE_OFFLINE, Alert.Severity.HIGH)
    return changed

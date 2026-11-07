from django.db import models
from django.utils import timezone


class Machine(models.Model):
    class Status(models.TextChoices):
        ONLINE = "ONLINE", "Online"
        OFFLINE = "OFFLINE", "Offline"
        MAINTENANCE = "MAINTENANCE", "Dang bao tri"
        DISABLED = "DISABLED", "Da tat"
        ERROR = "ERROR", "Loi"

    id = models.AutoField(primary_key=True, db_column="MachineID")
    brand = models.ForeignKey("catalog.Brand", models.PROTECT, db_column="BrandID", related_name="machines")
    location = models.ForeignKey("catalog.Location", models.PROTECT, db_column="LocationID", related_name="machines")
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices)
    serial_number = models.CharField(max_length=100, unique=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "Machine"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    @property
    def is_online(self):
        return self.status == self.Status.ONLINE


class MachineSlot(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Hoat dong"
        LOW_STOCK = "LOW_STOCK", "Sap het"
        EMPTY = "EMPTY", "Het"
        DISABLED = "DISABLED", "Da tat"

    id = models.AutoField(primary_key=True, db_column="MachineSlotID")
    perfume = models.ForeignKey("catalog.Perfume", models.PROTECT, db_column="PerfumeID", related_name="slots")
    machine = models.ForeignKey(Machine, models.PROTECT, db_column="MachineID", related_name="slots")
    slot_number = models.IntegerField()
    quantity = models.IntegerField(help_text="So lan xit uoc tinh con lai")
    price_per_spray = models.DecimalField(max_digits=10, decimal_places=2)
    low_stock_threshold = models.IntegerField()
    spray_duration = models.IntegerField(help_text="Thoi gian xit (mili giay)")
    capacity = models.IntegerField(help_text="So lan xit toi da cua chai")
    status = models.CharField(max_length=20, choices=Status.choices)

    class Meta:
        managed = False
        db_table = "MachineSlot"
        unique_together = [("machine", "slot_number")]
        ordering = ["machine_id", "slot_number"]

    def __str__(self):
        return f"{self.machine.name} / slot {self.slot_number}"

    @property
    def is_available(self):
        """Khach chi duoc chon mui huong khi slot san sang va may online (business rule cua de tai)."""
        return (
            self.status in (self.Status.ACTIVE, self.Status.LOW_STOCK)
            and self.quantity > 0
            and self.perfume.is_active
            and self.machine.is_online
        )


class DeviceEvent(models.Model):
    class EventType(models.TextChoices):
        STARTUP = "STARTUP"
        SHUTDOWN = "SHUTDOWN"
        RECONNECT = "RECONNECT"
        HEARTBEAT_LOST = "HEARTBEAT_LOST"
        MAINTENANCE_MODE = "MAINTENANCE_MODE"
        SENSOR_ERROR = "SENSOR_ERROR"
        DISPENSE_FAILURE = "DISPENSE_FAILURE"
        FIRMWARE_UPDATE = "FIRMWARE_UPDATE"
        DOOR_OPENED = "DOOR_OPENED"
        DOOR_CLOSED = "DOOR_CLOSED"

    id = models.AutoField(primary_key=True, db_column="DeviceEventID")
    machine = models.ForeignKey(Machine, models.CASCADE, db_column="MachineID", related_name="events")
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    message = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "DeviceEvent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.machine_id} {self.event_type}"


class Alert(models.Model):
    class Type(models.TextChoices):
        LOW_STOCK = "LOW_STOCK"
        MACHINE_OFFLINE = "MACHINE_OFFLINE"
        DOOR_OPEN = "DOOR_OPEN"
        LEAKAGE_SUSPECTED = "LEAKAGE_SUSPECTED"
        SENSOR_FAILURE = "SENSOR_FAILURE"
        ACTUATOR_FAILURE = "ACTUATOR_FAILURE"
        DISPENSE_FAILURE = "DISPENSE_FAILURE"

    class Severity(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        CRITICAL = "CRITICAL"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Moi"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Da tiep nhan"
        RESOLVED = "RESOLVED", "Da xu ly"

    id = models.AutoField(primary_key=True, db_column="AlertID")
    machine = models.ForeignKey(Machine, models.CASCADE, db_column="MachineID", related_name="alerts")
    machine_slot = models.ForeignKey(
        MachineSlot, models.SET_NULL, db_column="MachineSlotID", related_name="alerts", blank=True, null=True
    )
    alert_type = models.CharField(max_length=30, choices=Type.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    created_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    class Meta:
        managed = False
        db_table = "Alert"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.alert_type} ({self.severity}) - {self.status}"

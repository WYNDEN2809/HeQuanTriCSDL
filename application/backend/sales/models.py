from django.db import models
from django.utils import timezone


class Order(models.Model):
    """Bang Orders. Gia va san pham duoc chot tai thoi diem tao don."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Cho thanh toan"
        DISPENSED = "DISPENSED", "Da xit"
        DISPENSE_FAILED = "DISPENSE_FAILED", "Da tra tien - xit loi"
        REFUNDED = "REFUNDED", "Da hoan tien"
        REVIEW = "REVIEW", "Can xem xet"
        EXPIRED = "EXPIRED", "Het han"
        CANCELLED = "CANCELLED", "Da huy"
        FAILED = "FAILED", "Thanh toan loi"

    id = models.AutoField(primary_key=True, db_column="OrderID")
    machine_slot = models.ForeignKey(
        "devices.MachineSlot", models.PROTECT, db_column="MachineSlotID", related_name="orders"
    )
    perfume = models.ForeignKey("catalog.Perfume", models.PROTECT, db_column="PerfumeID", related_name="orders")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_reference = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=10, default="VND")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "Orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id} ({self.payment_reference})"

    @property
    def is_expired(self):
        return self.status == self.Status.PENDING and timezone.now() >= self.expires_at


class Payment(models.Model):
    class Method(models.TextChoices):
        VIETQR = "VIETQR"
        MOMO = "MOMO"
        ZALOPAY = "ZALOPAY"
        VNPAY = "VNPAY"

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"
        CANCELLED = "CANCELLED"
        REFUNDED = "REFUNDED"

    id = models.AutoField(primary_key=True, db_column="PaymentID")
    order = models.ForeignKey(Order, models.PROTECT, db_column="OrderID", related_name="payments")
    method = models.CharField(max_length=20, choices=Method.choices)
    provider_transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "Payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.id} - {self.status}"


class DispenseTransaction(models.Model):
    """Moi don hang chi co toi da MOT lenh xit (OneToOne <-> rang buoc UNIQUE trong SQL)."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Dang cho"
        SUCCESS = "SUCCESS", "Thanh cong"
        FAILED = "FAILED", "That bai"
        UNCERTAIN = "UNCERTAIN", "Khong ro ket qua"

    id = models.AutoField(primary_key=True, db_column="DispenseTransactionID")
    order = models.OneToOneField(Order, models.PROTECT, db_column="OrderID", related_name="dispense")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    command_id = models.CharField(max_length=100, unique=True)
    error_message = models.CharField(max_length=500, blank=True, null=True)
    expires_at = models.DateTimeField()
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    executed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = "DispenseTransaction"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispense {self.command_id} - {self.status}"

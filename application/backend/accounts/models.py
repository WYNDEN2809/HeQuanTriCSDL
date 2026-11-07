from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def _create(self, username, email, password, **extra):
        if not username:
            raise ValueError("Phai co username")
        user = self.model(username=username, email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra):
        extra.setdefault("role", "USER")
        return self._create(username, email, password, **extra)

    def create_superuser(self, username, email=None, password=None, **extra):
        extra["role"] = "SUPER_ADMIN"
        return self._create(username, email, password, **extra)


class User(AbstractBaseUser):
    """Anh xa vao bang [User] cua SQL Server. Mat khau luu o cot password_hash."""

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Platform Super Administrator"
        USER = "USER", "Nguoi dung thuong hieu"

    id = models.AutoField(primary_key=True, db_column="UserID")
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_active = models.BooleanField(default=True)

    last_login = None  # bang [User] khong co cot last_login

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        managed = False
        db_table = "User"

    def __str__(self):
        return self.username

    # ---- Quyen cap nen tang (Django admin can cac thuoc tinh nay) ----
    @property
    def is_platform_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_superuser(self):
        return self.is_platform_admin

    @property
    def is_staff(self):
        return self.is_platform_admin

    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_platform_admin

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(p, obj) for p in perm_list)

    def has_module_perms(self, app_label):
        return self.is_active and self.is_platform_admin

    # ---- Quyen theo thuong hieu (multi-tenant) ----
    def accessible_brand_ids(self):
        """None nghia la tat ca brand (super admin)."""
        if self.is_platform_admin:
            return None
        return list(self.brand_memberships.values_list("brand_id", flat=True))

    def brand_role_in(self, brand_id):
        return (
            self.brand_memberships.filter(brand_id=brand_id)
            .values_list("brand_role", flat=True)
            .first()
        )


class BrandMember(models.Model):
    class BrandRole(models.TextChoices):
        BRAND_ADMIN = "BRAND_ADMIN", "Brand Administrator"
        OPS_MANAGER = "OPS_MANAGER", "Operations Manager"
        TECHNICIAN = "TECHNICIAN", "Technician"
        INVENTORY_STAFF = "INVENTORY_STAFF", "Inventory Staff"
        VIEWER = "VIEWER", "Viewer"

    id = models.AutoField(primary_key=True, db_column="BrandMemberID")
    user = models.ForeignKey(User, models.CASCADE, db_column="UserID", related_name="brand_memberships")
    brand = models.ForeignKey("catalog.Brand", models.PROTECT, db_column="BrandID", related_name="members")
    brand_role = models.CharField(max_length=20, choices=BrandRole.choices)

    class Meta:
        managed = False
        db_table = "BrandMember"
        unique_together = [("user", "brand")]

    def __str__(self):
        return f"{self.user} - {self.brand} ({self.brand_role})"

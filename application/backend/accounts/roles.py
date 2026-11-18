"""
Nhom vai tro dung chung cho portal (bang phan quyen: KE_HOACH_BUOC_3_4_5.md muc 4).
Super Admin luon duoc phep (xem can()). Dung voi @brand_role_required(*roles.XXX).
"""
BRAND_ADMIN = "BRAND_ADMIN"
OPS = "OPS_MANAGER"
TECH = "TECHNICIAN"
INV = "INVENTORY_STAFF"
VIEWER = "VIEWER"
ALL = (BRAND_ADMIN, OPS, TECH, INV, VIEWER)

LABELS = {
    BRAND_ADMIN: "Brand Administrator",
    OPS: "Operations Manager",
    TECH: "Technician",
    INV: "Inventory Staff",
    VIEWER: "Viewer",
}

TRANSACTIONS_VIEW = (BRAND_ADMIN, OPS, VIEWER)
TRANSACTIONS_MANAGE = (BRAND_ADMIN, OPS)

ALERTS_VIEW = ALL
ALERTS_ACK = (BRAND_ADMIN, OPS, TECH)
ALERTS_MANAGE = (BRAND_ADMIN, OPS)

MACHINES_VIEW = ALL
MACHINES_CONFIG = (BRAND_ADMIN,)
MACHINES_TOGGLE = (BRAND_ADMIN, OPS)
MACHINES_MAINTENANCE_MODE = (BRAND_ADMIN, OPS, TECH)

MAINT_VIEW = (BRAND_ADMIN, OPS, TECH, VIEWER)
MAINT_MANAGE = (BRAND_ADMIN, OPS)
MAINT_EXECUTE = (TECH,)
MAINT_REPORTS = (BRAND_ADMIN, OPS, VIEWER)

INVENTORY_VIEW = (BRAND_ADMIN, OPS, INV, VIEWER)
INVENTORY_MANAGE = (INV,)
INVENTORY_REPORTS = (BRAND_ADMIN, OPS, INV, VIEWER)

PEOPLE_MANAGE = (BRAND_ADMIN,)
CATALOG_VIEW = (BRAND_ADMIN, VIEWER)
CATALOG_MANAGE = (BRAND_ADMIN,)

REPORTS_VIEW = (BRAND_ADMIN, OPS, VIEWER)
AUDIT_VIEW = (BRAND_ADMIN,)


def can(request, roles):
    """Nguoi dung hien tai co thuoc mot trong cac vai tro duoc phep (hoac la Super Admin) khong."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return False
    return bool(user.is_platform_admin or getattr(request, "brand_role", None) in roles)

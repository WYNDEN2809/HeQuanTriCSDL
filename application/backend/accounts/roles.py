"""Role names and capabilities used by the brand portal."""

PLATFORM_ADMIN = "PLATFORM_ADMIN"
BRAND_ADMIN = "BRAND_ADMIN"
OPS_MANAGER = "OPS_MANAGER"
TECHNICIAN = "TECHNICIAN"
INV = "INVENTORY_STAFF"
VIEWER = "VIEWER"

ALERTS_VIEW = (BRAND_ADMIN, OPS_MANAGER, TECHNICIAN, VIEWER)
ALERTS_ACK = (BRAND_ADMIN, OPS_MANAGER, TECHNICIAN)
ALERTS_MANAGE = (BRAND_ADMIN, OPS_MANAGER)
REPORTS_VIEW = (BRAND_ADMIN, OPS_MANAGER, VIEWER)

_CAPABILITIES = {
    "ALERTS_ACK": ALERTS_ACK,
    "ALERTS_MANAGE": ALERTS_MANAGE,
    "REPORTS_VIEW": REPORTS_VIEW,
}


def can(request, capability):
    if request.user.is_platform_admin:
        return True
    allowed = _CAPABILITIES.get(capability, capability if isinstance(capability, tuple) else ())
    return request.brand_role in allowed

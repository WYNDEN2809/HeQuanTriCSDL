from . import roles


def portal_access(request):
    """Cho template biet nguoi dung duoc thay muc nao tren thanh menu portal."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    def c(group):
        return roles.can(request, group)

    return {
        "portal": {
            "transactions": c(roles.TRANSACTIONS_VIEW),
            "alerts": c(roles.ALERTS_VIEW),
            "machines": c(roles.MACHINES_VIEW),
            "maintenance": c(roles.MAINT_VIEW),
            "inventory": c(roles.INVENTORY_VIEW),
            "people": c(roles.PEOPLE_MANAGE),
            "catalog": c(roles.CATALOG_VIEW),
            "tenants": user.is_platform_admin,
            "reports": c(roles.REPORTS_VIEW) or c(roles.INVENTORY_REPORTS),
            "audit": c(roles.AUDIT_VIEW),
        }
    }

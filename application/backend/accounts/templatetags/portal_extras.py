from django import template

register = template.Library()

_BADGES = {
    "DISPENSED": "success", "SUCCESS": "success", "COMPLETED": "success", "RESOLVED": "success",
    "ONLINE": "success", "ACTIVE": "success",
    "PENDING": "info", "WAITING_PAYMENT": "info", "IN_PROGRESS": "primary", "ACKNOWLEDGED": "primary",
    "OPEN": "warning", "LOW_STOCK": "warning", "MEDIUM": "warning", "MAINTENANCE": "warning", "UNCERTAIN": "warning",
    "REVIEW": "danger", "DISPENSE_FAILED": "danger", "FAILED": "danger", "ERROR": "danger", "EMPTY": "danger",
    "CRITICAL": "danger", "HIGH": "danger",
    "OFFLINE": "secondary", "DISABLED": "secondary", "EXPIRED": "secondary", "CANCELLED": "secondary",
    "REFUNDED": "secondary", "LOW": "secondary",
}


@register.filter
def badge(value):
    """Ten mau Bootstrap cho mot trang thai: <span class="badge text-bg-{{ x|badge }}">"""
    return _BADGES.get(str(value), "secondary")


@register.filter
def money(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.simple_tag(takes_context=True)
def qs(context, **kwargs):
    """Tao query string tu request.GET, thay/bo cac khoa duoc truyen: {% qs page=2 %}"""
    query = context["request"].GET.copy()
    for key, val in kwargs.items():
        if val in (None, ""):
            query.pop(key, None)
        else:
            query[key] = val
    return query.urlencode()


@register.filter
def dictget(mapping, key):
    """Lay phan tu mapping[key] trong template: {{ result|dictget:key }}"""
    try:
        return mapping.get(key, [])
    except AttributeError:
        return []

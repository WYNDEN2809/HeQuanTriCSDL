<<<<<<< HEAD
=======
<<<<<<< HEAD
from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation

=======
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89
from django import template

register = template.Library()

<<<<<<< HEAD
=======
<<<<<<< HEAD

@register.filter
def badge(value):
    return {
        "ONLINE": "success", "DISPENSED": "success", "RESOLVED": "success", "COMPLETED": "success",
        "OPEN": "warning", "PENDING": "info", "ACKNOWLEDGED": "primary", "IN_PROGRESS": "primary",
        "LOW": "secondary", "MEDIUM": "info", "HIGH": "warning", "CRITICAL": "danger",
        "OFFLINE": "secondary", "ERROR": "danger", "EMPTY": "danger", "DISABLED": "secondary",
        "DISPENSE_FAILED": "danger", "REVIEW": "danger", "FAILED": "danger",
    }.get(str(value), "secondary")
=======
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89
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
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89


@register.filter
def money(value):
    try:
<<<<<<< HEAD
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value
=======
<<<<<<< HEAD
        number = int(Decimal(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"{number:,}".replace(",", ".")
=======
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89


@register.simple_tag(takes_context=True)
def qs(context, **kwargs):
<<<<<<< HEAD
=======
<<<<<<< HEAD
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return urlencode(params)
=======
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89
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
<<<<<<< HEAD
=======
>>>>>>> origin/main
>>>>>>> 00cae3259f9e6ca547464be52217e0547768ca89

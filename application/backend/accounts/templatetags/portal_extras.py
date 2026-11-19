from urllib.parse import urlencode
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def badge(value):
    return {
        "ONLINE": "success", "DISPENSED": "success", "RESOLVED": "success", "COMPLETED": "success",
        "OPEN": "warning", "PENDING": "info", "ACKNOWLEDGED": "primary", "IN_PROGRESS": "primary",
        "LOW": "secondary", "MEDIUM": "info", "HIGH": "warning", "CRITICAL": "danger",
        "OFFLINE": "secondary", "ERROR": "danger", "EMPTY": "danger", "DISABLED": "secondary",
        "DISPENSE_FAILED": "danger", "REVIEW": "danger", "FAILED": "danger",
    }.get(str(value), "secondary")


@register.filter
def money(value):
    try:
        number = int(Decimal(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return value
    return f"{number:,}".replace(",", ".")


@register.simple_tag(takes_context=True)
def qs(context, **kwargs):
    params = context["request"].GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return urlencode(params)

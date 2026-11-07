import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .audit import log_action

logger = logging.getLogger(__name__)


def _first_brand_id(user):
    if user is None or not getattr(user, "pk", None) or user.is_platform_admin:
        return None
    return user.brand_memberships.values_list("brand_id", flat=True).first()


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    try:
        log_action(user, "LOGIN", "User", user.pk, brand_id=_first_brand_id(user))
    except Exception:  # khong de loi audit chan viec dang nhap
        logger.exception("Khong ghi duoc audit log dang nhap")


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    try:
        if user is not None:
            log_action(user, "LOGOUT", "User", user.pk, brand_id=_first_brand_id(user))
    except Exception:
        logger.exception("Khong ghi duoc audit log dang xuat")

import json

from .models import AuditLog


def _dump(value):
    if value is None or isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def log_action(user, action, entity_type=None, entity_id=None, brand_id=None, old_value=None, new_value=None):
    """
    Ghi nhat ky audit. Dung cho moi thao tac quan trong (doi gia, refill, hoan tien, doi quyen...).
    old_value / new_value co the la dict (se luu dang JSON).
    """
    return AuditLog.objects.create(
        user=user if getattr(user, "pk", None) else None,
        brand_id=brand_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=_dump(old_value),
        new_value=_dump(new_value),
    )

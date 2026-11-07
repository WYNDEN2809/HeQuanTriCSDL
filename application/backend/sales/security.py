"""Ky va xac thuc: webhook thanh toan, token thiet bi, chu ky lenh xit (HMAC-SHA256)."""
import hashlib
import hmac

from django.conf import settings


def _hmac(secret, message):
    if isinstance(message, str):
        message = message.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


# ---- Webhook thanh toan -------------------------------------------------
def sign_webhook_body(body):
    return _hmac(settings.PAYMENT_WEBHOOK_SECRET, body)


def verify_webhook_signature(body, signature):
    return bool(signature) and hmac.compare_digest(sign_webhook_body(body), signature)


# ---- Thiet bi -----------------------------------------------------------
def device_token(serial):
    """Token cua may = HMAC(secret, serial). May that se duoc nap token nay luc kich hoat."""
    return _hmac(settings.DEVICE_API_SECRET, "device:" + serial)


def verify_device_token(serial, token):
    return bool(token) and hmac.compare_digest(device_token(serial), token)


def sign_command(command_id, serial, slot_number, spray_duration, expires_at_iso):
    """Chu ky lenh xit: may tu tinh lai de tu choi lenh gia mao / bi sua."""
    message = "cmd:" + "|".join(str(x) for x in (command_id, serial, slot_number, spray_duration, expires_at_iso))
    return _hmac(settings.DEVICE_API_SECRET, message)

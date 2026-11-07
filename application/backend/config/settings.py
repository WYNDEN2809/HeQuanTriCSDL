"""
Cau hinh Django cho ScentStation.

Co so du lieu la SQL Server da tao bang cac file 01..04 trong thu muc database/.
Cac model trong du an dung managed = False: Django KHONG tu tao/sua bang cua ScentStation,
schema duoc quan ly boi file 01_CreateSchema.sql.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.getenv(name, default)


def env_bool(name, default=False):
    return str(os.getenv(name, str(default))).strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # ScentStation
    "accounts",
    "catalog",
    "devices",
    "sales",
    "inventory",
    "maintenance",
    "reports",
    "kiosk",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.ActiveBrandMiddleware",   # xac dinh brand dang lam viec cua user
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------- Database
_extra_params = ["TrustServerCertificate=yes"]
if env_bool("DB_TRUSTED", False):
    _extra_params.append("Trusted_Connection=yes")

DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": env("DB_NAME", "ScentStationDB"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", ""),
        "USER": env("DB_USER", ""),
        "PASSWORD": env("DB_PASSWORD", ""),
        "OPTIONS": {
            "driver": env("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
            "extra_params": ";".join(_extra_params),
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# ---------------------------------------------------------------- Auth
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
]

# ---------------------------------------------------------------- I18N
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
# Cac cot datetime2 trong SQL Server luu gio dia phuong (SYSDATETIME()) khong kem mui gio,
# nen tat USE_TZ de Django lam viec voi datetime "naive", tranh loi lech gio.
USE_TZ = False

# ---------------------------------------------------------------- Static
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------- Buoc 2: ban hang & thiet bi
# Thoi han don hang chua thanh toan / thoi han lenh xit (giay)
ORDER_TTL_SECONDS = int(env("ORDER_TTL_SECONDS", "300"))
DISPENSE_COMMAND_TTL_SECONDS = int(env("DISPENSE_COMMAND_TTL_SECONDS", "120"))
# Heartbeat: <= ONLINE_SECONDS la online, <= OFFLINE_SECONDS la khong on dinh, qua nua la offline
HEARTBEAT_ONLINE_SECONDS = int(env("HEARTBEAT_ONLINE_SECONDS", "30"))
HEARTBEAT_OFFLINE_SECONDS = int(env("HEARTBEAT_OFFLINE_SECONDS", "90"))
# Khoa bi mat dung ky webhook thanh toan va tao token thiet bi (PHAI doi khi trien khai that)
PAYMENT_WEBHOOK_SECRET = env("PAYMENT_WEBHOOK_SECRET", "dev-webhook-secret-change-me")
DEVICE_API_SECRET = env("DEVICE_API_SECRET", "dev-device-secret-change-me")
# Trang thanh toan gia lap (chi nen bat khi demo / phat trien)
PAYMENT_SANDBOX_ENABLED = env_bool("PAYMENT_SANDBOX_ENABLED", DEBUG)
# Kiosk tu lam moi man hinh chinh sau ... giay khong thao tac
KIOSK_IDLE_SECONDS = int(env("KIOSK_IDLE_SECONDS", "60"))

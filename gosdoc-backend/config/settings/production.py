"""
ГосДок — Настройки для production (config/settings/production.py)
"""

import sentry_sdk
from decouple import config
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F401, F403

# ============================================================
# Безопасность (раздел 6 ТЗ)
# ============================================================
DEBUG = False
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="api.gosdoc.gov.kz").split(",")

# HTTPS (раздел 6 ТЗ: TLS 1.2+)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000        # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ============================================================
# Файловое хранилище — AWS S3 / Yandex Object Storage
# ============================================================
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATICFILES_STORAGE = "storages.backends.s3boto3.S3StaticStorage"

# ============================================================
# Sentry — мониторинг ошибок
# ============================================================
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
        release=config("APP_VERSION", default="1.0.0"),
    )

# ============================================================
# Логирование — минимальный уровень INFO
# ============================================================
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405

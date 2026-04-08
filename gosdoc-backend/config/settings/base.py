"""
ГосДок — Базовые настройки Django (config/settings/base.py)
Используется как основа для development.py и production.py
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config

# ============================================================
# Пути
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================
# Безопасность
# ============================================================
SECRET_KEY = config("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-production")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

# ============================================================
# Приложения
# ============================================================
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "storages",
    "drf_spectacular",
    "django_celery_beat",   # Планировщик Celery Beat (хранит расписание в БД)
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.organizations",
    "apps.workspaces",
    "apps.documents",
    "apps.tasks",
    "apps.signatures",
    "apps.notifications",
    "apps.reports",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ============================================================
# Middleware
# ============================================================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",          # CORS — должен быть выше CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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

# ============================================================
# База данных (PostgreSQL через DATABASE_URL)
# ============================================================
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default="postgres://gosdoc_user:gosdoc_pass@localhost:5432/gosdoc"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ============================================================
# Кастомная модель пользователя
# ============================================================
AUTH_USER_MODEL = "users.User"

# ============================================================
# Валидация паролей
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ============================================================
# Локализация
# ============================================================
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

# ============================================================
# Статика
# ============================================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================
# Django REST Framework
# ============================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Rate limiting (раздел 6 ТЗ: 100 запросов/мин)
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.core.throttling.StandardUserThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "standard_user": "100/min",
        "auth_anon": "10/min",
        "upload": "20/min",
    },
    # Унифицированный формат ошибок
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# ============================================================
# JWT настройки (раздел 6 ТЗ: access 15 мин, refresh 7 дней)
# ============================================================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,       # Выдаём новый refresh при использовании
    "BLACKLIST_AFTER_ROTATION": True,    # Старый refresh → blacklist
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.users.serializers.CustomTokenObtainPairSerializer",
}

# ============================================================
# Redis + Кэш
# ============================================================
REDIS_URL = config("REDIS_URL", default="redis://redis:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 300,
    }
}

# ============================================================
# Celery
# ============================================================
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ============================================================
# AWS S3 / Yandex Object Storage (раздел 6 ТЗ)
# ============================================================
AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="gosdoc-documents")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)  # Для Yandex
AWS_S3_CUSTOM_DOMAIN = None
AWS_DEFAULT_ACL = "private"                  # Приватный бакет (раздел 6 ТЗ)
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = True                  # presigned URL
AWS_QUERYSTRING_EXPIRE = 3600               # TTL 60 мин (раздел 6 ТЗ)
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

# ============================================================
# Email
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="ГосДок <noreply@gosdoc.gov.kz>")

# ============================================================
# OpenAI / LLM (AI-модуль)
# ============================================================
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
OPENAI_MODEL = config("OPENAI_MODEL", default="gpt-4o-mini")

# ============================================================
# CORS (раздел 6 ТЗ: только доверенные домены)
# ============================================================
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://localhost:5173",
).split(",")
CORS_ALLOW_CREDENTIALS = True

# ============================================================
# Rate limiting (раздел 6 ТЗ: 100 запросов/мин)
# ============================================================
RATELIMIT_USE_CACHE = "default"
RATELIMIT_DEFAULT = "100/m"

# ============================================================
# DRF Spectacular (Swagger/OpenAPI)
# ============================================================
SPECTACULAR_SETTINGS = {
    "TITLE": "ГосДок API",
    "DESCRIPTION": "Облачная платформа документооборота для государственных органов",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
    },
}

# ============================================================
# Логирование (аудит-лог, раздел 6 ТЗ)
# ============================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

# ============================================================
# Sentry — мониторинг ошибок (раздел 6 ТЗ, критерий приёмки №12)
# ============================================================
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(
                transaction_style="url",
                middleware_spans=True,
            ),
            CeleryIntegration(),
        ],
        # Процент трассировок производительности (0.1 = 10%)
        traces_sample_rate=config("SENTRY_TRACES_SAMPLE_RATE", default=0.1, cast=float),
        # Среда: development / staging / production
        environment=config("DJANGO_ENVIRONMENT", default="development"),
        # Не отправляем PII (email, IP) в Sentry (GDPR)
        send_default_pii=False,
        # Версия приложения для группировки ошибок
        release="gosdoc@1.0.0",
    )

# ============================================================
# Максимальный размер загружаемого файла: 100 МБ (раздел 2.5 ТЗ)
# ============================================================
DATA_UPLOAD_MAX_MEMORY_SIZE = 104_857_600   # 100 МБ
FILE_UPLOAD_MAX_MEMORY_SIZE = 104_857_600   # 100 МБ

# Поддерживаемые форматы документов (раздел 2.5 ТЗ)
ALLOWED_DOCUMENT_EXTENSIONS = ["pdf", "docx", "xlsx", "odt", "ods"]
MAX_DOCUMENT_SIZE_BYTES = 104_857_600  # 100 МБ

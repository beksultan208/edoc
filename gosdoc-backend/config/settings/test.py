"""
ГосДок — Настройки для тестирования (config/settings/test.py)
"""

from .base import *  # noqa: F401, F403
import dj_database_url

# ============================================================
# Локальная БД для тестов (localhost, не docker hostname)
# ============================================================
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://gosdoc_user:gosdoc_pass@localhost:5432/gosdoc",
        conn_max_age=0,
    )
}

# ============================================================
# Быстрый хэш паролей (ускоряет тесты в ~10 раз)
# ============================================================
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# ============================================================
# Email — не отправляем реальные письма в тестах
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ============================================================
# Celery — выполняем задачи синхронно (без брокера)
# ============================================================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ============================================================
# Кэш — в памяти (не нужен Redis)
# ============================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ============================================================
# CORS — разрешаем всё в тестах
# ============================================================
CORS_ALLOW_ALL_ORIGINS = True

# ============================================================
# Логи — тишина в тестах
# ============================================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"]},
}

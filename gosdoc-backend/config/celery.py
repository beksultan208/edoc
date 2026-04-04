"""
ГосДок — Конфигурация Celery (config/celery.py)
"""

import os

from celery import Celery
from celery.schedules import crontab

# Устанавливаем настройки Django для Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("gosdoc")

# Загружаем конфигурацию из Django settings (префикс CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматическое обнаружение задач в apps/*/tasks.py
app.autodiscover_tasks()

# ============================================================
# Celery Beat — расписание периодических задач
# ============================================================
app.conf.beat_schedule = {
    # Ежемесячная генерация отчётов — 1-е число каждого месяца в 00:00 (раздел 2.9 ТЗ)
    "generate-monthly-reports": {
        "task": "apps.reports.tasks.generate_monthly_reports",
        "schedule": crontab(minute=0, hour=0, day_of_month=1),
    },
    # Проверка дедлайнов задач — каждый час (раздел 2.8 ТЗ: уведомление за 24ч)
    "check-task-deadlines": {
        "task": "apps.notifications.tasks.check_task_deadlines",
        "schedule": crontab(minute=0),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Диагностическая задача для проверки Celery."""
    print(f"Request: {self.request!r}")

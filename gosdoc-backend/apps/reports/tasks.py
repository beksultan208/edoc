"""
ГосДок — Celery задача: ежемесячная генерация отчётов (apps/reports/tasks.py)
Раздел 2.9 ТЗ: 1-е число каждого месяца
"""

import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.reports.tasks.generate_monthly_reports")
def generate_monthly_reports():
    """
    Генерирует ежемесячные отчёты для всех организаций.
    Запускается Celery Beat 1-го числа каждого месяца в 00:00.
    """
    from apps.organizations.models import Organization
    from apps.reports.generators import generate_report_data
    from apps.reports.models import MonthlyReport

    today = date.today()
    # Отчёт за прошлый месяц
    if today.month == 1:
        year, month = today.year - 1, 12
    else:
        year, month = today.year, today.month - 1

    organizations = Organization.objects.all()
    created_count = 0

    for org in organizations:
        try:
            data = generate_report_data(str(org.id), year, month)
            _, created = MonthlyReport.objects.update_or_create(
                organization=org,
                period_year=year,
                period_month=month,
                defaults=data,
            )
            if created:
                created_count += 1
        except Exception as exc:
            logger.error("Ошибка генерации отчёта для %s: %s", org.name, exc)

    logger.info(
        "Ежемесячные отчёты сгенерированы: %d/%d организаций (%s/%s)",
        created_count,
        organizations.count(),
        month,
        year,
    )

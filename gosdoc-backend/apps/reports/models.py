"""
ГосДок — Модель ежемесячных отчётов (apps/reports/models.py)
Раздел 3.11 ТЗ
"""

import uuid

from django.db import models


class MonthlyReport(models.Model):
    """
    Ежемесячный отчёт по организации.

    Поля по разделу 3.11 ТЗ:
    - id: UUID PK
    - organization_id: FK → organizations
    - period_year: год (SMALLINT)
    - period_month: месяц 1–12 (SMALLINT)
    - docs_total: всего документов
    - docs_completed: завершённых
    - docs_signed: подписанных
    - tasks_completed: завершённых задач
    - avg_completion_days: среднее время согласования (дней)
    - report_data: JSONB с детальными данными
    - generated_at: время генерации
    - UNIQUE(organization_id, period_year, period_month)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="monthly_reports",
        verbose_name="Организация",
        db_index=True,
        null=True,
        blank=True,
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="monthly_reports",
        verbose_name="Кабинет",
        db_index=True,
        null=True,
        blank=True,
    )
    period_year = models.SmallIntegerField(verbose_name="Год")
    period_month = models.SmallIntegerField(verbose_name="Месяц (1–12)")
    docs_total = models.IntegerField(default=0, verbose_name="Всего документов")
    docs_completed = models.IntegerField(default=0, verbose_name="Завершённых")
    docs_signed = models.IntegerField(default=0, verbose_name="Подписанных")
    tasks_completed = models.IntegerField(default=0, verbose_name="Завершённых задач")
    avg_completion_days = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Среднее время (дней)",
    )
    report_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Детальные данные (JSONB)",
    )
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата генерации")

    class Meta:
        verbose_name = "Ежемесячный отчёт"
        verbose_name_plural = "Ежемесячные отчёты"
        db_table = "monthly_reports"
        unique_together = [("workspace", "period_year", "period_month")]
        ordering = ["-period_year", "-period_month"]
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["period_year", "period_month"]),
        ]

    def __str__(self) -> str:
        return f"Отчёт {self.organization} {self.period_month}/{self.period_year}"

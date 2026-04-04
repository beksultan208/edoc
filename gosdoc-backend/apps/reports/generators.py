"""
ГосДок — Генераторы отчётов (apps/reports/generators.py)
Раздел 2.9 ТЗ: PDF, XLSX экспорт
"""

import io
import logging
from datetime import date

logger = logging.getLogger(__name__)


def generate_report_data_by_workspace(workspace_id: str, year: int, month: int) -> dict:
    """
    Собирает статистику за указанный период.
    Возвращает словарь для сохранения в MonthlyReport.
    """
    from apps.documents.models import Document
    from apps.tasks.models import Task
    from django.db.models import Avg, F, ExpressionWrapper, DurationField

    # Границы периода
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    docs = Document.objects.filter(
        workspace_id=workspace_id,
        created_at__date__gte=start_date,
        created_at__date__lt=end_date,
    )

    docs_total = docs.count()
    docs_completed = docs.filter(status__in=["signed", "archived"]).count()
    docs_signed = docs.filter(status="signed").count()

    tasks_completed = Task.objects.filter(
        workspace_id=workspace_id,
        status="done",
        completed_at__date__gte=start_date,
        completed_at__date__lt=end_date,
    ).count()

    # Среднее время согласования (дней)
    avg_days = None
    signed_docs = docs.filter(status="signed", updated_at__isnull=False)
    if signed_docs.exists():
        total_days = sum(
            (d.updated_at.date() - d.created_at.date()).days
            for d in signed_docs
        )
        avg_days = round(total_days / signed_docs.count(), 2)

    return {
        "docs_total": docs_total,
        "docs_completed": docs_completed,
        "docs_signed": docs_signed,
        "tasks_completed": tasks_completed,
        "avg_completion_days": avg_days,
        "report_data": {
            "period": f"{year}-{month:02d}",
            "workspace_id": str(workspace_id),
        },
    }


def export_report_to_xlsx(report) -> bytes:
    """
    Экспортирует отчёт в XLSX.
    Раздел 2.9 ТЗ.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Отчёт {report.period_month:02d}.{report.period_year}"

        # Заголовок
        ws["A1"] = f"Ежемесячный отчёт ГосДок — {report.period_month:02d}/{report.period_year}"
        ws["A1"].font = Font(bold=True, size=14)
        ws.merge_cells("A1:B1")

        # Данные
        rows = [
            ("Показатель", "Значение"),
            ("Всего документов", report.docs_total),
            ("Завершённых документов", report.docs_completed),
            ("Подписанных документов", report.docs_signed),
            ("Завершённых задач", report.tasks_completed),
            ("Среднее время согласования (дней)", float(report.avg_completion_days or 0)),
        ]

        for row_idx, (label, value) in enumerate(rows, start=3):
            ws.cell(row=row_idx, column=1, value=label)
            ws.cell(row=row_idx, column=2, value=value)
            if row_idx == 3:
                ws.cell(row=row_idx, column=1).font = Font(bold=True)
                ws.cell(row=row_idx, column=2).font = Font(bold=True)

        ws.column_dimensions["A"].width = 40
        ws.column_dimensions["B"].width = 20

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    except ImportError:
        logger.error("openpyxl не установлен")
        return b""


def export_report_to_pdf(report) -> bytes:
    """
    Экспортирует отчёт в PDF с помощью WeasyPrint.
    Раздел 2.9 ТЗ.
    """
    try:
        import weasyprint

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; padding: 40px; }}
                h1 {{ color: #2c3e50; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Ежемесячный отчёт ГосДок</h1>
            <p>Период: {report.period_month:02d}/{report.period_year}</p>
            <p>Организация: {report.organization.name}</p>
            <table>
                <tr><th>Показатель</th><th>Значение</th></tr>
                <tr><td>Всего документов</td><td>{report.docs_total}</td></tr>
                <tr><td>Завершённых документов</td><td>{report.docs_completed}</td></tr>
                <tr><td>Подписанных документов</td><td>{report.docs_signed}</td></tr>
                <tr><td>Завершённых задач</td><td>{report.tasks_completed}</td></tr>
                <tr><td>Среднее время согласования (дней)</td><td>{report.avg_completion_days or '—'}</td></tr>
            </table>
            <p><small>Сгенерировано: {report.generated_at.strftime('%d.%m.%Y %H:%M')}</small></p>
        </body>
        </html>
        """

        pdf = weasyprint.HTML(string=html_content).write_pdf()
        return pdf

    except ImportError:
        logger.error("weasyprint не установлен")
        return b""

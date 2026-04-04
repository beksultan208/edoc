from django.contrib import admin
from .models import MonthlyReport


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ["organization", "period_year", "period_month", "docs_total", "docs_signed", "generated_at"]
    list_filter = ["period_year", "period_month"]
    raw_id_fields = ["organization"]
    readonly_fields = ["generated_at"]

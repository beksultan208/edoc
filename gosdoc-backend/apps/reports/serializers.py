from rest_framework import serializers
from .models import MonthlyReport


class MonthlyReportSerializer(serializers.ModelSerializer):
    workspace_title = serializers.CharField(source="workspace.title", read_only=True)

    class Meta:
        model = MonthlyReport
        fields = [
            "id", "workspace", "workspace_title",
            "period_year", "period_month",
            "docs_total", "docs_completed", "docs_signed",
            "tasks_completed", "avg_completion_days",
            "report_data", "generated_at",
        ]
        read_only_fields = fields


class GenerateReportSerializer(serializers.Serializer):
    """Ручная генерация отчёта за период."""
    period_year = serializers.IntegerField(min_value=2000, max_value=2100)
    period_month = serializers.IntegerField(min_value=1, max_value=12)
    organization = serializers.UUIDField()  # принимаем workspace UUID (поле называется organization для совместимости с фронтом)

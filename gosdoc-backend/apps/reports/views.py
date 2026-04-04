"""
ГосДок — Views отчётов (apps/reports/views.py)
Раздел 4.10 ТЗ
"""

import logging

from django.http import HttpResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .generators import export_report_to_pdf, export_report_to_xlsx, generate_report_data_by_workspace
from .models import MonthlyReport
from .serializers import GenerateReportSerializer, MonthlyReportSerializer

logger = logging.getLogger(__name__)


class ReportListView(generics.ListAPIView):
    """GET /api/v1/reports/ — список отчётов текущего пользователя"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MonthlyReportSerializer

    def get_queryset(self):
        return MonthlyReport.objects.filter(
            workspace__members__user=self.request.user
        ).select_related("workspace").distinct()


class ReportGenerateView(APIView):
    """POST /api/v1/reports/generate/ — ручная генерация отчёта"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        year = serializer.validated_data["period_year"]
        month = serializer.validated_data["period_month"]
        workspace_id = serializer.validated_data["organization"]  # frontend отправляет workspace UUID

        from apps.workspaces.models import Workspace, WorkspaceMember
        try:
            workspace = Workspace.objects.get(pk=workspace_id, members__user=request.user)
        except Workspace.DoesNotExist:
            return Response({"detail": "Кабинет не найден или нет доступа."}, status=status.HTTP_403_FORBIDDEN)

        data = generate_report_data_by_workspace(workspace_id, year, month)

        report, created = MonthlyReport.objects.update_or_create(
            workspace=workspace,
            period_year=year,
            period_month=month,
            defaults=data,
        )

        action = "создан" if created else "обновлён"
        logger.info("Отчёт %s: кабинет=%s %s/%s", action, workspace.title, month, year)

        return Response(MonthlyReportSerializer(report).data, status=status.HTTP_201_CREATED)


class ReportDetailView(generics.RetrieveAPIView):
    """GET /api/v1/reports/{id}/ — детали отчёта"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MonthlyReportSerializer

    def get_queryset(self):
        return MonthlyReport.objects.filter(
            workspace__members__user=self.request.user
        ).distinct()


class ReportExportView(APIView):
    """GET /api/v1/reports/{id}/export/?format=pdf|xlsx"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            report = MonthlyReport.objects.select_related("workspace").get(
                pk=pk,
                workspace__members__user=request.user,
            )
        except MonthlyReport.DoesNotExist:
            return Response({"detail": "Отчёт не найден."}, status=status.HTTP_404_NOT_FOUND)

        export_format = request.query_params.get("format", "pdf").lower()
        filename = f"report_{report.period_year}_{report.period_month:02d}"

        if export_format == "xlsx":
            content = export_report_to_xlsx(report)
            response = HttpResponse(
                content,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
        elif export_format == "pdf":
            content = export_report_to_pdf(report)
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
        else:
            return Response({"detail": "Допустимые форматы: pdf, xlsx"}, status=status.HTTP_400_BAD_REQUEST)

        return response

from django.urls import path
from .views import ReportDetailView, ReportExportView, ReportGenerateView, ReportListView

urlpatterns = [
    path("", ReportListView.as_view(), name="report-list"),
    path("generate/", ReportGenerateView.as_view(), name="report-generate"),
    path("<uuid:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("<uuid:pk>/export/", ReportExportView.as_view(), name="report-export"),
]

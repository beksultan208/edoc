"""
ГосДок — Корневые URL (config/urls.py)
Base URL: https://api.gosdoc.gov.kz
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # ---- Django Admin ----
    path("admin/", admin.site.urls),

    # ---- API v1 ----
    path("api/v1/auth/", include("apps.users.urls.auth")),
    path("api/v1/users/", include("apps.users.urls.users")),
    path("api/v1/organizations/", include("apps.organizations.urls")),
    path("api/v1/workspaces/", include("apps.workspaces.urls")),
    path("api/v1/documents/", include("apps.documents.urls")),
    path("api/v1/tasks/", include("apps.tasks.urls")),
    path("api/v1/signatures/", include("apps.signatures.urls")),
    path("api/v1/comments/", include("apps.documents.comment_urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),

    # ---- OpenAPI / Swagger (раздел 9 ТЗ: /api/schema/swagger-ui/) ----
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

"""
ГосДок — URL документов (apps/documents/urls.py)
Раздел 4.5 ТЗ

Маршруты:
  Загрузка (двухэтапная, без проксирования через Django):
    POST  /documents/request-upload/               — шаг 1: получить presigned POST URL
    POST  /documents/                              — шаг 2: подтверждение, создать запись
  Документы:
    GET   /documents/                              — список
    GET   /documents/{id}/                        — деталь
    PATCH /documents/{id}/                        — обновить title
    DELETE /documents/{id}/                       — архивировать
    GET   /documents/{id}/download/               — presigned GET URL
  Версии:
    GET   /documents/{id}/versions/               — список версий
    POST  /documents/{id}/versions/request-upload/— presigned POST для новой версии (шаг 1)
    POST  /documents/{id}/versions/               — подтверждение новой версии (шаг 2)
    GET   /documents/{id}/versions/{vid}/diff/    — AI-diff
  Workflow:
    POST  /documents/{id}/workflow/start/         — запустить workflow (draft → review)
  Комментарии (вложены в документ):
    GET   /documents/{id}/comments/               — список
    POST  /documents/{id}/comments/               — создать
  Подписи (вложены в документ):
    POST  /documents/{id}/sign/                   — подписать
    GET   /documents/{id}/signatures/             — список подписей
"""

from django.urls import path

from apps.signatures.views import SignDocumentView, SignatureListView
from .views import (
    CommentListCreateView,
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListCreateView,
    DocumentVersionCreateView,
    DocumentVersionDiffView,
    DocumentVersionListView,
    DocumentWorkflowStartView,
    RequestUploadView,
    RequestVersionUploadView,
)

urlpatterns = [
    # ---- Двухэтапная загрузка ----
    path("request-upload/", RequestUploadView.as_view(), name="document-request-upload"),

    # ---- CRUD документов ----
    path("", DocumentListCreateView.as_view(), name="document-list"),
    path("<uuid:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path("<uuid:pk>/download/", DocumentDownloadView.as_view(), name="document-download"),

    # ---- Версии ----
    path("<uuid:pk>/versions/", DocumentVersionListView.as_view(), name="document-version-list"),
    path(
        "<uuid:pk>/versions/request-upload/",
        RequestVersionUploadView.as_view(),
        name="document-version-request-upload",
    ),
    # Подтверждение новой версии (после загрузки в S3)
    path(
        "<uuid:pk>/versions/confirm/",
        DocumentVersionCreateView.as_view(),
        name="document-version-confirm",
    ),
    # AI-diff конкретной версии
    path(
        "<uuid:pk>/versions/<uuid:vid>/diff/",
        DocumentVersionDiffView.as_view(),
        name="document-version-diff",
    ),

    # ---- Workflow ----
    path("<uuid:pk>/workflow/start/", DocumentWorkflowStartView.as_view(), name="document-workflow-start"),

    # ---- Комментарии ----
    path("<uuid:pk>/comments/", CommentListCreateView.as_view(), name="document-comment-list"),

    # ---- Подписи ----
    path("<uuid:pk>/sign/", SignDocumentView.as_view(), name="document-sign"),
    path("<uuid:pk>/signatures/", SignatureListView.as_view(), name="document-signatures"),
]

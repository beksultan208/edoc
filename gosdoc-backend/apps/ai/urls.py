"""
ГосДок — URL AI-сервиса (apps/ai/urls.py)

Маршруты:
  POST /api/v1/ai/generate/        — генерация текста документа
  POST /api/v1/ai/summarize/       — резюме документа
  POST /api/v1/ai/search/          — семантический поиск (RAG)
  POST /api/v1/ai/embed/           — ручная индексация документа в pgvector
  POST /api/v1/ai/classify/        — ML-классификация типа документа
  POST /api/v1/ai/chat/document/   — чат с конкретным документом
  POST /api/v1/ai/chat/general/    — общий AI ассистент по кабинету
  GET  /api/v1/ai/chat/history/    — история сообщений чата
"""

from django.urls import path

from .views import (
    ChatHistoryView,
    ChatWithDocumentView,
    ClassifyDocumentView,
    EmbedDocumentView,
    GeneralChatView,
    GenerateDocumentView,
    SearchDocumentsView,
    SummarizeDocumentView,
)

urlpatterns = [
    path("generate/", GenerateDocumentView.as_view(), name="ai-generate"),
    path("summarize/", SummarizeDocumentView.as_view(), name="ai-summarize"),
    path("search/", SearchDocumentsView.as_view(), name="ai-search"),
    path("embed/", EmbedDocumentView.as_view(), name="ai-embed"),
    path("classify/", ClassifyDocumentView.as_view(), name="ai-classify"),
    # --- Чат ---
    path("chat/document/", ChatWithDocumentView.as_view(), name="ai-chat-document"),
    path("chat/general/", GeneralChatView.as_view(), name="ai-chat-general"),
    path("chat/history/", ChatHistoryView.as_view(), name="ai-chat-history"),
]

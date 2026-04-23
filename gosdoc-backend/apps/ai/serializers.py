"""
ГосДок — Сериализаторы AI-сервиса (apps/ai/serializers.py)

Входные данные для endpoints:
  - GenerateDocumentSerializer   — POST /api/v1/ai/generate/
  - SummarizeDocumentSerializer  — POST /api/v1/ai/summarize/
  - SearchDocumentsSerializer    — POST /api/v1/ai/search/
  - EmbedDocumentSerializer      — POST /api/v1/ai/embed/
  - ChatWithDocumentSerializer   — POST /api/v1/ai/chat/document/
  - GeneralChatSerializer        — POST /api/v1/ai/chat/general/
  - ChatHistoryQuerySerializer   — GET  /api/v1/ai/chat/history/
  - ChatMessageSerializer        — сериализация ChatMessage для ответа
"""

from rest_framework import serializers

from .models import ChatMessage


class GenerateDocumentSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/generate/
    Генерация текста официального документа по описанию.
    """
    DOC_TYPE_CHOICES = ["contract", "order", "act", "invoice"]

    description = serializers.CharField(
        min_length=10,
        max_length=3000,
        help_text="Описание содержания документа (что должен содержать, между кем и кем, условия и т.д.)",
    )
    doc_type = serializers.ChoiceField(
        choices=DOC_TYPE_CHOICES,
        help_text="Тип документа: contract (договор), order (приказ), act (акт), invoice (счёт-фактура)",
    )


class SummarizeDocumentSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/summarize/
    Резюме существующего документа по его ID.
    """
    document_id = serializers.UUIDField(
        help_text="UUID документа, для которого нужно сгенерировать резюме",
    )


class SearchDocumentsSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/search/
    Семантический поиск по документам кабинета.
    """
    query = serializers.CharField(
        min_length=2,
        max_length=500,
        help_text="Поисковый запрос на естественном языке",
    )
    workspace_id = serializers.UUIDField(
        help_text="UUID кабинета, в котором выполняется поиск",
    )
    top_k = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=20,
        required=False,
        help_text="Количество результатов (по умолчанию 5, максимум 20)",
    )


class EmbedDocumentSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/embed/
    Ручной запуск индексации документа в pgvector.
    """
    document_id = serializers.UUIDField(
        help_text="UUID документа для индексации",
    )


class ClassifyDocumentSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/classify/
    ML-классификация типа документа.
    """
    document_id = serializers.UUIDField(
        help_text="UUID документа для классификации",
    )


# ============================================================
# Чат сериализаторы
# ============================================================

class ChatWithDocumentSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/chat/document/
    Чат с конкретным документом.
    """
    document_id = serializers.UUIDField(
        help_text="UUID документа для чата",
    )
    message = serializers.CharField(
        min_length=1,
        max_length=2000,
        help_text="Сообщение пользователя",
    )


class GeneralChatSerializer(serializers.Serializer):
    """
    POST /api/v1/ai/chat/general/
    Общий AI ассистент по кабинету.
    """
    message = serializers.CharField(
        min_length=1,
        max_length=2000,
        help_text="Сообщение пользователя",
    )
    workspace_id = serializers.UUIDField(
        help_text="UUID кабинета — контекст для поиска по документам",
    )


class ChatHistoryQuerySerializer(serializers.Serializer):
    """
    GET /api/v1/ai/chat/history/
    Фильтры для получения истории чата.
    Один из параметров обязателен: document_id или workspace_id.
    """
    document_id = serializers.UUIDField(required=False, help_text="UUID документа")
    workspace_id = serializers.UUIDField(required=False, help_text="UUID кабинета")

    def validate(self, data):
        if not data.get("document_id") and not data.get("workspace_id"):
            raise serializers.ValidationError(
                "Укажите document_id или workspace_id."
            )
        if data.get("document_id") and data.get("workspace_id"):
            raise serializers.ValidationError(
                "Укажите только один параметр: document_id или workspace_id."
            )
        return data


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор ChatMessage для GET /api/v1/ai/chat/history/.
    """
    class Meta:
        model = ChatMessage
        fields = ["id", "role", "content", "created_at"]

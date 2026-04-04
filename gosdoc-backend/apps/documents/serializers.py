"""
ГосДок — Сериализаторы документов (apps/documents/serializers.py)
Разделы 4.5, 4.8 ТЗ
"""

from django.conf import settings
from rest_framework import serializers

from .models import Comment, Document, DocumentVersion


# ============================================================
# Presigned Upload (прямая загрузка в S3, раздел 6 ТЗ)
# ============================================================

class PresignedUploadRequestSerializer(serializers.Serializer):
    """
    Шаг 1 двухэтапной загрузки: запрос presigned POST URL.
    POST /api/v1/documents/request-upload/
    """
    workspace = serializers.UUIDField(
        required=True,
        help_text="UUID кабинета, в который загружается документ",
    )
    title = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Название документа",
    )
    file_name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Оригинальное имя файла (напр. contract.pdf)",
    )
    file_size = serializers.IntegerField(
        required=True,
        min_value=1,
        help_text="Размер файла в байтах (макс. 100 МБ)",
    )

    def validate_file_name(self, value):
        from .storage import validate_file_extension
        if not validate_file_extension(value):
            raise serializers.ValidationError(
                f"Недопустимый формат. Разрешены: {', '.join(settings.ALLOWED_DOCUMENT_EXTENSIONS)}"
            )
        return value

    def validate_file_size(self, value):
        if value > settings.MAX_DOCUMENT_SIZE_BYTES:
            raise serializers.ValidationError(
                f"Файл превышает максимальный размер {settings.MAX_DOCUMENT_SIZE_BYTES // 1_048_576} МБ."
            )
        return value


class DocumentConfirmUploadSerializer(serializers.Serializer):
    """
    Шаг 2 двухэтапной загрузки: подтверждение после загрузки в S3.
    POST /api/v1/documents/
    """
    workspace = serializers.UUIDField(required=True)
    title = serializers.CharField(max_length=255, required=True)
    storage_key = serializers.CharField(
        required=True,
        help_text="Ключ объекта в S3, полученный от request-upload/",
    )
    file_name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Оригинальное имя файла (нужно для определения типа и чексуммы)",
    )


class NewVersionPresignedRequestSerializer(serializers.Serializer):
    """
    Шаг 1 для новой версии документа.
    POST /api/v1/documents/{id}/versions/request-upload/
    """
    file_name = serializers.CharField(max_length=255, required=True)
    file_size = serializers.IntegerField(required=True, min_value=1)

    def validate_file_name(self, value):
        from .storage import validate_file_extension
        if not validate_file_extension(value):
            raise serializers.ValidationError(
                f"Недопустимый формат. Разрешены: {', '.join(settings.ALLOWED_DOCUMENT_EXTENSIONS)}"
            )
        return value


class NewVersionConfirmSerializer(serializers.Serializer):
    """
    Шаг 2 для новой версии.
    POST /api/v1/documents/{id}/versions/
    """
    storage_key = serializers.CharField(required=True)
    file_name = serializers.CharField(max_length=255, required=True)


# ============================================================
# DocumentVersion
# ============================================================

class DocumentVersionSerializer(serializers.ModelSerializer):
    """Полный сериализатор версии документа."""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "document", "version_number", "storage_key",
            "checksum", "ai_changes_detected", "ai_diff_summary",
            "created_by", "created_by_name", "created_at",
        ]
        read_only_fields = [
            "id", "version_number", "checksum",
            "ai_changes_detected", "ai_diff_summary",
            "created_by", "created_at",
        ]


class DocumentVersionListSerializer(serializers.ModelSerializer):
    """Краткий вид версии для списков."""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "version_number", "checksum",
            "ai_changes_detected", "created_by_name", "created_at",
        ]
        read_only_fields = fields


# ============================================================
# Document
# ============================================================

class DocumentSerializer(serializers.ModelSerializer):
    """
    Полный сериализатор документа.
    Используется для GET (одиночный) и PATCH.
    Создание документа — через DocumentConfirmUploadSerializer.
    """
    uploaded_by_name = serializers.CharField(source="uploaded_by.full_name", read_only=True)
    current_version_number = serializers.IntegerField(
        source="current_version.version_number", read_only=True
    )
    current_version_checksum = serializers.CharField(
        source="current_version.checksum", read_only=True
    )
    workspace_title = serializers.CharField(source="workspace.title", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "workspace", "workspace_title", "title", "file_type",
            "storage_key", "current_version", "current_version_number",
            "current_version_checksum", "status",
            "uploaded_by", "uploaded_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "file_type", "storage_key",
            "current_version", "uploaded_by",
            "created_at", "updated_at",
        ]


class DocumentListSerializer(serializers.ModelSerializer):
    """Краткий вид документа для списков."""
    uploaded_by_name = serializers.CharField(source="uploaded_by.full_name", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id", "title", "file_type", "status",
            "uploaded_by_name", "created_at", "updated_at",
        ]
        read_only_fields = fields


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для PATCH /api/v1/documents/{id}/ (только изменяемые поля)."""

    class Meta:
        model = Document
        fields = ["title"]


# ============================================================
# Комментарии (раздел 4.8 ТЗ)
# ============================================================

class CommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор комментария.
    Поддерживает вложенность (parent_id) и рекурсивные ответы.
    """
    author_name = serializers.CharField(source="author.full_name", read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True)
    replies = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id", "document", "author", "author_name", "author_email",
            "content", "parent", "is_resolved",
            "created_at", "replies_count", "replies",
        ]
        read_only_fields = ["id", "document", "author", "created_at", "is_resolved"]

    def get_replies(self, obj) -> list:
        """Возвращает только первый уровень ответов (не рекурсивно, чтобы не нагружать БД)."""
        if not hasattr(obj, "_prefetched_objects_cache"):
            return []
        replies_qs = obj.replies.filter(is_resolved=False).select_related("author")
        if replies_qs.exists():
            return CommentSerializer(
                replies_qs,
                many=True,
                context=self.context,
            ).data
        return []

    def get_replies_count(self, obj) -> int:
        return obj.replies.count()

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

    def validate_parent(self, value):
        """Комментарий-ответ должен относиться к тому же документу."""
        if value is not None:
            # document передаётся через context или из URL
            request = self.context.get("request")
            if value.document_id != self.context.get("document_id"):
                raise serializers.ValidationError(
                    "Родительский комментарий принадлежит другому документу."
                )
        return value

"""
ГосДок — Модели документов, версий и комментариев (apps/documents/models.py)
Разделы 3.5, 3.6, 3.8 ТЗ
"""

import uuid

from django.db import models


class Document(models.Model):
    """
    Документ — основная сущность системы.

    Поля по разделу 3.5 ТЗ:
    - id: UUID PK
    - workspace_id: FK → workspaces
    - title: название
    - file_type: расширение файла (pdf, docx и т.д.)
    - storage_key: ключ объекта в S3
    - storage_url: публичная/presigned URL (кэш)
    - current_version_id: FK → document_versions (текущая версия)
    - status: draft | review | signed | archived
    - uploaded_by: FK → users
    - created_at, updated_at
    """

    class DocumentStatus(models.TextChoices):
        DRAFT = "draft", "Черновик"
        REVIEW = "review", "На согласовании"
        SIGNED = "signed", "Подписан"
        ARCHIVED = "archived", "Архив"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Кабинет",
        db_index=True,
    )
    title = models.CharField(max_length=255, verbose_name="Название документа")
    file_type = models.CharField(max_length=20, verbose_name="Тип файла")
    storage_key = models.TextField(verbose_name="Ключ S3")
    storage_url = models.TextField(null=True, blank=True, verbose_name="URL файла")
    # current_version — nullable FK, заполняется после создания первой версии
    current_version = models.ForeignKey(
        "DocumentVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_documents",
        verbose_name="Текущая версия",
    )
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT,
        verbose_name="Статус",
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
        verbose_name="Загрузил",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        db_table = "documents"
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["status"]),
            models.Index(fields=["uploaded_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} [{self.get_status_display()}]"


class DocumentVersion(models.Model):
    """
    Версия документа — история изменений.

    Поля по разделу 3.6 ТЗ:
    - id: UUID PK
    - document_id: FK → documents
    - version_number: порядковый номер
    - storage_key: ключ объекта в S3
    - checksum: SHA-256 хэш файла
    - ai_changes_detected: флаг обнаружения изменений AI
    - ai_diff_summary: JSONB с описанием изменений
    - created_by: FK → users
    - created_at
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Документ",
        db_index=True,
    )
    version_number = models.IntegerField(verbose_name="Номер версии")
    storage_key = models.TextField(verbose_name="Ключ S3")
    checksum = models.CharField(
        max_length=64,
        verbose_name="SHA-256",
        help_text="SHA-256 хэш файла для контроля целостности",
    )
    ai_changes_detected = models.BooleanField(
        default=False,
        verbose_name="AI: изменения обнаружены",
    )
    ai_diff_summary = models.JSONField(
        null=True,
        blank=True,
        verbose_name="AI: описание изменений",
        help_text="JSONB с результатом AI-анализа изменений",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_versions",
        verbose_name="Создал",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Версия документа"
        verbose_name_plural = "Версии документа"
        db_table = "document_versions"
        ordering = ["-version_number"]
        unique_together = [("document", "version_number")]
        indexes = [
            models.Index(fields=["document"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} v{self.version_number}"


class Comment(models.Model):
    """
    Комментарий к документу — поддерживает вложенность (self-reference).

    Поля по разделу 3.8 ТЗ:
    - id: UUID PK
    - document_id: FK → documents
    - author_id: FK → users
    - content: текст
    - parent_id: FK → comments (рекурсия для ответов)
    - is_resolved: закрыт ли
    - created_at
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Документ",
        db_index=True,
    )
    author = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="comments",
        verbose_name="Автор",
        db_index=True,
    )
    content = models.TextField(verbose_name="Текст комментария")
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Родительский комментарий",
    )
    is_resolved = models.BooleanField(default=False, verbose_name="Закрыт")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        db_table = "comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["document"]),
            models.Index(fields=["author"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self) -> str:
        return f"Комментарий {self.author} к {self.document}"

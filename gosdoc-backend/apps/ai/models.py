"""
ГосДок — Модели AI-сервиса (apps/ai/models.py)

DocumentEmbedding — векторные представления чанков документов для RAG.
ChatMessage       — история сообщений чатов (с документом / общий).
"""

import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class DocumentEmbedding(models.Model):
    """
    Векторное представление фрагмента (чанка) документа.

    Один документ может иметь несколько чанков — каждый чанк имеет
    отдельный вектор (384 измерения, модель all-MiniLM-L6-v2).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="embeddings",
        verbose_name="Документ",
    )
    chunk_text = models.TextField(verbose_name="Текст фрагмента")
    chunk_index = models.IntegerField(verbose_name="Порядковый номер фрагмента")
    # all-MiniLM-L6-v2 выдаёт векторы размерностью 384
    embedding = VectorField(dimensions=384, verbose_name="Векторное представление")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")

    class Meta:
        verbose_name = "Векторное представление документа"
        verbose_name_plural = "Векторные представления документов"
        ordering = ["document", "chunk_index"]
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
        ]

    def __str__(self):
        return f"Embedding({self.document_id}, chunk={self.chunk_index})"


class ChatMessage(models.Model):
    """
    Сообщение в чате с AI.

    Используется для двух режимов:
      - Чат с конкретным документом (document != None, workspace == None)
      - Общий чат по кабинету   (workspace != None, document == None)
    """
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_CHOICES = [
        (ROLE_USER, "Пользователь"),
        (ROLE_ASSISTANT, "Ассистент"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
        verbose_name="Пользователь",
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_messages",
        verbose_name="Документ (для режима чата с документом)",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_messages",
        verbose_name="Кабинет (для общего чата)",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name="Роль",
    )
    content = models.TextField(verbose_name="Содержимое сообщения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Сообщение чата"
        verbose_name_plural = "Сообщения чата"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["user", "document", "created_at"]),
            models.Index(fields=["user", "workspace", "created_at"]),
        ]

    def __str__(self):
        scope = f"doc={self.document_id}" if self.document_id else f"ws={self.workspace_id}"
        return f"ChatMessage({self.role}, {scope}, user={self.user_id})"

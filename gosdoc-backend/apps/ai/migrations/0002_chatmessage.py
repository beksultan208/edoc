"""
ГосДок — Миграция: модель ChatMessage (apps/ai/migrations/0002_chatmessage.py)
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        # Предыдущая миграция AI-приложения (DocumentEmbedding)
        ("ai", "0001_initial"),
        # Document FK
        ("documents", "0002_documentauditlog"),
        # Workspace FK
        ("workspaces", "0001_workspace_organization_nullable"),
        # User FK (AUTH_USER_MODEL = "users.User")
        ("users", "0001_email_verification_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("role", models.CharField(
                    max_length=10,
                    choices=[("user", "Пользователь"), ("assistant", "Ассистент")],
                    verbose_name="Роль",
                )),
                ("content", models.TextField(verbose_name="Содержимое сообщения")),
                ("created_at", models.DateTimeField(
                    auto_now_add=True,
                    verbose_name="Создано",
                )),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_messages",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_messages",
                        to="documents.document",
                        verbose_name="Документ (для режима чата с документом)",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_messages",
                        to="workspaces.workspace",
                        verbose_name="Кабинет (для общего чата)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Сообщение чата",
                "verbose_name_plural": "Сообщения чата",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(
                fields=["user", "document", "created_at"],
                name="ai_chatmsg_user_doc_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(
                fields=["user", "workspace", "created_at"],
                name="ai_chatmsg_user_ws_idx",
            ),
        ),
    ]

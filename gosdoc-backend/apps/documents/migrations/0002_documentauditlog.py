"""
Миграция: создаёт таблицу document_audit_logs для аудит-лога.
Раздел 6 ТЗ: «Логирование всех действий с документами».
"""

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Добавляет модель DocumentAuditLog."""

    dependencies = [
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentAuditLog",
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
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("created", "Создан"),
                            ("updated", "Обновлён"),
                            ("archived", "Архивирован"),
                            ("workflow_started", "Workflow запущен"),
                            ("signed", "Подписан"),
                            ("version_uploaded", "Версия загружена"),
                            ("comment_added", "Комментарий добавлен"),
                            ("downloaded", "Скачан"),
                        ],
                        db_index=True,
                        max_length=50,
                        verbose_name="Действие",
                    ),
                ),
                (
                    "details",
                    models.JSONField(
                        blank=True,
                        null=True,
                        verbose_name="Детали",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(
                        blank=True,
                        null=True,
                        verbose_name="IP-адрес",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        verbose_name="Время действия",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_logs",
                        to="documents.document",
                        verbose_name="Документ",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="document_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Аудит-лог документа",
                "verbose_name_plural": "Аудит-логи документов",
                "db_table": "document_audit_logs",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="documentauditlog",
            index=models.Index(
                fields=["document"], name="audit_document_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="documentauditlog",
            index=models.Index(
                fields=["user"], name="audit_user_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="documentauditlog",
            index=models.Index(
                fields=["action"], name="audit_action_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="documentauditlog",
            index=models.Index(
                fields=["timestamp"], name="audit_timestamp_idx"
            ),
        ),
    ]

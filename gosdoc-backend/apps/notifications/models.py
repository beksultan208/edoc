"""
ГосДок — Модель уведомлений (apps/notifications/models.py)
Раздел 3.10 ТЗ
"""

import uuid

from django.db import models


class Notification(models.Model):
    """
    Внутреннее уведомление пользователя.

    Поля по разделу 3.10 ТЗ:
    - id: UUID PK
    - user_id: FK → users (получатель)
    - type: тип события (task_assigned, signed и т.д.)
    - title: заголовок
    - message: текст
    - entity_type: тип сущности (document, task и т.д.)
    - entity_id: UUID сущности
    - is_read: прочитано ли
    - created_at
    """

    # Типы уведомлений (раздел 2.8 ТЗ)
    class NotificationType(models.TextChoices):
        TASK_ASSIGNED = "task_assigned", "Задача назначена"
        STEP_COMPLETED = "step_completed", "Шаг завершён"
        DOCUMENT_SIGNED = "document_signed", "Документ подписан"
        NEW_COMMENT = "new_comment", "Новый комментарий"
        DEADLINE_APPROACHING = "deadline_approaching", "Срок истекает"
        DOCUMENT_REJECTED = "document_rejected", "Документ отклонён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Пользователь",
        db_index=True,
    )
    type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        verbose_name="Тип уведомления",
        db_index=True,
    )
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    message = models.TextField(null=True, blank=True, verbose_name="Текст")
    entity_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Тип сущности",
    )
    entity_id = models.UUIDField(
        null=True,
        blank=True,
        verbose_name="ID сущности",
    )
    is_read = models.BooleanField(default=False, verbose_name="Прочитано", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} → {self.user}"

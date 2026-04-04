"""
ГосДок — Модель задачи workflow (apps/tasks/models.py)
Раздел 3.9 ТЗ
"""

import uuid

from django.db import models


class Task(models.Model):
    """
    Задача — шаг в цепочке workflow для документа.

    Поля по разделу 3.9 ТЗ:
    - id: UUID PK
    - workspace_id: FK → workspaces
    - document_id: FK → documents
    - assigned_to: FK → users (исполнитель)
    - step_order: порядок шага
    - title: название задачи
    - status: pending | in_progress | done | skipped
    - due_date: срок выполнения
    - completed_at: дата завершения
    """

    class TaskStatus(models.TextChoices):
        PENDING = "pending", "Ожидает"
        IN_PROGRESS = "in_progress", "В работе"
        DONE = "done", "Завершена"
        SKIPPED = "skipped", "Пропущена"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Кабинет",
        db_index=True,
    )
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Документ",
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_tasks",
        verbose_name="Исполнитель",
        db_index=True,
    )
    step_order = models.IntegerField(verbose_name="Порядок шага")
    title = models.CharField(max_length=255, verbose_name="Название задачи")
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        verbose_name="Статус",
        db_index=True,
    )
    due_date = models.DateField(null=True, blank=True, verbose_name="Срок выполнения")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        db_table = "tasks"
        ordering = ["step_order"]
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["document"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["status"]),
            models.Index(fields=["step_order"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} [шаг {self.step_order}] — {self.get_status_display()}"

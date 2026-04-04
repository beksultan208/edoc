"""
ГосДок — Модели рабочих кабинетов (apps/workspaces/models.py)
Разделы 3.3, 3.4 ТЗ
"""

import uuid

from django.db import models


class Workspace(models.Model):
    """
    Рабочий кабинет — контейнер для документов и участников workflow.

    Поля по разделу 3.3 ТЗ:
    - id: UUID PK
    - title: название
    - type: individual | corporate
    - organization_id: FK → organizations
    - created_by: FK → users
    - status: active | archived | closed
    - description: описание
    - deadline: срок завершения
    - created_at
    """

    class WorkspaceType(models.TextChoices):
        INDIVIDUAL = "individual", "Индивидуальный"
        CORPORATE = "corporate", "Корпоративный"

    class WorkspaceStatus(models.TextChoices):
        ACTIVE = "active", "Активный"
        ARCHIVED = "archived", "Архивный"
        CLOSED = "closed", "Закрытый"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name="Название")
    type = models.CharField(
        max_length=20,
        choices=WorkspaceType.choices,
        verbose_name="Тип кабинета",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workspaces",
        verbose_name="Организация",
        db_index=True,
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workspaces",
        verbose_name="Создатель",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=WorkspaceStatus.choices,
        default=WorkspaceStatus.ACTIVE,
        verbose_name="Статус",
    )
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    deadline = models.DateField(null=True, blank=True, verbose_name="Срок")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Рабочий кабинет"
        verbose_name_plural = "Рабочие кабинеты"
        db_table = "workspaces"
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["status"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_type_display()})"


class WorkspaceMember(models.Model):
    """
    Участник рабочего кабинета — связь многие-ко-многим с ролью и шагом workflow.

    Поля по разделу 3.4 ТЗ:
    - id: UUID PK
    - workspace_id: FK → workspaces
    - user_id: FK → users
    - role: owner | editor | signer | viewer
    - step_order: порядковый номер шага в workflow
    - joined_at
    - UNIQUE(workspace_id, user_id)
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Владелец"
        EDITOR = "editor", "Редактор"
        SIGNER = "signer", "Подписант"
        VIEWER = "viewer", "Наблюдатель"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Кабинет",
        db_index=True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
        verbose_name="Пользователь",
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name="Роль",
    )
    step_order = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Порядок шага",
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата вступления")

    class Meta:
        verbose_name = "Участник кабинета"
        verbose_name_plural = "Участники кабинета"
        db_table = "workspace_members"
        unique_together = [("workspace", "user")]  # UNIQUE(workspace_id, user_id)
        indexes = [
            models.Index(fields=["workspace"]),
            models.Index(fields=["user"]),
            models.Index(fields=["role"]),
            models.Index(fields=["step_order"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.workspace} [{self.get_role_display()}]"

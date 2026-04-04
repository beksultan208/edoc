"""
ГосДок — Модель организации (apps/organizations/models.py)
Раздел 3.1 ТЗ
"""

import uuid

from django.db import models


class Organization(models.Model):
    """
    Организация — юридическое лицо, которому принадлежат кабинеты и пользователи.

    Поля по разделу 3.1 ТЗ:
    - id: UUID PK
    - name: название
    - type: individual | corporate
    - inn: ИНН (уникальный)
    - address: адрес
    - owner_id: FK → users
    - created_at
    """

    class OrgType(models.TextChoices):
        INDIVIDUAL = "individual", "Индивидуальный"
        CORPORATE = "corporate", "Корпоративный"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    name = models.CharField(max_length=255, verbose_name="Название организации")
    type = models.CharField(
        max_length=20,
        choices=OrgType.choices,
        verbose_name="Тип",
    )
    inn = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="ИНН",
    )
    address = models.TextField(blank=True, null=True, verbose_name="Адрес")
    # owner устанавливается после создания users, поэтому nullable
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_organizations",
        verbose_name="Владелец",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Организация"
        verbose_name_plural = "Организации"
        db_table = "organizations"
        indexes = [
            models.Index(fields=["owner"]),
            models.Index(fields=["type"]),
            models.Index(fields=["inn"]),
        ]

    def __str__(self) -> str:
        return self.name

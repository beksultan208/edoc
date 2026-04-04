"""
ГосДок — Модель электронной подписи (apps/signatures/models.py)
Раздел 3.7 ТЗ
"""

import uuid

from django.db import models


class Signature(models.Model):
    """
    Электронная подпись документа.

    Поля по разделу 3.7 ТЗ:
    - id: UUID PK
    - document_id: FK → documents
    - user_id: FK → users
    - signature_data: Base64 данные подписи (canvas/КЭП)
    - certificate_id: ID сертификата КЭП
    - signed_at: время подписания
    - ip_address: IP-адрес подписанта
    - is_valid: статус верификации
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "documents.Document",
        on_delete=models.CASCADE,
        related_name="signatures",
        verbose_name="Документ",
        db_index=True,
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="signatures",
        verbose_name="Подписант",
        db_index=True,
    )
    signature_data = models.TextField(
        verbose_name="Данные подписи",
        help_text="Base64-encoded данные рукописной подписи или КЭП",
    )
    certificate_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="ID сертификата КЭП",
    )
    signed_at = models.DateTimeField(auto_now_add=True, verbose_name="Время подписания")
    ip_address = models.GenericIPAddressField(verbose_name="IP-адрес")
    is_valid = models.BooleanField(default=True, verbose_name="Действительна")

    class Meta:
        verbose_name = "Подпись"
        verbose_name_plural = "Подписи"
        db_table = "signatures"
        indexes = [
            models.Index(fields=["document"]),
            models.Index(fields=["user"]),
            models.Index(fields=["signed_at"]),
        ]

    def __str__(self) -> str:
        return f"Подпись {self.user} на {self.document}"

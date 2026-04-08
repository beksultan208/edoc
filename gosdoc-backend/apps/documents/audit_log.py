"""
ГосДок — Аудит-лог документов (apps/documents/audit_log.py)
Раздел 6 ТЗ: «Логирование всех действий с документами».

Утилита log_document_action() — единая точка входа для записи в аудит-лог.
Вызывается из views.py при ключевых действиях с документами.
"""

import logging

logger = logging.getLogger(__name__)


def log_document_action(
    document,
    user,
    action: str,
    details: dict = None,
    ip_address: str = None,
):
    """
    Записывает действие с документом в таблицу document_audit_logs.

    Args:
        document:   экземпляр Document
        user:       экземпляр User (инициатор действия)
        action:     строка из DocumentAuditLog.Action (created, archived, signed и т.д.)
        details:    словарь с дополнительными данными (сохраняется в JSONB)
        ip_address: IP-адрес инициатора (из request.META)

    Returns:
        DocumentAuditLog | None  — запись лога или None при ошибке
    """
    from apps.documents.models import DocumentAuditLog

    try:
        return DocumentAuditLog.objects.create(
            document=document,
            user=user,
            action=action,
            details=details or {},
            ip_address=ip_address,
        )
    except Exception as exc:
        # Ошибка аудит-лога не должна прерывать бизнес-логику
        logger.error(
            "Ошибка записи аудит-лога [action=%s, doc=%s]: %s",
            action, getattr(document, "id", "?"), exc,
        )
        return None


def get_client_ip(request) -> str | None:
    """
    Извлекает реальный IP-адрес клиента из запроса.
    Учитывает reverse proxy (X-Forwarded-For).
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

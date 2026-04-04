"""
ГосДок — Сервисный слой для уведомлений (apps/notifications/services.py)
Раздел 2.8 ТЗ — триггеры уведомлений.

Все функции здесь — тонкая обёртка, которая:
1. Создаёт запись в таблице notifications (внутреннее уведомление)
2. Ставит задачу в очередь Celery для email-отправки
"""

import logging

logger = logging.getLogger(__name__)


def notify_new_comment(comment):
    """
    Уведомляет всех участников кабинета о новом комментарии.
    Раздел 2.8 ТЗ: «Новый комментарий → Платформа → Все участники кабинета».
    """
    from apps.notifications.models import Notification

    document = comment.document
    author = comment.author
    members = document.workspace.members.select_related("user").exclude(user=author)

    notifications = [
        Notification(
            user=member.user,
            type=Notification.NotificationType.NEW_COMMENT,
            title=f"Новый комментарий к «{document.title}»",
            message=f"{author.full_name}: {comment.content[:100]}{'...' if len(comment.content) > 100 else ''}",
            entity_type="document",
            entity_id=document.id,
        )
        for member in members
    ]
    Notification.objects.bulk_create(notifications, ignore_conflicts=True)


def notify_document_rejected(document, rejected_by):
    """
    Уведомляет инициатора о том, что документ отклонён.
    Раздел 2.8 ТЗ: «Документ отклонён → Email + Платформа → Инициатор».
    """
    from apps.notifications.models import Notification
    from apps.notifications.tasks import send_email_notification

    initiator = document.uploaded_by
    if not initiator:
        return

    Notification.objects.create(
        user=initiator,
        type=Notification.NotificationType.DOCUMENT_REJECTED,
        title=f"Документ «{document.title}» отклонён",
        message=f"Отклонил(а): {rejected_by.full_name}.",
        entity_type="document",
        entity_id=document.id,
    )

    try:
        send_email_notification.delay(
            recipient_email=initiator.email,
            subject=f"ГосДок: документ отклонён — {document.title}",
            message=(
                f"Здравствуйте, {initiator.full_name}!\n\n"
                f"Ваш документ «{document.title}» был отклонён пользователем {rejected_by.full_name}.\n"
                f"Войдите в систему для получения подробностей."
            ),
        )
    except Exception as exc:
        logger.warning("Не удалось поставить email об отклонении в очередь: %s", exc)

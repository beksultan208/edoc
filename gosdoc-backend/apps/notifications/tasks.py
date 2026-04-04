"""
ГосДок — Celery-задачи для уведомлений (apps/notifications/tasks.py)
Раздел 2.8 ТЗ
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# Email-задачи
# ============================================================

@shared_task(
    name="apps.notifications.tasks.send_email_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Повтор через 60 сек при сбое
)
def send_email_notification(self, recipient_email: str, subject: str, message: str):
    """
    Отправляет email-уведомление через SMTP.
    При сбое повторяет до 3 раз с задержкой 60 сек.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info("Email отправлен: [%s] → %s", subject, recipient_email)
    except Exception as exc:
        logger.error("Ошибка отправки email на %s: %s", recipient_email, exc)
        # Повторяем задачу при сбое
        raise self.retry(exc=exc)


@shared_task(
    name="apps.notifications.tasks.send_bulk_email",
    bind=True,
    max_retries=2,
)
def send_bulk_email(self, recipient_emails: list, subject: str, message: str):
    """
    Отправляет одно письмо нескольким получателям (BCC).
    Используется для уведомлений всех участников кабинета.
    """
    if not recipient_emails:
        return

    try:
        from django.core.mail import EmailMessage
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],   # Основной получатель — сам сервис
            bcc=recipient_emails,               # Скрытая копия всем участникам
        )
        email.send(fail_silently=False)
        logger.info(
            "Массовая рассылка: [%s] → %d получателей",
            subject, len(recipient_emails),
        )
    except Exception as exc:
        logger.error("Ошибка массовой рассылки [%s]: %s", subject, exc)
        raise self.retry(exc=exc)


# ============================================================
# Celery Beat задачи
# ============================================================

@shared_task(name="apps.notifications.tasks.check_task_deadlines")
def check_task_deadlines():
    """
    Проверяет задачи с дедлайном ровно через 24 часа.
    Раздел 2.8 ТЗ: уведомление за 24ч до срока.
    Запускается Celery Beat каждый час.
    """
    from apps.notifications.models import Notification
    from apps.tasks.models import Task

    tomorrow = timezone.now().date() + timedelta(days=1)

    tasks_due = Task.objects.filter(
        due_date=tomorrow,
        status=Task.TaskStatus.IN_PROGRESS,
    ).select_related("assigned_to", "document", "workspace")

    notified_count = 0

    for task in tasks_due:
        # Уведомление исполнителю
        if task.assigned_to:
            _, created = Notification.objects.get_or_create(
                user=task.assigned_to,
                type=Notification.NotificationType.DEADLINE_APPROACHING,
                entity_type="task",
                entity_id=task.id,
                defaults={
                    "title": f"Срок задачи истекает завтра: {task.title}",
                    "message": f"Задача «{task.title}» должна быть завершена до {task.due_date}.",
                },
            )
            if created:
                send_email_notification.delay(
                    recipient_email=task.assigned_to.email,
                    subject=f"ГосДок: срок задачи истекает — {task.title}",
                    message=(
                        f"Здравствуйте, {task.assigned_to.full_name}!\n\n"
                        f"Задача «{task.title}» по документу «{task.document.title}» "
                        f"должна быть завершена до {task.due_date}.\n"
                        f"Войдите в систему для выполнения задачи."
                    ),
                )
                notified_count += 1

        # Уведомление владельцам кабинета
        owners = (
            task.workspace.members
            .filter(role="owner")
            .select_related("user")
            .exclude(user=task.assigned_to)
        )
        for owner_member in owners:
            Notification.objects.get_or_create(
                user=owner_member.user,
                type=Notification.NotificationType.DEADLINE_APPROACHING,
                entity_type="task",
                entity_id=task.id,
                defaults={
                    "title": f"Срок задачи истекает завтра: {task.title}",
                    "message": (
                        f"Исполнитель: {task.assigned_to.full_name if task.assigned_to else '—'}. "
                        f"Срок: {task.due_date}."
                    ),
                },
            )

    logger.info(
        "Проверка дедлайнов завершена: найдено %d задач с истекающим сроком, "
        "отправлено %d новых уведомлений",
        tasks_due.count(), notified_count,
    )
    return {"tasks_checked": tasks_due.count(), "notifications_sent": notified_count}

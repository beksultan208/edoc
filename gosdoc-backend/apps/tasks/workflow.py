"""
ГосДок — Логика workflow (apps/tasks/workflow.py)
Раздел 2.3 ТЗ: цепочка шагов, активация следующего шага.

Поток:
  1. create_workflow_tasks()   — создаёт задачи из участников кабинета,
                                 активирует первый шаг
  2. activate_next_task()      — при завершении задачи активирует следующую
  3. Когда все шаги пройдены  — вызывает _mark_all_steps_done()
"""

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


# ============================================================
# Публичный API workflow
# ============================================================

def create_workflow_tasks(document, workspace) -> list:
    """
    Создаёт задачи для каждого участника с step_order, активирует первый шаг.

    Алгоритм (раздел 2.3 ТЗ):
    - Для каждого участника с заполненным step_order создаётся Task(status=pending)
    - Задача с наименьшим step_order переводится в in_progress
    - Исполнитель первой задачи получает уведомление
    """
    from apps.tasks.models import Task

    # Участники с заданным step_order, отсортированные по нему
    members = (
        workspace.members
        .filter(step_order__isnull=False)
        .order_by("step_order")
        .select_related("user")
    )

    if not members.exists():
        logger.warning(
            "Нет участников с step_order в кабинете '%s', workflow не создан",
            workspace.title,
        )
        return []

    # Создаём все задачи разом (bulk_create)
    task_objects = [
        Task(
            workspace=workspace,
            document=document,
            assigned_to=member.user,
            step_order=member.step_order,
            title=f"Шаг {member.step_order}: {member.get_role_display()} — {document.title}",
            status=Task.TaskStatus.PENDING,
        )
        for member in members
    ]
    created_tasks = Task.objects.bulk_create(task_objects)

    # Активируем первую задачу
    first_task = Task.objects.filter(
        document=document,
        status=Task.TaskStatus.PENDING,
    ).order_by("step_order").first()

    if first_task:
        first_task.status = Task.TaskStatus.IN_PROGRESS
        first_task.save(update_fields=["status"])

        _send_task_assigned_notification(first_task)
        _send_task_assigned_email(first_task)

        logger.info(
            "Первый шаг workflow активирован: задача '%s' (шаг %d) → %s",
            first_task.title, first_task.step_order, first_task.assigned_to.email,
        )

    return created_tasks


def activate_next_task(completed_task) -> "Task | None":
    """
    После завершения текущей задачи активирует следующую в цепочке.

    Алгоритм (раздел 2.3 ТЗ):
    - Ищем задачу с наименьшим step_order > completed_task.step_order со статусом pending
    - Если найдена: переводим в in_progress, уведомляем исполнителя
    - Если не найдена: все шаги пройдены → вызываем _mark_all_steps_done()
    """
    from apps.tasks.models import Task

    next_task = (
        Task.objects.filter(
            document=completed_task.document,
            step_order__gt=completed_task.step_order,
            status=Task.TaskStatus.PENDING,
        )
        .order_by("step_order")
        .first()
    )

    if next_task:
        next_task.status = Task.TaskStatus.IN_PROGRESS
        next_task.save(update_fields=["status"])

        _send_task_assigned_notification(next_task)
        _send_task_assigned_email(next_task)

        logger.info(
            "Следующий шаг workflow: задача '%s' (шаг %d) → %s",
            next_task.title, next_task.step_order, next_task.assigned_to.email,
        )
        return next_task

    # Все шаги пройдены
    _mark_all_steps_done(completed_task.document)
    return None


# ============================================================
# Внутренние функции
# ============================================================

def _mark_all_steps_done(document):
    """
    Вызывается когда все шаги workflow пройдены.
    Уведомляет всех участников кабинета о готовности документа к подписи.
    """
    logger.info(
        "Все шаги workflow завершены для документа '%s'. Готов к подписи.",
        document.title,
    )
    from apps.notifications.models import Notification
    _notify_all_workspace_members(
        document=document,
        notification_type=Notification.NotificationType.STEP_COMPLETED,
        title=f"Документ «{document.title}» готов к подписи",
        message="Все шаги согласования пройдены. Документ ожидает электронной подписи.",
    )


def _send_task_assigned_notification(task):
    """
    Создаёт внутреннее уведомление о назначенной задаче.
    Раздел 2.8 ТЗ: «Задача назначена → Платформа → Исполнитель».
    """
    from apps.notifications.models import Notification

    if not task.assigned_to:
        return

    Notification.objects.create(
        user=task.assigned_to,
        type=Notification.NotificationType.TASK_ASSIGNED,
        title=f"Новая задача: {task.title}",
        message=(
            f"Вам назначена задача по документу «{task.document.title}». "
            f"Шаг {task.step_order}."
            + (f" Срок: {task.due_date}." if task.due_date else "")
        ),
        entity_type="task",
        entity_id=task.id,
    )


def _send_task_assigned_email(task):
    """
    Отправляет email-уведомление о назначенной задаче через Celery.
    Раздел 2.8 ТЗ: «Задача назначена → Email → Исполнитель».
    """
    if not task.assigned_to:
        return

    try:
        from apps.notifications.tasks import send_email_notification
        send_email_notification.delay(
            recipient_email=task.assigned_to.email,
            subject=f"ГосДок: новая задача — {task.title}",
            message=(
                f"Здравствуйте, {task.assigned_to.full_name}!\n\n"
                f"Вам назначена задача по документу «{task.document.title}».\n"
                f"Задача: {task.title}\n"
                f"Шаг: {task.step_order}\n"
                + (f"Срок: {task.due_date}\n" if task.due_date else "")
                + f"\nВойдите в систему для выполнения задачи."
            ),
        )
    except Exception as exc:
        # Email-сбой не должен прерывать workflow
        logger.warning("Не удалось поставить задачу email в очередь: %s", exc)


def _notify_all_workspace_members(document, notification_type, title: str, message: str):
    """
    Создаёт уведомление всем участникам кабинета.
    notification_type — строка или Notification.NotificationType значение.
    """
    from apps.notifications.models import Notification

    members = document.workspace.members.select_related("user").all()
    notifications = [
        Notification(
            user=member.user,
            type=notification_type,
            title=title,
            message=message,
            entity_type="document",
            entity_id=document.id,
        )
        for member in members
    ]
    Notification.objects.bulk_create(notifications, ignore_conflicts=True)


def notify_document_signed(document, signer):
    """
    Уведомляет всех участников кабинета о подписанном документе.
    Раздел 2.8 ТЗ: «Документ подписан → Email + Платформа → Все участники».
    Вызывается из apps/signatures/views.py после подписи.
    """
    from apps.notifications.models import Notification
    _notify_all_workspace_members(
        document=document,
        notification_type=Notification.NotificationType.DOCUMENT_SIGNED,
        title=f"Документ «{document.title}» подписан",
        message=f"Документ подписал(а): {signer.full_name}.",
    )

    # Email всем участникам через Celery
    try:
        from apps.notifications.tasks import send_email_notification
        members = document.workspace.members.select_related("user").all()
        for member in members:
            send_email_notification.delay(
                recipient_email=member.user.email,
                subject=f"ГосДок: документ подписан — {document.title}",
                message=(
                    f"Здравствуйте, {member.user.full_name}!\n\n"
                    f"Документ «{document.title}» подписан пользователем {signer.full_name}.\n"
                    f"Войдите в систему для просмотра."
                ),
            )
    except Exception as exc:
        logger.warning("Не удалось отправить email о подписи: %s", exc)

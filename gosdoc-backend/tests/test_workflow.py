"""
ГосДок — Тесты workflow (tests/test_workflow.py)
Раздел 9 ТЗ: workflow (step_order), логика цепочки шагов.
"""

import pytest
from unittest.mock import patch

from apps.tasks.workflow import activate_next_task, create_workflow_tasks
from tests.factories import (
    DocumentFactory,
    TaskFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


# ============================================================
# create_workflow_tasks
# ============================================================

@pytest.mark.django_db
class TestCreateWorkflowTasks:

    def test_creates_tasks_for_each_member_with_step_order(self):
        """Создаёт задачи для участников с step_order."""
        user1 = UserFactory()
        user2 = UserFactory()
        ws = WorkspaceFactory(created_by=user1)
        WorkspaceMemberFactory(workspace=ws, user=user1, role="owner", step_order=1)
        WorkspaceMemberFactory(workspace=ws, user=user2, role="signer", step_order=2)
        doc = DocumentFactory(workspace=ws, uploaded_by=user1)

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            tasks = create_workflow_tasks(doc, ws)

        assert len(tasks) == 2

    def test_first_task_activated(self):
        """Первая задача переходит в in_progress."""
        user1 = UserFactory()
        user2 = UserFactory()
        ws = WorkspaceFactory(created_by=user1)
        WorkspaceMemberFactory(workspace=ws, user=user1, role="owner", step_order=1)
        WorkspaceMemberFactory(workspace=ws, user=user2, role="signer", step_order=2)
        doc = DocumentFactory(workspace=ws, uploaded_by=user1)

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            create_workflow_tasks(doc, ws)

        from apps.tasks.models import Task
        tasks = Task.objects.filter(document=doc).order_by("step_order")
        assert tasks[0].status == "in_progress"  # шаг 1 активен
        assert tasks[1].status == "pending"       # шаг 2 ожидает

    def test_no_members_returns_empty(self):
        """Без участников с step_order — возвращает пустой список."""
        user = UserFactory()
        ws = WorkspaceFactory(created_by=user)
        WorkspaceMemberFactory(workspace=ws, user=user, role="owner", step_order=None)
        doc = DocumentFactory(workspace=ws, uploaded_by=user)

        tasks = create_workflow_tasks(doc, ws)
        assert tasks == []

    def test_creates_notification_for_first_assignee(self):
        """Создаётся уведомление для первого исполнителя."""
        user1 = UserFactory()
        ws = WorkspaceFactory(created_by=user1)
        WorkspaceMemberFactory(workspace=ws, user=user1, role="owner", step_order=1)
        doc = DocumentFactory(workspace=ws, uploaded_by=user1)

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            create_workflow_tasks(doc, ws)

        from apps.notifications.models import Notification
        notif = Notification.objects.filter(user=user1, type="task_assigned").first()
        assert notif is not None


# ============================================================
# activate_next_task
# ============================================================

@pytest.mark.django_db
class TestActivateNextTask:

    def _setup_two_step_workflow(self):
        """Создаёт кабинет с двумя задачами (step 1 и step 2)."""
        user1 = UserFactory()
        user2 = UserFactory()
        ws = WorkspaceFactory(created_by=user1)
        doc = DocumentFactory(workspace=ws, uploaded_by=user1)
        task1 = TaskFactory(
            workspace=ws, document=doc, assigned_to=user1,
            step_order=1, status="in_progress",
        )
        task2 = TaskFactory(
            workspace=ws, document=doc, assigned_to=user2,
            step_order=2, status="pending",
        )
        return task1, task2, user1, user2

    def test_activates_next_pending_task(self):
        """После завершения шага 1 шаг 2 становится in_progress."""
        task1, task2, _, _ = self._setup_two_step_workflow()
        task1.status = "done"
        task1.save()

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            next_task = activate_next_task(task1)

        task2.refresh_from_db()
        assert task2.status == "in_progress"
        assert next_task.pk == task2.pk

    def test_returns_none_when_all_done(self):
        """Когда следующего шага нет — возвращает None и вызывает _mark_all_steps_done."""
        user1 = UserFactory()
        ws = WorkspaceFactory(created_by=user1)
        doc = DocumentFactory(workspace=ws, uploaded_by=user1)
        # Создаём участника, чтобы _notify работал без ошибок
        WorkspaceMemberFactory(workspace=ws, user=user1, role="owner")
        task1 = TaskFactory(
            workspace=ws, document=doc, assigned_to=user1,
            step_order=1, status="done",
        )

        with patch("apps.tasks.workflow._send_task_assigned_email"), \
             patch("apps.tasks.workflow._mark_all_steps_done") as mock_done:
            result = activate_next_task(task1)

        assert result is None
        mock_done.assert_called_once_with(doc)

    def test_skipped_task_also_activates_next(self):
        """Пропущенная задача тоже активирует следующую."""
        task1, task2, _, _ = self._setup_two_step_workflow()
        task1.status = "skipped"
        task1.save()

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            next_task = activate_next_task(task1)

        task2.refresh_from_db()
        assert task2.status == "in_progress"

    def test_notification_sent_to_next_assignee(self):
        """Уведомление отправляется следующему исполнителю."""
        task1, task2, _, user2 = self._setup_two_step_workflow()
        task1.status = "done"
        task1.save()

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            activate_next_task(task1)

        from apps.notifications.models import Notification
        notif = Notification.objects.filter(user=user2, type="task_assigned").first()
        assert notif is not None


# ============================================================
# Task views — complete / skip
# ============================================================

@pytest.mark.django_db
class TestTaskCompleteView:

    def test_assignee_can_complete_task(self, auth_client, task):
        """Исполнитель может завершить свою задачу."""
        with patch("apps.tasks.workflow.activate_next_task"):
            response = auth_client.post(f"/api/v1/tasks/{task.pk}/complete/")
        assert response.status_code == 200
        task.refresh_from_db()
        assert task.status == "done"

    def test_other_user_cannot_complete(self, auth_client_second, task):
        """Другой пользователь не может завершить чужую задачу."""
        response = auth_client_second.post(f"/api/v1/tasks/{task.pk}/complete/")
        assert response.status_code in (403, 404)

    def test_cannot_complete_pending_task(self, auth_client, workspace, document, user):
        """Задача в статусе pending не может быть завершена."""
        task = TaskFactory(
            workspace=workspace, document=document,
            assigned_to=user, status="pending",
        )
        response = auth_client.post(f"/api/v1/tasks/{task.pk}/complete/")
        assert response.status_code == 400


@pytest.mark.django_db
class TestTaskSkipView:

    def test_owner_can_skip_task(self, auth_client, task):
        """Владелец кабинета может пропустить задачу."""
        with patch("apps.tasks.workflow.activate_next_task"):
            response = auth_client.post(f"/api/v1/tasks/{task.pk}/skip/")
        assert response.status_code == 200
        task.refresh_from_db()
        assert task.status == "skipped"

"""
ГосДок — Тесты уведомлений (tests/test_notifications.py)
Разделы 4.9, 2.8 ТЗ: список, отметка прочитанных, фильтрация.

Сценарии:
- Список уведомлений пользователя (только свои)
- Фильтр по is_read
- Отметить одно уведомление как прочитанное
- Отметить чужое уведомление → 404
- Отметить все как прочитанные
- Триггеры: task_assigned создаёт уведомление (проверка через workflow)
"""

import pytest

from tests.factories import (
    NotificationFactory,
    UserFactory,
)


def _auth_client_for(user):
    """Создаёт APIClient, авторизованный от имени user."""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ============================================================
# GET /api/v1/notifications/
# ============================================================

@pytest.mark.django_db
class TestNotificationListView:

    def test_requires_auth(self):
        """Список уведомлений требует авторизации."""
        from rest_framework.test import APIClient
        response = APIClient().get("/api/v1/notifications/")
        assert response.status_code == 401

    def test_returns_user_notifications(self, user, auth_client):
        """Пользователь видит только свои уведомления."""
        NotificationFactory(user=user, title="Моё уведомление")
        NotificationFactory(user=user, title="Моё второе")

        response = auth_client.get("/api/v1/notifications/")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert len(results) >= 2

    def test_excludes_other_users_notifications(self, auth_client):
        """Чужие уведомления не видны."""
        other = UserFactory()
        NotificationFactory(user=other, title="Чужое")

        response = auth_client.get("/api/v1/notifications/")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        titles = [n["title"] for n in results]
        assert "Чужое" not in titles

    def test_filter_by_is_read_false(self, user, auth_client):
        """Фильтр is_read=false возвращает только непрочитанные."""
        NotificationFactory(user=user, is_read=False)
        NotificationFactory(user=user, is_read=True)

        response = auth_client.get("/api/v1/notifications/?is_read=false")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for notif in results:
            assert notif["is_read"] is False

    def test_filter_by_is_read_true(self, user, auth_client):
        """Фильтр is_read=true возвращает только прочитанные."""
        NotificationFactory(user=user, is_read=False)
        NotificationFactory(user=user, is_read=True)

        response = auth_client.get("/api/v1/notifications/?is_read=true")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for notif in results:
            assert notif["is_read"] is True

    def test_filter_by_type(self, user, auth_client):
        """Фильтрация по типу уведомления."""
        NotificationFactory(user=user, type="task_assigned")
        NotificationFactory(user=user, type="document_signed")

        response = auth_client.get("/api/v1/notifications/?type=task_assigned")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for notif in results:
            assert notif["type"] == "task_assigned"

    def test_empty_list_for_new_user(self, auth_client):
        """Новый пользователь без уведомлений получает пустой список."""
        response = auth_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        results = response.data.get("results", response.data)
        assert isinstance(results, list)


# ============================================================
# POST /api/v1/notifications/{id}/read/
# ============================================================

@pytest.mark.django_db
class TestNotificationReadView:

    def test_mark_own_notification_as_read(self, user, auth_client):
        """Пользователь может отметить своё уведомление как прочитанное."""
        notif = NotificationFactory(user=user, is_read=False)

        response = auth_client.post(f"/api/v1/notifications/{notif.pk}/read/")

        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_read_other_user_notification_returns_404(self, auth_client):
        """Попытка прочитать чужое уведомление — 404."""
        other = UserFactory()
        notif = NotificationFactory(user=other, is_read=False)

        response = auth_client.post(f"/api/v1/notifications/{notif.pk}/read/")

        assert response.status_code == 404
        notif.refresh_from_db()
        assert notif.is_read is False  # не изменилось

    def test_requires_auth(self, user):
        """Без авторизации — 401."""
        from rest_framework.test import APIClient
        notif = NotificationFactory(user=user)

        response = APIClient().post(f"/api/v1/notifications/{notif.pk}/read/")

        assert response.status_code == 401

    def test_already_read_notification_stays_read(self, user, auth_client):
        """Повторная отметка уже прочитанного уведомления не ломает систему."""
        notif = NotificationFactory(user=user, is_read=True)

        response = auth_client.post(f"/api/v1/notifications/{notif.pk}/read/")

        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_nonexistent_notification_returns_404(self, auth_client):
        """Несуществующее уведомление — 404."""
        import uuid
        response = auth_client.post(f"/api/v1/notifications/{uuid.uuid4()}/read/")
        assert response.status_code == 404


# ============================================================
# POST /api/v1/notifications/read-all/
# ============================================================

@pytest.mark.django_db
class TestNotificationReadAllView:

    def test_marks_all_own_notifications_as_read(self, user, auth_client):
        """read-all отмечает все уведомления пользователя прочитанными."""
        NotificationFactory(user=user, is_read=False)
        NotificationFactory(user=user, is_read=False)
        NotificationFactory(user=user, is_read=False)

        response = auth_client.post("/api/v1/notifications/read-all/")

        assert response.status_code == 200

        from apps.notifications.models import Notification
        unread_count = Notification.objects.filter(user=user, is_read=False).count()
        assert unread_count == 0

    def test_does_not_affect_other_users(self, user, auth_client):
        """read-all не затрагивает уведомления других пользователей."""
        other = UserFactory()
        NotificationFactory(user=other, is_read=False)

        auth_client.post("/api/v1/notifications/read-all/")

        from apps.notifications.models import Notification
        other_notif = Notification.objects.get(user=other)
        assert other_notif.is_read is False

    def test_requires_auth(self):
        """Без авторизации — 401."""
        from rest_framework.test import APIClient
        response = APIClient().post("/api/v1/notifications/read-all/")
        assert response.status_code == 401

    def test_response_contains_count(self, user, auth_client):
        """Ответ содержит количество прочитанных уведомлений."""
        NotificationFactory(user=user, is_read=False)
        NotificationFactory(user=user, is_read=False)

        response = auth_client.post("/api/v1/notifications/read-all/")

        assert response.status_code == 200
        assert "detail" in response.data
        # Ответ: "Отмечено 2 уведомлений."
        assert "2" in response.data["detail"]

    def test_no_unread_returns_zero(self, user, auth_client):
        """Если нет непрочитанных — ответ содержит 0."""
        NotificationFactory(user=user, is_read=True)

        response = auth_client.post("/api/v1/notifications/read-all/")

        assert response.status_code == 200
        assert "0" in response.data["detail"]


# ============================================================
# Модель Notification
# ============================================================

@pytest.mark.django_db
class TestNotificationModel:

    def test_notification_str(self, user):
        """__str__ возвращает читаемое описание."""
        notif = NotificationFactory(user=user, title="Тест")
        result = str(notif)
        assert "Тест" in result

    def test_notification_types(self):
        """Все типы уведомлений из ТЗ раздела 2.8 доступны."""
        from apps.notifications.models import Notification
        types = [t.value for t in Notification.NotificationType]
        assert "task_assigned" in types
        assert "step_completed" in types
        assert "document_signed" in types
        assert "new_comment" in types
        assert "deadline_approaching" in types
        assert "document_rejected" in types

    def test_notification_is_read_default_false(self, user):
        """По умолчанию is_read=False."""
        notif = NotificationFactory(user=user)
        assert notif.is_read is False

    def test_notification_ordering_newest_first(self, user):
        """Уведомления возвращаются по убыванию created_at."""
        from apps.notifications.models import Notification
        NotificationFactory(user=user, title="Первое")
        NotificationFactory(user=user, title="Второе")

        notifs = list(Notification.objects.filter(user=user))
        # ordering = ["-created_at"] — последнее должно быть первым
        assert notifs[0].title == "Второе"


# ============================================================
# notify_new_comment сервис (раздел 2.8 ТЗ)
# ============================================================

@pytest.mark.django_db
class TestNotifyNewComment:

    def test_notify_new_comment_creates_notifications(self, workspace, user, second_user, document):
        """
        notify_new_comment создаёт уведомления для всех участников,
        кроме автора комментария.
        """
        from apps.notifications.services import notify_new_comment
        from apps.notifications.models import Notification
        from tests.factories import WorkspaceMemberFactory

        WorkspaceMemberFactory(workspace=workspace, user=second_user, role="viewer")

        # Создаём минимальный объект комментария
        from apps.documents.models import Comment
        comment = Comment.objects.create(
            document=document,
            author=user,
            content="Тестовый комментарий",
        )

        notify_new_comment(comment)

        # second_user должен получить уведомление, а user (автор) — нет
        notifs = Notification.objects.filter(user=second_user, type="new_comment")
        assert notifs.exists()

        own_notif = Notification.objects.filter(user=user, type="new_comment")
        assert not own_notif.exists()

"""
ГосДок — Тесты документов и комментариев (tests/test_documents.py)
Разделы 4.5, 4.8 ТЗ.

Сценарии:
- Список документов (только кабинеты пользователя)
- Детали документа (участник vs не-участник)
- Мягкое удаление (архивирование)
- Аудит-лог записывается при архивировании
- Комментарии: CRUD, вложенность, закрытие
- Workflow: старт, проверка статуса, уведомления
- DocumentAuditLog: проверка модели
"""

import pytest
from unittest.mock import patch

from tests.factories import (
    DocumentFactory,
    DocumentVersionFactory,
    TaskFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


def _auth_client_for(user):
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ============================================================
# GET /api/v1/documents/ — список документов
# ============================================================

@pytest.mark.django_db
class TestDocumentListView:

    def test_requires_auth(self, api_client):
        response = api_client.get("/api/v1/documents/")
        assert response.status_code == 401

    def test_returns_user_documents(self, auth_client, workspace, document):
        """Участник видит документы своего кабинета."""
        response = auth_client.get("/api/v1/documents/")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        ids = [d["id"] for d in results]
        assert str(document.pk) in ids

    def test_excludes_other_workspace_documents(self, auth_client):
        """Документы чужого кабинета не видны."""
        other_user = UserFactory()
        other_ws = WorkspaceFactory(created_by=other_user)
        WorkspaceMemberFactory(workspace=other_ws, user=other_user, role="owner")
        other_doc = DocumentFactory(workspace=other_ws, uploaded_by=other_user)

        response = auth_client.get("/api/v1/documents/")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        ids = [d["id"] for d in results]
        assert str(other_doc.pk) not in ids

    def test_filter_by_status(self, auth_client, workspace, user):
        """Фильтрация по статусу документа."""
        DocumentFactory(workspace=workspace, uploaded_by=user, status="draft")
        DocumentFactory(workspace=workspace, uploaded_by=user, status="signed")

        response = auth_client.get("/api/v1/documents/?status=draft")

        assert response.status_code == 200
        results = response.data.get("results", response.data)
        for doc in results:
            assert doc["status"] == "draft"

    def test_filter_by_workspace(self, auth_client, workspace, user):
        """Фильтрация по ID кабинета."""
        DocumentFactory(workspace=workspace, uploaded_by=user)

        response = auth_client.get(f"/api/v1/documents/?workspace={workspace.pk}")

        assert response.status_code == 200


# ============================================================
# GET /api/v1/documents/{id}/ — детали
# ============================================================

@pytest.mark.django_db
class TestDocumentDetailView:

    def test_requires_auth(self, api_client, document):
        response = api_client.get(f"/api/v1/documents/{document.pk}/")
        assert response.status_code == 401

    def test_member_can_view(self, auth_client, document):
        """Участник кабинета может просмотреть документ."""
        response = auth_client.get(f"/api/v1/documents/{document.pk}/")

        assert response.status_code == 200
        assert str(response.data["id"]) == str(document.pk)

    def test_non_member_gets_404(self, document):
        """Не-участник получает 404."""
        stranger = UserFactory()
        client = _auth_client_for(stranger)

        response = client.get(f"/api/v1/documents/{document.pk}/")

        assert response.status_code == 404

    def test_owner_can_patch_title(self, auth_client, document):
        """Редактор/владелец может изменить название документа."""
        response = auth_client.patch(
            f"/api/v1/documents/{document.pk}/",
            {"title": "Новое название"},
        )

        assert response.status_code == 200
        document.refresh_from_db()
        assert document.title == "Новое название"

    def test_viewer_cannot_patch(self, document):
        """Наблюдатель не может изменить документ."""
        viewer = UserFactory()
        ws = document.workspace
        WorkspaceMemberFactory(workspace=ws, user=viewer, role="viewer")
        client = _auth_client_for(viewer)

        response = client.patch(
            f"/api/v1/documents/{document.pk}/",
            {"title": "Взлом"},
        )

        assert response.status_code == 403

    def test_owner_can_delete_archives_document(self, auth_client, document):
        """DELETE архивирует документ (мягкое удаление), возвращает 204."""
        response = auth_client.delete(f"/api/v1/documents/{document.pk}/")

        assert response.status_code == 204
        document.refresh_from_db()
        assert document.status == "archived"

    def test_non_owner_cannot_delete(self, document):
        """Не-владелец не может удалить документ."""
        editor = UserFactory()
        WorkspaceMemberFactory(workspace=document.workspace, user=editor, role="editor")
        client = _auth_client_for(editor)

        response = client.delete(f"/api/v1/documents/{document.pk}/")

        assert response.status_code == 403


# ============================================================
# GET /api/v1/documents/{id}/versions/
# ============================================================

@pytest.mark.django_db
class TestDocumentVersionListView:

    def test_member_can_list_versions(self, auth_client, document, document_version):
        """Участник может просмотреть историю версий."""
        response = auth_client.get(f"/api/v1/documents/{document.pk}/versions/")

        assert response.status_code == 200
        assert len(response.data) >= 1

    def test_requires_auth(self, api_client, document, document_version):
        response = api_client.get(f"/api/v1/documents/{document.pk}/versions/")
        assert response.status_code == 401

    def test_non_member_gets_404(self, document, document_version):
        stranger = UserFactory()
        client = _auth_client_for(stranger)

        response = client.get(f"/api/v1/documents/{document.pk}/versions/")

        assert response.status_code == 404


# ============================================================
# POST /api/v1/documents/{id}/workflow/start/
# ============================================================

@pytest.mark.django_db
class TestDocumentWorkflowStartView:

    def test_owner_can_start_workflow(self, auth_client, workspace_with_members, user):
        """Владелец может запустить workflow для черновика."""
        doc = DocumentFactory(
            workspace=workspace_with_members,
            uploaded_by=user,
            status="draft",
        )

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            response = auth_client.post(f"/api/v1/documents/{doc.pk}/workflow/start/")

        assert response.status_code == 200
        assert response.data["status"] == "review"
        assert response.data["tasks_created"] >= 1

        doc.refresh_from_db()
        assert doc.status == "review"

    def test_workflow_requires_draft_status(self, auth_client, workspace_with_members, user):
        """Нельзя запустить workflow для нечерновика."""
        doc = DocumentFactory(
            workspace=workspace_with_members,
            uploaded_by=user,
            status="review",
        )

        response = auth_client.post(f"/api/v1/documents/{doc.pk}/workflow/start/")

        assert response.status_code == 400

    def test_workflow_requires_members_with_step_order(self, auth_client, workspace, user):
        """Без участников с step_order workflow не запускается."""
        doc = DocumentFactory(workspace=workspace, uploaded_by=user, status="draft")
        # В workspace все участники без step_order (step_order=None по умолчанию)

        response = auth_client.post(f"/api/v1/documents/{doc.pk}/workflow/start/")

        assert response.status_code == 400

    def test_non_owner_cannot_start_workflow(self, workspace_with_members, second_user):
        """Не-владелец не может запустить workflow."""
        doc = DocumentFactory(workspace=workspace_with_members, status="draft")
        client = _auth_client_for(second_user)

        response = client.post(f"/api/v1/documents/{doc.pk}/workflow/start/")

        assert response.status_code == 403

    def test_workflow_requires_auth(self, api_client, document):
        response = api_client.post(f"/api/v1/documents/{document.pk}/workflow/start/")
        assert response.status_code == 401

    def test_workflow_creates_audit_log(self, auth_client, workspace_with_members, user):
        """После запуска workflow создаётся запись аудит-лога."""
        doc = DocumentFactory(
            workspace=workspace_with_members,
            uploaded_by=user,
            status="draft",
        )

        with patch("apps.tasks.workflow._send_task_assigned_email"):
            auth_client.post(f"/api/v1/documents/{doc.pk}/workflow/start/")

        from apps.documents.models import DocumentAuditLog
        log = DocumentAuditLog.objects.filter(
            document=doc,
            action=DocumentAuditLog.Action.WORKFLOW_STARTED,
        ).first()
        assert log is not None


# ============================================================
# GET/POST /api/v1/documents/{id}/comments/
# ============================================================

@pytest.mark.django_db
class TestCommentListCreateView:

    def test_requires_auth(self, api_client, document):
        response = api_client.get(f"/api/v1/documents/{document.pk}/comments/")
        assert response.status_code == 401

    def test_member_can_list_comments(self, auth_client, document):
        """Участник видит список комментариев."""
        response = auth_client.get(f"/api/v1/documents/{document.pk}/comments/")
        assert response.status_code == 200
        assert isinstance(response.data, list)

    def test_member_can_add_comment(self, auth_client, document):
        """Участник может добавить комментарий."""
        response = auth_client.post(
            f"/api/v1/documents/{document.pk}/comments/",
            {"content": "Требует исправлений в разделе 3."},
        )
        assert response.status_code == 201
        assert response.data["content"] == "Требует исправлений в разделе 3."

    def test_non_member_cannot_comment(self, document):
        """Не-участник получает 404 при попытке добавить комментарий."""
        stranger = UserFactory()
        client = _auth_client_for(stranger)

        response = client.post(
            f"/api/v1/documents/{document.pk}/comments/",
            {"content": "Попытка взлома"},
        )

        assert response.status_code == 404

    def test_reply_to_comment(self, auth_client, document):
        """Ответ на комментарий через parent."""
        from apps.documents.models import Comment

        parent_comment = Comment.objects.create(
            document=document,
            author=document.uploaded_by,
            content="Родительский комментарий",
        )

        response = auth_client.post(
            f"/api/v1/documents/{document.pk}/comments/",
            {
                "content": "Ответ на комментарий",
                "parent": str(parent_comment.pk),
            },
        )

        assert response.status_code == 201

    def test_comment_requires_content(self, auth_client, document):
        """Пустой content не допускается."""
        response = auth_client.post(
            f"/api/v1/documents/{document.pk}/comments/",
            {"content": ""},
        )
        assert response.status_code == 400

    def test_comment_notification_sent_to_workspace_members(
        self, auth_client, workspace, user, second_user, document
    ):
        """
        После добавления комментария уведомление отправляется другим участникам.
        Раздел 2.8 ТЗ.
        """
        WorkspaceMemberFactory(workspace=workspace, user=second_user, role="viewer")

        auth_client.post(
            f"/api/v1/documents/{document.pk}/comments/",
            {"content": "Проверка уведомлений"},
        )

        from apps.notifications.models import Notification
        notif = Notification.objects.filter(
            user=second_user, type="new_comment"
        ).first()
        assert notif is not None


# ============================================================
# PATCH/DELETE /api/v1/comments/{id}/
# ============================================================

@pytest.mark.django_db
class TestCommentDetailView:

    def _create_comment(self, document, author):
        from apps.documents.models import Comment
        return Comment.objects.create(
            document=document,
            author=author,
            content="Исходный текст",
        )

    def test_author_can_update_comment(self, auth_client, document, user):
        """Автор может отредактировать свой комментарий."""
        comment = self._create_comment(document, user)

        response = auth_client.patch(
            f"/api/v1/comments/{comment.pk}/",
            {"content": "Обновлённый текст"},
        )

        assert response.status_code == 200
        comment.refresh_from_db()
        assert comment.content == "Обновлённый текст"

    def test_non_author_cannot_update(self, document):
        """Не-автор не может редактировать комментарий."""
        author = UserFactory()
        WorkspaceMemberFactory(workspace=document.workspace, user=author, role="viewer")
        comment = self._create_comment(document, author)

        other = UserFactory()
        WorkspaceMemberFactory(workspace=document.workspace, user=other, role="viewer")
        client = _auth_client_for(other)

        response = client.patch(
            f"/api/v1/comments/{comment.pk}/",
            {"content": "Взлом"},
        )

        assert response.status_code == 403

    def test_author_can_delete_comment(self, auth_client, document, user):
        """Автор может удалить свой комментарий."""
        comment = self._create_comment(document, user)

        response = auth_client.delete(f"/api/v1/comments/{comment.pk}/")

        assert response.status_code == 204

    def test_workspace_owner_can_delete_any_comment(self, workspace, user, document):
        """Владелец кабинета может удалить любой комментарий."""
        author = UserFactory()
        WorkspaceMemberFactory(workspace=workspace, user=author, role="viewer")
        comment = self._create_comment(document, author)

        # user = owner
        owner_client = _auth_client_for(user)
        response = owner_client.delete(f"/api/v1/comments/{comment.pk}/")

        assert response.status_code == 204


# ============================================================
# POST /api/v1/comments/{id}/resolve/
# ============================================================

@pytest.mark.django_db
class TestCommentResolveView:

    def _create_comment(self, document, author):
        from apps.documents.models import Comment
        return Comment.objects.create(
            document=document,
            author=author,
            content="Открытый комментарий",
        )

    def test_owner_can_resolve_comment(self, auth_client, workspace, user, document):
        """Владелец кабинета может закрыть комментарий."""
        other = UserFactory()
        WorkspaceMemberFactory(workspace=workspace, user=other, role="viewer")
        comment = self._create_comment(document, other)

        response = auth_client.post(f"/api/v1/comments/{comment.pk}/resolve/")

        assert response.status_code == 200
        comment.refresh_from_db()
        assert comment.is_resolved is True

    def test_non_owner_cannot_resolve(self, workspace, document):
        """Не-владелец не может закрыть комментарий."""
        viewer = UserFactory()
        WorkspaceMemberFactory(workspace=workspace, user=viewer, role="viewer")
        author = UserFactory()
        WorkspaceMemberFactory(workspace=workspace, user=author, role="editor")
        comment = self._create_comment(document, author)

        viewer_client = _auth_client_for(viewer)
        response = viewer_client.post(f"/api/v1/comments/{comment.pk}/resolve/")

        assert response.status_code == 403

    def test_resolve_requires_auth(self, api_client, document, user):
        comment = self._create_comment(document, user)
        response = api_client.post(f"/api/v1/comments/{comment.pk}/resolve/")
        assert response.status_code == 401


# ============================================================
# DocumentAuditLog модель
# ============================================================

@pytest.mark.django_db
class TestDocumentAuditLog:

    def test_audit_log_created_on_archive(self, auth_client, document):
        """При архивировании документа создаётся запись аудит-лога."""
        auth_client.delete(f"/api/v1/documents/{document.pk}/")

        from apps.documents.models import DocumentAuditLog
        log = DocumentAuditLog.objects.filter(
            document=document,
            action=DocumentAuditLog.Action.ARCHIVED,
        ).first()
        assert log is not None

    def test_log_document_action_utility(self, document, user):
        """log_document_action создаёт запись без исключений."""
        from apps.documents.audit_log import log_document_action
        from apps.documents.models import DocumentAuditLog

        result = log_document_action(
            document=document,
            user=user,
            action=DocumentAuditLog.Action.SIGNED,
            details={"test": True},
            ip_address="127.0.0.1",
        )

        assert result is not None
        assert result.action == "signed"
        assert result.ip_address == "127.0.0.1"
        assert result.details == {"test": True}

    def test_log_document_action_str(self, document, user):
        """__str__ возвращает читаемую строку."""
        from apps.documents.audit_log import log_document_action
        from apps.documents.models import DocumentAuditLog

        log = log_document_action(
            document=document,
            user=user,
            action=DocumentAuditLog.Action.CREATED,
        )
        assert log is not None
        result = str(log)
        assert "Создан" in result

    def test_audit_log_action_choices(self):
        """Все требуемые типы действий доступны."""
        from apps.documents.models import DocumentAuditLog
        actions = [a.value for a in DocumentAuditLog.Action]
        assert "created" in actions
        assert "archived" in actions
        assert "workflow_started" in actions
        assert "signed" in actions
        assert "version_uploaded" in actions

    def test_audit_log_user_nullable(self, document):
        """user может быть None (например, системное действие)."""
        from apps.documents.models import DocumentAuditLog

        log = DocumentAuditLog.objects.create(
            document=document,
            user=None,
            action=DocumentAuditLog.Action.CREATED,
        )
        assert log.user is None
        assert log.pk is not None


# ============================================================
# Версии документов — модель и логика
# ============================================================

@pytest.mark.django_db
class TestDocumentVersionModel:

    def test_checksum_stored(self, document, user):
        """Checksum SHA-256 сохраняется в версии."""
        ver = DocumentVersionFactory(
            document=document,
            created_by=user,
            version_number=1,
            checksum="a" * 64,
        )
        assert ver.checksum == "a" * 64

    def test_ai_diff_summary_nullable(self, document, user):
        """ai_diff_summary может быть NULL (первая версия)."""
        ver = DocumentVersionFactory(
            document=document,
            created_by=user,
            version_number=1,
        )
        assert ver.ai_diff_summary is None
        assert ver.ai_changes_detected is False

    def test_ai_changes_detected_true(self, document, user):
        """ai_changes_detected=True для версии с изменениями."""
        ver = DocumentVersionFactory(
            document=document,
            created_by=user,
            version_number=2,
            ai_changes_detected=True,
            ai_diff_summary={"summary": "Изменены пункты 1 и 3."},
        )
        assert ver.ai_changes_detected is True
        assert "summary" in ver.ai_diff_summary

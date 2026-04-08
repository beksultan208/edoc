"""
ГосДок — Тесты моделей (tests/test_models.py)
Раздел 9 ТЗ: models, serializers, views.
"""

import pytest
from django.utils import timezone

from tests.factories import (
    DocumentFactory,
    DocumentVersionFactory,
    EmailVerificationCodeFactory,
    OrganizationFactory,
    TaskFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


# ============================================================
# User model
# ============================================================

@pytest.mark.django_db
class TestUserModel:

    def test_create_user(self):
        user = UserFactory(email="test@gosdoc.test", full_name="Тест Тестов")
        assert user.pk is not None
        assert user.email == "test@gosdoc.test"
        assert user.full_name == "Тест Тестов"
        assert user.is_active is True
        assert user.is_staff is False

    def test_user_password_is_hashed(self):
        user = UserFactory()
        # Пароль не хранится в открытом виде
        assert user.password != "TestPass123!"
        assert user.check_password("TestPass123!") is True

    def test_user_str(self):
        user = UserFactory(full_name="Иван Иванов", email="ivan@test.test")
        assert "Иван Иванов" in str(user)
        assert "ivan@test.test" in str(user)

    def test_user_email_is_unique(self):
        UserFactory(email="unique@gosdoc.test")
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            # factory_boy использует get_or_create, поэтому создаём напрямую
            from django.contrib.auth import get_user_model
            User = get_user_model()
            User.objects.create_user(
                email="unique@gosdoc.test",
                full_name="Дубликат",
                password="pass",
            )

    def test_create_superuser(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin = User.objects.create_superuser(
            email="admin@gosdoc.test",
            full_name="Администратор",
            password="AdminPass123!",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_password_hash_property(self):
        user = UserFactory()
        assert user.password_hash == user.password


# ============================================================
# EmailVerificationCode model
# ============================================================

@pytest.mark.django_db
class TestEmailVerificationCode:

    def test_generate_creates_code(self):
        from apps.users.models import EmailVerificationCode
        vc = EmailVerificationCode.generate("test@gosdoc.test", "registration")
        assert vc.pk is not None
        assert len(vc.code) == 6
        assert vc.code.isdigit()
        assert vc.is_used is False
        assert vc.expires_at > timezone.now()

    def test_generate_invalidates_previous(self):
        from apps.users.models import EmailVerificationCode
        vc1 = EmailVerificationCode.generate("test2@gosdoc.test", "registration")
        vc2 = EmailVerificationCode.generate("test2@gosdoc.test", "registration")

        vc1.refresh_from_db()
        assert vc1.is_used is True   # старый инвалидирован
        assert vc2.is_used is False  # новый активен

    def test_is_valid_correct_code(self):
        vc = EmailVerificationCodeFactory(code="654321")
        assert vc.is_valid("654321") is True

    def test_is_valid_wrong_code(self):
        vc = EmailVerificationCodeFactory(code="654321")
        assert vc.is_valid("000000") is False

    def test_is_valid_expired(self):
        vc = EmailVerificationCodeFactory(
            expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )
        assert vc.is_valid(vc.code) is False

    def test_is_valid_used(self):
        vc = EmailVerificationCodeFactory(is_used=True)
        assert vc.is_valid(vc.code) is False


# ============================================================
# Workspace & WorkspaceMember models
# ============================================================

@pytest.mark.django_db
class TestWorkspaceModel:

    def test_create_workspace(self):
        user = UserFactory()
        ws = WorkspaceFactory(created_by=user, type="individual")
        assert ws.pk is not None
        assert ws.status == "active"
        assert ws.created_by == user

    def test_workspace_str(self):
        ws = WorkspaceFactory(title="Тест кабинет", type="individual")
        assert "Тест кабинет" in str(ws)

    def test_workspace_member_roles(self):
        from apps.workspaces.models import WorkspaceMember
        roles = [r.value for r in WorkspaceMember.Role]
        assert "owner" in roles
        assert "editor" in roles
        assert "signer" in roles
        assert "viewer" in roles

    def test_workspace_member_unique_constraint(self):
        ws = WorkspaceFactory()
        user = UserFactory()
        WorkspaceMemberFactory(workspace=ws, user=user, role="owner")
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            WorkspaceMemberFactory(workspace=ws, user=user, role="editor")

    def test_workspace_member_str(self):
        member = WorkspaceMemberFactory(role="signer")
        assert "signer" in str(member).lower() or "Подписант" in str(member)


# ============================================================
# Document model
# ============================================================

@pytest.mark.django_db
class TestDocumentModel:

    def test_create_document(self):
        doc = DocumentFactory(title="Приказ №1", file_type="pdf")
        assert doc.pk is not None
        assert doc.status == "draft"
        assert doc.title == "Приказ №1"
        assert doc.file_type == "pdf"

    def test_document_status_choices(self):
        from apps.documents.models import Document
        statuses = [s.value for s in Document.DocumentStatus]
        assert "draft" in statuses
        assert "review" in statuses
        assert "signed" in statuses
        assert "archived" in statuses

    def test_document_str(self):
        doc = DocumentFactory(title="Контракт", status="draft")
        assert "Контракт" in str(doc)

    def test_document_version_unique_per_doc(self):
        doc = DocumentFactory()
        DocumentVersionFactory(document=doc, version_number=1)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            DocumentVersionFactory(document=doc, version_number=1)

    def test_document_version_str(self):
        doc = DocumentFactory(title="Акт")
        ver = DocumentVersionFactory(document=doc, version_number=2)
        result = str(ver)
        assert "Акт" in result
        assert "2" in result


# ============================================================
# Task model
# ============================================================

@pytest.mark.django_db
class TestTaskModel:

    def test_create_task(self):
        task = TaskFactory(step_order=1, status="pending")
        assert task.pk is not None
        assert task.status == "pending"
        assert task.step_order == 1

    def test_task_status_choices(self):
        from apps.tasks.models import Task
        statuses = [s.value for s in Task.TaskStatus]
        assert "pending" in statuses
        assert "in_progress" in statuses
        assert "done" in statuses
        assert "skipped" in statuses

    def test_task_str(self):
        task = TaskFactory(title="Согласование", step_order=2, status="pending")
        result = str(task)
        assert "Согласование" in result
        assert "2" in result

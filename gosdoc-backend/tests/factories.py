"""
ГосДок — factory_boy фабрики для тестов.
Раздел 9 ТЗ: pytest + factory_boy для фикстур.
"""

import uuid

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory


# ============================================================
# User
# ============================================================

class UserFactory(DjangoModelFactory):
    """Создаёт активного пользователя."""

    class Meta:
        model = "users.User"
        django_get_or_create = ("email",)

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user{n}@gosdoc.test")
    full_name = factory.Sequence(lambda n: f"Пользователь {n}")
    phone = factory.Sequence(lambda n: f"+7700{n:07d}")
    is_active = True
    is_staff = False
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")


class AdminUserFactory(UserFactory):
    """Администратор."""
    is_staff = True
    is_superuser = True


# ============================================================
# Organization
# ============================================================

class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = "organizations.Organization"

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Организация {n}")
    type = "individual"
    owner = factory.SubFactory(UserFactory)


# ============================================================
# Workspace
# ============================================================

class WorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = "workspaces.Workspace"

    id = factory.LazyFunction(uuid.uuid4)
    title = factory.Sequence(lambda n: f"Кабинет {n}")
    type = "individual"
    created_by = factory.SubFactory(UserFactory)
    status = "active"
    description = "Тестовый кабинет"


class WorkspaceMemberFactory(DjangoModelFactory):
    class Meta:
        model = "workspaces.WorkspaceMember"

    id = factory.LazyFunction(uuid.uuid4)
    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role = "owner"
    step_order = None


# ============================================================
# Document & Version
# ============================================================

class DocumentFactory(DjangoModelFactory):
    class Meta:
        model = "documents.Document"

    id = factory.LazyFunction(uuid.uuid4)
    workspace = factory.SubFactory(WorkspaceFactory)
    title = factory.Sequence(lambda n: f"Документ {n}")
    file_type = "pdf"
    storage_key = factory.Sequence(lambda n: f"docs/test_{n}.pdf")
    storage_url = factory.Sequence(lambda n: f"https://s3.example.com/docs/test_{n}.pdf")
    status = "draft"
    uploaded_by = factory.SubFactory(UserFactory)


class DocumentVersionFactory(DjangoModelFactory):
    class Meta:
        model = "documents.DocumentVersion"

    id = factory.LazyFunction(uuid.uuid4)
    document = factory.SubFactory(DocumentFactory)
    version_number = 1
    storage_key = factory.Sequence(lambda n: f"docs/ver_{n}.pdf")
    checksum = factory.Sequence(lambda n: f"{'a' * 60}{n:04d}")
    ai_changes_detected = False
    created_by = factory.SubFactory(UserFactory)


# ============================================================
# Task
# ============================================================

class TaskFactory(DjangoModelFactory):
    class Meta:
        model = "tasks.Task"

    id = factory.LazyFunction(uuid.uuid4)
    workspace = factory.SubFactory(WorkspaceFactory)
    document = factory.SubFactory(DocumentFactory)
    assigned_to = factory.SubFactory(UserFactory)
    step_order = 1
    title = factory.Sequence(lambda n: f"Задача {n}")
    status = "pending"


# ============================================================
# Signature
# ============================================================

class SignatureFactory(DjangoModelFactory):
    class Meta:
        model = "signatures.Signature"

    id = factory.LazyFunction(uuid.uuid4)
    document = factory.SubFactory(DocumentFactory)
    user = factory.SubFactory(UserFactory)
    signature_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    ip_address = "127.0.0.1"
    is_valid = True


# ============================================================
# Notification
# ============================================================

class NotificationFactory(DjangoModelFactory):
    class Meta:
        model = "notifications.Notification"

    id = factory.LazyFunction(uuid.uuid4)
    user = factory.SubFactory(UserFactory)
    type = "task_assigned"
    title = factory.Sequence(lambda n: f"Уведомление {n}")
    message = "Тестовое уведомление"
    is_read = False


# ============================================================
# MonthlyReport
# ============================================================

class MonthlyReportFactory(DjangoModelFactory):
    class Meta:
        model = "reports.MonthlyReport"

    id = factory.LazyFunction(uuid.uuid4)
    workspace = factory.SubFactory(WorkspaceFactory)
    period_year = 2025
    period_month = 1
    docs_total = 10
    docs_completed = 7
    docs_signed = 5
    tasks_completed = 8
    avg_completion_days = 3.50
    report_data = {"period": "2025-01", "workspace_id": "test"}


# ============================================================
# DocumentAuditLog
# ============================================================

class DocumentAuditLogFactory(DjangoModelFactory):
    class Meta:
        model = "documents.DocumentAuditLog"

    id = factory.LazyFunction(uuid.uuid4)
    document = factory.SubFactory(DocumentFactory)
    user = factory.SubFactory(UserFactory)
    action = "created"
    details = factory.LazyFunction(dict)
    ip_address = "127.0.0.1"


# ============================================================
# EmailVerificationCode
# ============================================================

class EmailVerificationCodeFactory(DjangoModelFactory):
    class Meta:
        model = "users.EmailVerificationCode"

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user{n}@gosdoc.test")
    code = "123456"
    purpose = "registration"
    is_used = False
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + timezone.timedelta(minutes=15)
    )

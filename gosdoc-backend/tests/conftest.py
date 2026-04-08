"""
ГосДок — pytest фикстуры (tests/conftest.py)
Раздел 9 ТЗ: pytest + pytest-django.
"""

import pytest
from django.test import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    DocumentFactory,
    DocumentVersionFactory,
    MonthlyReportFactory,
    OrganizationFactory,
    TaskFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


# ============================================================
# Пользователи
# ============================================================

@pytest.fixture
def user(db):
    """Обычный активный пользователь."""
    return UserFactory()


@pytest.fixture
def second_user(db):
    """Второй пользователь для тестов multi-user."""
    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Администратор."""
    from tests.factories import AdminUserFactory
    return AdminUserFactory()


# ============================================================
# API клиент с авторизацией
# ============================================================

@pytest.fixture
def api_client():
    """Неавторизованный DRF APIClient."""
    return APIClient()


@pytest.fixture
def auth_client(user):
    """APIClient, авторизованный как user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def auth_client_second(second_user):
    """APIClient, авторизованный как second_user."""
    client = APIClient()
    refresh = RefreshToken.for_user(second_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ============================================================
# Кабинеты
# ============================================================

@pytest.fixture
def workspace(db, user):
    """Кабинет, созданный user."""
    ws = WorkspaceFactory(created_by=user)
    # Добавляем creator как owner
    WorkspaceMemberFactory(workspace=ws, user=user, role="owner")
    return ws


@pytest.fixture
def workspace_with_members(workspace, second_user):
    """
    Кабинет с двумя участниками:
    - user → owner, step_order=1
    - second_user → signer, step_order=2
    """
    # Обновляем существующую запись owner → step_order=1
    workspace.members.filter(user=workspace.created_by).update(step_order=1)
    WorkspaceMemberFactory(
        workspace=workspace, user=second_user, role="signer", step_order=2
    )
    return workspace


# ============================================================
# Документы
# ============================================================

@pytest.fixture
def document(db, workspace, user):
    """Черновик документа в workspace."""
    return DocumentFactory(workspace=workspace, uploaded_by=user, status="draft")


@pytest.fixture
def document_version(db, document, user):
    """Версия документа."""
    return DocumentVersionFactory(document=document, created_by=user, version_number=1)


# ============================================================
# Задачи
# ============================================================

@pytest.fixture
def task(db, workspace, document, user):
    """Задача in_progress для user."""
    return TaskFactory(
        workspace=workspace,
        document=document,
        assigned_to=user,
        step_order=1,
        status="in_progress",
    )


# ============================================================
# Отчёты
# ============================================================

@pytest.fixture
def monthly_report(db, workspace):
    """Готовый отчёт за Январь 2025."""
    return MonthlyReportFactory(workspace=workspace, period_year=2025, period_month=1)

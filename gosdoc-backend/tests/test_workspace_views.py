"""
ГосДок — Тесты кабинетов (tests/test_workspace_views.py)
Раздел 9 ТЗ: workspace CRUD, members management.
"""

import pytest

from tests.factories import (
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


@pytest.mark.django_db
class TestWorkspaceListCreate:

    def test_list_requires_auth(self, api_client):
        response = api_client.get("/api/v1/workspaces/")
        assert response.status_code == 401

    def test_list_returns_user_workspaces(self, auth_client, workspace):
        response = auth_client.get("/api/v1/workspaces/")
        assert response.status_code == 200
        ids = [w["id"] for w in response.data.get("results", response.data)]
        assert str(workspace.pk) in ids

    def test_list_excludes_other_workspaces(self, auth_client):
        other = WorkspaceFactory()
        response = auth_client.get("/api/v1/workspaces/")
        assert response.status_code == 200
        ids = [w["id"] for w in response.data.get("results", response.data)]
        assert str(other.pk) not in ids

    def test_create_workspace(self, auth_client):
        response = auth_client.post("/api/v1/workspaces/", {
            "title": "Новый кабинет",
            "type": "individual",
        })
        assert response.status_code in (201, 200)

    def test_create_requires_auth(self, api_client):
        response = api_client.post("/api/v1/workspaces/", {
            "title": "Тест",
            "type": "individual",
        })
        assert response.status_code == 401

    def test_list_filter_by_status(self, auth_client, workspace):
        response = auth_client.get("/api/v1/workspaces/?status=active")
        assert response.status_code == 200

    def test_list_filter_by_type(self, auth_client, workspace):
        response = auth_client.get("/api/v1/workspaces/?type=individual")
        assert response.status_code == 200


@pytest.mark.django_db
class TestWorkspaceDetail:

    def test_detail_requires_auth(self, api_client, workspace):
        response = api_client.get(f"/api/v1/workspaces/{workspace.pk}/")
        assert response.status_code == 401

    def test_detail_returns_workspace(self, auth_client, workspace):
        response = auth_client.get(f"/api/v1/workspaces/{workspace.pk}/")
        assert response.status_code == 200
        assert str(response.data["id"]) == str(workspace.pk)

    def test_detail_foreign_workspace_returns_404(self, auth_client):
        other = WorkspaceFactory()
        response = auth_client.get(f"/api/v1/workspaces/{other.pk}/")
        assert response.status_code == 404

    def test_owner_can_patch(self, auth_client, workspace):
        response = auth_client.patch(f"/api/v1/workspaces/{workspace.pk}/", {
            "title": "Обновлённый кабинет",
        })
        assert response.status_code == 200
        assert response.data["title"] == "Обновлённый кабинет"

    def test_non_owner_cannot_patch(self, auth_client_second, workspace):
        # second_user is not a member of workspace
        response = auth_client_second.patch(f"/api/v1/workspaces/{workspace.pk}/", {
            "title": "Взлом",
        })
        assert response.status_code in (403, 404)

    def test_owner_can_delete(self, auth_client, workspace):
        """DELETE → soft close (status=closed), returns 204."""
        response = auth_client.delete(f"/api/v1/workspaces/{workspace.pk}/")
        assert response.status_code == 204
        workspace.refresh_from_db()
        assert workspace.status == "closed"

    def test_non_owner_cannot_delete(self, auth_client_second, workspace):
        response = auth_client_second.delete(f"/api/v1/workspaces/{workspace.pk}/")
        assert response.status_code in (403, 404)


@pytest.mark.django_db
class TestWorkspaceMemberList:

    def test_list_requires_auth(self, api_client, workspace):
        response = api_client.get(f"/api/v1/workspaces/{workspace.pk}/members/")
        assert response.status_code == 401

    def test_member_can_list(self, auth_client, workspace):
        response = auth_client.get(f"/api/v1/workspaces/{workspace.pk}/members/")
        assert response.status_code == 200
        assert isinstance(response.data, list)

    def test_non_member_cannot_list(self, auth_client_second, workspace):
        response = auth_client_second.get(f"/api/v1/workspaces/{workspace.pk}/members/")
        assert response.status_code == 403

    def test_owner_can_add_member(self, auth_client, workspace):
        new_user = UserFactory()
        response = auth_client.post(f"/api/v1/workspaces/{workspace.pk}/members/", {
            "user_id": str(new_user.pk),
            "role": "viewer",
        })
        assert response.status_code == 201

    def test_non_owner_cannot_add_member(self, auth_client_second, workspace):
        new_user = UserFactory()
        response = auth_client_second.post(f"/api/v1/workspaces/{workspace.pk}/members/", {
            "user_id": str(new_user.pk),
            "role": "viewer",
        })
        assert response.status_code in (403, 404)

    def test_add_member_missing_user_returns_error(self, auth_client, workspace):
        import uuid
        response = auth_client.post(f"/api/v1/workspaces/{workspace.pk}/members/", {
            "user_id": str(uuid.uuid4()),
            "role": "viewer",
        })
        # View возвращает 400 (пользователь не найден) или 404
        assert response.status_code in (400, 404)

    def test_add_existing_member_updates_role(self, auth_client, workspace, second_user):
        WorkspaceMemberFactory(workspace=workspace, user=second_user, role="viewer")
        response = auth_client.post(f"/api/v1/workspaces/{workspace.pk}/members/", {
            "user_id": str(second_user.pk),
            "role": "signer",
        })
        assert response.status_code == 201
        assert response.data["role"] == "signer"


@pytest.mark.django_db
class TestWorkspaceMemberDetail:

    def test_owner_can_patch_member(self, auth_client, workspace, second_user):
        member = WorkspaceMemberFactory(workspace=workspace, user=second_user, role="viewer")
        response = auth_client.patch(
            f"/api/v1/workspaces/{workspace.pk}/members/{second_user.pk}/",
            {"role": "signer"},
        )
        assert response.status_code == 200
        assert response.data["role"] == "signer"

    def test_non_owner_cannot_patch_member(self, auth_client_second, workspace, user):
        response = auth_client_second.patch(
            f"/api/v1/workspaces/{workspace.pk}/members/{user.pk}/",
            {"role": "viewer"},
        )
        assert response.status_code in (403, 404)

    def test_owner_can_delete_member(self, auth_client, workspace, second_user):
        WorkspaceMemberFactory(workspace=workspace, user=second_user, role="viewer")
        response = auth_client.delete(
            f"/api/v1/workspaces/{workspace.pk}/members/{second_user.pk}/"
        )
        assert response.status_code == 204

    def test_cannot_delete_last_owner(self, auth_client, workspace, user):
        response = auth_client.delete(
            f"/api/v1/workspaces/{workspace.pk}/members/{user.pk}/"
        )
        assert response.status_code == 400

    def test_cannot_delete_self(self, auth_client, workspace, user):
        response = auth_client.delete(
            f"/api/v1/workspaces/{workspace.pk}/members/{user.pk}/"
        )
        assert response.status_code == 400

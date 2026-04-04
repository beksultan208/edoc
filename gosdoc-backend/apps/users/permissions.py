"""
ГосДок — Кастомные пермишены (apps/users/permissions.py)
"""

from rest_framework.permissions import BasePermission, IsAdminUser  # noqa: F401


class IsSelfOrAdmin(BasePermission):
    """
    Разрешает доступ только самому пользователю или администратору.
    Используется для PATCH/DELETE /api/v1/users/{id}/
    """

    def has_object_permission(self, request, view, obj):
        return obj == request.user or request.user.is_staff


class IsOrganizationOwner(BasePermission):
    """
    Разрешает доступ только владельцу организации.
    Объект должен иметь поле `owner`.
    """

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.is_staff


class IsWorkspaceMember(BasePermission):
    """
    Разрешает доступ участникам кабинета.
    Используется вместе с get_queryset, который фильтрует по membership.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # obj — это Workspace или его дочерний объект
        workspace = getattr(obj, "workspace", obj)
        return workspace.members.filter(user=request.user).exists()


class IsWorkspaceOwner(BasePermission):
    """Доступ только для роли owner в кабинете."""

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, "workspace", obj)
        return workspace.members.filter(
            user=request.user, role="owner"
        ).exists() or request.user.is_staff


class IsWorkspaceEditor(BasePermission):
    """Доступ для ролей owner и editor в кабинете."""

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, "workspace", obj)
        return workspace.members.filter(
            user=request.user, role__in=["owner", "editor"]
        ).exists() or request.user.is_staff


class IsWorkspaceSigner(BasePermission):
    """Доступ для роли signer (и выше) в кабинете."""

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, "workspace", obj)
        return workspace.members.filter(
            user=request.user, role__in=["owner", "editor", "signer"]
        ).exists() or request.user.is_staff

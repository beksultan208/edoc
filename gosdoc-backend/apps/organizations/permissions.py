"""
ГосДок — Пермишены для организаций
"""

from rest_framework.permissions import BasePermission


class IsOrganizationMember(BasePermission):
    """Доступ только членам организации."""

    def has_object_permission(self, request, view, obj):
        return (
            obj.owner == request.user
            or obj.users.filter(id=request.user.id).exists()
            or request.user.is_staff
        )


class IsOrganizationOwner(BasePermission):
    """Доступ только владельцу организации."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.is_staff

"""
ГосДок — Views организаций (apps/organizations/views.py)
Раздел 4.3 ТЗ
"""

import logging

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import UserListSerializer
from .models import Organization
from .permissions import IsOrganizationMember, IsOrganizationOwner
from .serializers import InviteMemberSerializer, OrganizationListSerializer, OrganizationSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class OrganizationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/organizations/ — список организаций пользователя
    POST /api/v1/organizations/ — создать организацию
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrganizationSerializer
        return OrganizationListSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Organization.objects.all().order_by("-created_at")
        # Показываем организации, в которых пользователь состоит или является владельцем
        return (
            Organization.objects.filter(users__id=user.id)
            | Organization.objects.filter(owner=user)
        ).distinct().order_by("-created_at")


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/organizations/{id}/ — JWT + Member
    PATCH /api/v1/organizations/{id}/ — JWT + Owner
    """
    queryset = Organization.objects.prefetch_related("users")

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [permissions.IsAuthenticated(), IsOrganizationOwner()]
        return [permissions.IsAuthenticated(), IsOrganizationMember()]

    def get_serializer_class(self):
        return OrganizationSerializer


class OrganizationMembersView(generics.ListAPIView):
    """
    GET /api/v1/organizations/{id}/members/
    JWT + Member — список активных пользователей организации.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserListSerializer

    def get_queryset(self):
        org = get_object_or_404(Organization, pk=self.kwargs["pk"])

        # Проверяем доступ
        is_member = (
            org.owner == self.request.user
            or org.users.filter(id=self.request.user.id).exists()
            or self.request.user.is_staff
        )
        if not is_member:
            raise PermissionDenied("Вы не являетесь членом этой организации.")

        return User.objects.filter(organization_id=self.kwargs["pk"], is_active=True).order_by("full_name")


class OrganizationInviteView(APIView):
    """
    POST /api/v1/organizations/{id}/invite/
    JWT + Owner — добавить пользователя в организацию по email.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        org = get_object_or_404(Organization, pk=pk)

        # Только владелец может приглашать
        if org.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("Только владелец организации может приглашать участников.")

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        user = get_object_or_404(User, email=email, is_active=True)

        if user.organization_id == org.id:
            return Response(
                {"detail": f"Пользователь {email} уже состоит в этой организации."},
                status=status.HTTP_409_CONFLICT,
            )

        user.organization = org
        user.save(update_fields=["organization"])

        # Создаём уведомление
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=user,
            type=Notification.NotificationType.TASK_ASSIGNED,
            title=f"Вы добавлены в организацию «{org.name}»",
            message=f"Владелец: {org.owner.full_name}.",
            entity_type="organization",
            entity_id=org.id,
        )

        logger.info("Пользователь %s добавлен в организацию '%s' (by %s)", email, org.name, request.user.email)

        return Response(
            {"detail": f"Пользователь {email} добавлен в организацию."},
            status=status.HTTP_200_OK,
        )

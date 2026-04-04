"""
ГосДок — Сериализаторы кабинетов (apps/workspaces/serializers.py)
Раздел 4.4 ТЗ
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Workspace, WorkspaceMember

User = get_user_model()


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """Полный сериализатор участника кабинета."""
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = [
            "id", "workspace", "user", "user_email", "user_name",
            "role", "step_order", "joined_at",
        ]
        read_only_fields = ["id", "workspace", "joined_at"]


class WorkspaceMemberUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для PATCH участника — можно менять только роль и step_order."""

    class Meta:
        model = WorkspaceMember
        fields = ["role", "step_order"]


class AddMemberSerializer(serializers.Serializer):
    """
    Добавление участника в кабинет.
    POST /api/v1/workspaces/{id}/members/
    """
    user_id = serializers.UUIDField(
        required=True,
        help_text="UUID пользователя для добавления в кабинет",
    )
    role = serializers.ChoiceField(
        choices=WorkspaceMember.Role.choices,
        required=True,
        help_text="Роль: owner | editor | signer | viewer",
    )
    step_order = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        help_text="Порядок шага в workflow (опционально)",
    )

    def validate_user_id(self, value):
        if not User.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Пользователь не найден или неактивен.")
        return value


class WorkspaceSerializer(serializers.ModelSerializer):
    """Полный сериализатор кабинета."""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id", "title", "type", "organization", "organization_name",
            "created_by", "created_by_name",
            "status", "description", "deadline",
            "created_at", "members_count",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def get_members_count(self, obj) -> int:
        return obj.members.count()

    def create(self, validated_data):
        user = self.context["request"].user
        # Если organization не передана — берём из профиля пользователя
        if "organization" not in validated_data and user.organization:
            validated_data["organization"] = user.organization
        workspace = Workspace.objects.create(created_by=user, **validated_data)
        # Создатель автоматически получает роль owner
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=WorkspaceMember.Role.OWNER,
            step_order=None,  # owner не участвует в workflow-шагах по умолчанию
        )
        return workspace

    def validate(self, attrs):
        request = self.context.get("request")
        workspace_type = attrs.get("type") or (self.instance.type if self.instance else None)
        organization = attrs.get("organization") or (self.instance.organization if self.instance else None)

        # Проверяем лимит для индивидуального кабинета (раздел 2.1 ТЗ)
        if workspace_type == Workspace.WorkspaceType.INDIVIDUAL and organization and request:
            existing_count = Workspace.objects.filter(
                organization=organization,
                type=Workspace.WorkspaceType.INDIVIDUAL,
                status=Workspace.WorkspaceStatus.ACTIVE,
            ).count()
            # При создании проверяем лимит 20 документов не здесь,
            # а на уровне загрузки документов (workspace level)
        return attrs


class WorkspaceListSerializer(serializers.ModelSerializer):
    """Краткий вид кабинета для списков."""
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id", "title", "type", "organization_name",
            "status", "deadline", "created_at", "user_role",
        ]
        read_only_fields = fields

    def get_user_role(self, obj) -> str | None:
        request = self.context.get("request")
        if not request:
            return None
        member = obj.members.filter(user=request.user).first()
        return member.role if member else None


class WorkspaceUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для PATCH кабинета — только изменяемые поля."""

    class Meta:
        model = Workspace
        fields = ["title", "description", "deadline", "status"]

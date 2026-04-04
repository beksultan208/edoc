"""
ГосДок — Сериализаторы организаций (apps/organizations/serializers.py)
Раздел 4.3 ТЗ
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.serializers import UserListSerializer
from .models import Organization

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    """Полный сериализатор организации."""

    owner_name = serializers.CharField(source="owner.full_name", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id", "name", "type", "inn", "address",
            "owner", "owner_name", "created_at",
        ]
        read_only_fields = ["id", "created_at", "owner"]

    def create(self, validated_data):
        # Владелец — текущий пользователь
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class OrganizationListSerializer(serializers.ModelSerializer):
    """Краткий вид для списков."""

    class Meta:
        model = Organization
        fields = ["id", "name", "type", "inn", "created_at"]
        read_only_fields = fields


class InviteMemberSerializer(serializers.Serializer):
    """Приглашение пользователя в организацию по email."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("Пользователь с таким email не найден.")
        return value

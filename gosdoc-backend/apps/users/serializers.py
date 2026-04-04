"""
ГосДок — Сериализаторы для пользователей (apps/users/serializers.py)
Покрывает разделы 4.1, 4.2 ТЗ
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


# ============================================================
# JWT — кастомный serializer, добавляем данные пользователя в токен
# ============================================================
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Расширяет стандартный JWT-сериализатор:
    добавляет email и full_name в payload токена.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Добавляем базовую информацию о пользователе в ответ
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "full_name": self.user.full_name,
        }
        return data


# ============================================================
# Регистрация пользователя
# ============================================================
class RegisterSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации — POST /api/v1/auth/register/"""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["email", "full_name", "phone", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Пароли не совпадают."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


# ============================================================
# Смена пароля
# ============================================================
class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор смены пароля — POST /api/v1/auth/password/change/"""

    old_password = serializers.CharField(required=True, style={"input_type": "password"})
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Новые пароли не совпадают."}
            )
        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value


# ============================================================
# Сброс пароля (запрос)
# ============================================================
class PasswordResetRequestSerializer(serializers.Serializer):
    """Сериализатор запроса сброса пароля — POST /api/v1/auth/password/reset/"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        return value.lower()


class VerifyEmailSerializer(serializers.Serializer):
    """Подтверждение email кодом — POST /api/v1/auth/verify-email/"""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(min_length=6, max_length=6, required=True)

    def validate_email(self, value):
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Сброс пароля по коду — POST /api/v1/auth/password/reset/confirm/"""

    email = serializers.EmailField(required=True)
    code = serializers.CharField(min_length=6, max_length=6, required=True)
    new_password = serializers.CharField(
        min_length=8,
        required=True,
        validators=[__import__("django.contrib.auth.password_validation", fromlist=["validate_password"]).validate_password],
    )

    def validate_email(self, value):
        return value.lower()


# ============================================================
# Профиль пользователя (чтение/редактирование)
# ============================================================
class UserSerializer(serializers.ModelSerializer):
    """Сериализатор профиля пользователя — GET/PATCH /api/v1/users/{id}/"""

    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "organization",
            "organization_name",
            "is_active",
            "created_at",
            "last_login",
        ]
        read_only_fields = ["id", "email", "is_active", "created_at", "last_login"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор обновления профиля (только изменяемые поля)."""

    class Meta:
        model = User
        fields = ["full_name", "phone"]


class UserListSerializer(serializers.ModelSerializer):
    """Краткое представление пользователя для списков."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "is_active", "created_at"]
        read_only_fields = fields

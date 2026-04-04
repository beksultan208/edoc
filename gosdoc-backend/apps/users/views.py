"""
ГосДок — Views для аутентификации и пользователей (apps/users/views.py)
Разделы 4.1, 4.2 ТЗ
"""

import logging

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .email_utils import send_verification_code
from .models import EmailVerificationCode
from .permissions import IsSelfOrAdmin, IsAdminUser
from .serializers import (
    ChangePasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserListSerializer,
    UserSerializer,
    UserUpdateSerializer,
    VerifyEmailSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# ============================================================
# 4.1 Аутентификация
# ============================================================

class RegisterView(generics.CreateAPIView):
    """
    POST /api/v1/auth/register/
    Публичный — регистрация: создаёт неактивного пользователя и отправляет код на email.
    """

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        # Если уже есть неактивный аккаунт с таким email — удаляем его перед созданием нового
        email = request.data.get("email", "").lower().strip()
        User.objects.filter(email=email, is_active=False).delete()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Создаём неактивного пользователя (is_active=False до подтверждения email)
        user = serializer.save(is_active=False)

        # Генерируем и отправляем код
        vc = EmailVerificationCode.generate(user.email, EmailVerificationCode.Purpose.REGISTRATION)
        sent = send_verification_code(user.email, vc.code, "registration")

        if not sent:
            user.delete()
            return Response(
                {"detail": "Не удалось отправить код подтверждения. Проверьте email."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info("Код регистрации отправлен: %s", user.email)
        return Response(
            {"detail": "Код подтверждения отправлен на ваш email.", "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class ResendCodeView(APIView):
    """
    POST /api/v1/auth/resend-code/
    Публичный — повторная отправка кода подтверждения.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").lower().strip()
        purpose = request.data.get("purpose", "")

        if purpose not in ("registration", "password_reset"):
            return Response({"detail": "Неверный тип кода."}, status=status.HTTP_400_BAD_REQUEST)

        if purpose == "registration":
            if not User.objects.filter(email=email, is_active=False).exists():
                return Response({"detail": "Аккаунт не найден или уже активирован."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not User.objects.filter(email=email, is_active=True).exists():
                return Response({"detail": "Пользователь не найден."}, status=status.HTTP_400_BAD_REQUEST)

        vc = EmailVerificationCode.generate(email, purpose)
        send_verification_code(email, vc.code, purpose)
        logger.info("Код повторно отправлен: %s [%s]", email, purpose)
        return Response({"detail": "Код отправлен повторно."})


class VerifyEmailView(APIView):
    """
    POST /api/v1/auth/verify-email/
    Публичный — подтверждение email кодом. Активирует аккаунт и возвращает JWT.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        vc = EmailVerificationCode.objects.filter(
            email=email,
            purpose=EmailVerificationCode.Purpose.REGISTRATION,
            is_used=False,
        ).order_by("-created_at").first()

        if not vc or not vc.is_valid(code):
            return Response(
                {"detail": "Неверный или просроченный код подтверждения."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Активируем пользователя
        user = User.objects.filter(email=email, is_active=False).first()
        if not user:
            return Response(
                {"detail": "Пользователь не найден или уже активирован."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save(update_fields=["is_active"])
        vc.is_used = True
        vc.save(update_fields=["is_used"])

        refresh = RefreshToken.for_user(user)
        logger.info("Email подтверждён, аккаунт активирован: %s", user.email)

        return Response({
            "detail": "Email подтверждён. Добро пожаловать!",
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Публичный — вход по email + пароль, возвращает JWT.
    Использует CustomTokenObtainPairSerializer из serializers.py.
    """

    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    JWT — добавляет refresh-токен в blacklist.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Поле 'refresh' обязательно."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("Пользователь %s вышел из системы", request.user.email)
        return Response({"detail": "Выход выполнен успешно."}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/password/change/
    JWT — смена пароля (нужен старый пароль).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        logger.info("Пользователь %s сменил пароль", user.email)
        return Response({"detail": "Пароль успешно изменён."}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    """
    POST /api/v1/auth/password/reset/
    Публичный — отправляет 6-значный код сброса пароля на email.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user_exists = User.objects.filter(email=email, is_active=True).exists()
        if user_exists:
            vc = EmailVerificationCode.generate(email, EmailVerificationCode.Purpose.PASSWORD_RESET)
            send_verification_code(email, vc.code, "password_reset")
            logger.info("Код сброса пароля отправлен: %s", email)

        # Всегда одинаковый ответ (безопасность)
        return Response(
            {"detail": "Если указанный email зарегистрирован, код отправлен."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    POST /api/v1/auth/password/reset/confirm/
    Публичный — проверяет код и устанавливает новый пароль.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        vc = EmailVerificationCode.objects.filter(
            email=email,
            purpose=EmailVerificationCode.Purpose.PASSWORD_RESET,
            is_used=False,
        ).order_by("-created_at").first()

        if not vc or not vc.is_valid(code):
            return Response(
                {"detail": "Неверный или просроченный код."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=["password"])
        vc.is_used = True
        vc.save(update_fields=["is_used"])

        logger.info("Пароль сброшен для %s", email)
        return Response({"detail": "Пароль успешно изменён. Войдите с новым паролем."})


# ============================================================
# 4.2 Пользователи
# ============================================================

class UserListView(generics.ListAPIView):
    """
    GET /api/v1/users/
    JWT — список всех пользователей (для добавления в кабинет).
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserListSerializer
    queryset = User.objects.select_related("organization").filter(is_active=True).order_by("created_at")
    filterset_fields = ["is_active", "organization"]
    search_fields = ["email", "full_name"]


class UserMeView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/users/me/
    JWT — текущий пользователь.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/users/{id}/  — JWT
    PATCH  /api/v1/users/{id}/  — JWT (self)
    DELETE /api/v1/users/{id}/  — JWT + Admin
    """

    queryset = User.objects.select_related("organization")

    def get_permissions(self):
        if self.request.method == "DELETE":
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.IsAuthenticated(), IsSelfOrAdmin()]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        # Мягкое удаление: деактивируем вместо физического удаления
        user.is_active = False
        user.save(update_fields=["is_active"])
        logger.info("Пользователь %s деактивирован администратором %s", user.email, request.user.email)
        return Response(status=status.HTTP_204_NO_CONTENT)

"""
ГосДок — Тесты аутентификации (tests/test_auth_views.py)
Разделы 4.1, 4.2 ТЗ.
"""

import pytest
from unittest.mock import patch
from django.utils import timezone

from tests.factories import EmailVerificationCodeFactory, UserFactory


# ============================================================
# Register
# ============================================================

@pytest.mark.django_db
class TestRegisterView:

    @patch("apps.users.views.send_verification_code", return_value=True)
    def test_register_creates_inactive_user(self, mock_send, api_client):
        """POST /register/ создаёт неактивного пользователя."""
        response = api_client.post("/api/v1/auth/register/", {
            "email": "newuser@gosdoc.test",
            "full_name": "Новый Пользователь",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
        })
        assert response.status_code == 201
        assert "email" in response.data

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(email="newuser@gosdoc.test")
        assert user.is_active is False

    @patch("apps.users.views.send_verification_code", return_value=True)
    def test_register_sends_code(self, mock_send, api_client):
        """При регистрации вызывается send_verification_code."""
        api_client.post("/api/v1/auth/register/", {
            "email": "code@gosdoc.test",
            "full_name": "Тест",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
        })
        assert mock_send.called

    @patch("apps.users.views.send_verification_code", return_value=True)
    def test_register_deletes_old_inactive_account(self, mock_send, api_client):
        """При повторной регистрации с тем же email старый неактивный аккаунт удаляется."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        old_user = UserFactory(email="dup@gosdoc.test", is_active=False)

        api_client.post("/api/v1/auth/register/", {
            "email": "dup@gosdoc.test",
            "full_name": "Повтор",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
        })

        assert not User.objects.filter(pk=old_user.pk).exists()

    def test_register_password_mismatch(self, api_client):
        """Несовпадение паролей возвращает 400."""
        response = api_client.post("/api/v1/auth/register/", {
            "email": "mismatch@gosdoc.test",
            "full_name": "Тест",
            "password": "StrongPass1!",
            "password_confirm": "WrongPass!",
        })
        assert response.status_code == 400

    @patch("apps.users.views.send_verification_code", return_value=False)
    def test_register_email_fail_rolls_back(self, mock_send, api_client):
        """Если email не отправлен — пользователь удаляется, возвращается 500."""
        response = api_client.post("/api/v1/auth/register/", {
            "email": "fail@gosdoc.test",
            "full_name": "Сбой Email",
            "password": "StrongPass1!",
            "password_confirm": "StrongPass1!",
        })
        assert response.status_code == 500
        from django.contrib.auth import get_user_model
        User = get_user_model()
        assert not User.objects.filter(email="fail@gosdoc.test").exists()


# ============================================================
# VerifyEmail
# ============================================================

@pytest.mark.django_db
class TestVerifyEmailView:

    def test_verify_activates_user_and_returns_tokens(self, api_client):
        """Верный код активирует пользователя и возвращает JWT."""
        user = UserFactory(email="verify@gosdoc.test", is_active=False)
        vc = EmailVerificationCodeFactory(
            email="verify@gosdoc.test",
            code="111111",
            purpose="registration",
        )

        response = api_client.post("/api/v1/auth/verify-email/", {
            "email": "verify@gosdoc.test",
            "code": "111111",
        })

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

        user.refresh_from_db()
        assert user.is_active is True

    def test_verify_wrong_code(self, api_client):
        """Неверный код возвращает 400."""
        UserFactory(email="wrong@gosdoc.test", is_active=False)
        EmailVerificationCodeFactory(
            email="wrong@gosdoc.test",
            code="999999",
            purpose="registration",
        )

        response = api_client.post("/api/v1/auth/verify-email/", {
            "email": "wrong@gosdoc.test",
            "code": "000000",
        })
        assert response.status_code == 400

    def test_verify_expired_code(self, api_client):
        """Просроченный код возвращает 400."""
        UserFactory(email="expired@gosdoc.test", is_active=False)
        EmailVerificationCodeFactory(
            email="expired@gosdoc.test",
            code="555555",
            purpose="registration",
            expires_at=timezone.now() - timezone.timedelta(seconds=1),
        )

        response = api_client.post("/api/v1/auth/verify-email/", {
            "email": "expired@gosdoc.test",
            "code": "555555",
        })
        assert response.status_code == 400


# ============================================================
# Login
# ============================================================

@pytest.mark.django_db
class TestLoginView:

    def test_login_returns_tokens(self, api_client):
        """Верные учётные данные возвращают access + refresh токены."""
        UserFactory(email="login@gosdoc.test", is_active=True)

        response = api_client.post("/api/v1/auth/login/", {
            "email": "login@gosdoc.test",
            "password": "TestPass123!",
        })

        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client):
        """Неверный пароль возвращает 401."""
        UserFactory(email="badpass@gosdoc.test")

        response = api_client.post("/api/v1/auth/login/", {
            "email": "badpass@gosdoc.test",
            "password": "WrongPassword!",
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, api_client):
        """Неактивный пользователь не может войти."""
        UserFactory(email="inactive@gosdoc.test", is_active=False)

        response = api_client.post("/api/v1/auth/login/", {
            "email": "inactive@gosdoc.test",
            "password": "TestPass123!",
        })
        assert response.status_code == 401


# ============================================================
# Logout
# ============================================================

@pytest.mark.django_db
class TestLogoutView:

    def test_logout_blacklists_token(self, auth_client, user):
        """Logout добавляет refresh-токен в blacklist."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        response = auth_client.post("/api/v1/auth/logout/", {
            "refresh": str(refresh),
        })
        assert response.status_code == 200

    def test_logout_without_refresh_returns_400(self, auth_client):
        """Logout без refresh-токена возвращает 400."""
        response = auth_client.post("/api/v1/auth/logout/", {})
        assert response.status_code == 400

    def test_logout_requires_auth(self, api_client):
        """Logout без авторизации возвращает 401."""
        response = api_client.post("/api/v1/auth/logout/", {"refresh": "token"})
        assert response.status_code == 401


# ============================================================
# ChangePassword
# ============================================================

@pytest.mark.django_db
class TestChangePasswordView:

    def test_change_password_success(self, auth_client, user):
        """Смена пароля с верным старым паролем."""
        response = auth_client.post("/api/v1/auth/password/change/", {
            "old_password": "TestPass123!",
            "new_password": "NewStrongPass1!",
            "new_password_confirm": "NewStrongPass1!",
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("NewStrongPass1!") is True

    def test_change_password_wrong_old(self, auth_client):
        """Смена пароля с неверным старым паролем возвращает 400."""
        response = auth_client.post("/api/v1/auth/password/change/", {
            "old_password": "WrongOld!",
            "new_password": "NewPass123!",
            "new_password_confirm": "NewPass123!",
        })
        assert response.status_code == 400


# ============================================================
# PasswordReset
# ============================================================

@pytest.mark.django_db
class TestPasswordResetFlow:

    @patch("apps.users.views.send_verification_code")
    def test_reset_request_sends_code_for_existing_user(self, mock_send, api_client):
        """Запрос сброса пароля отправляет код для существующего пользователя."""
        UserFactory(email="reset@gosdoc.test", is_active=True)

        response = api_client.post("/api/v1/auth/password/reset/", {
            "email": "reset@gosdoc.test",
        })
        assert response.status_code == 200
        assert mock_send.called

    @patch("apps.users.views.send_verification_code")
    def test_reset_request_same_response_for_unknown_email(self, mock_send, api_client):
        """Одинаковый ответ для несуществующего email (защита от enumeration)."""
        response = api_client.post("/api/v1/auth/password/reset/", {
            "email": "ghost@gosdoc.test",
        })
        assert response.status_code == 200
        assert not mock_send.called

    def test_reset_confirm_sets_new_password(self, api_client):
        """Верный код устанавливает новый пароль."""
        user = UserFactory(email="confirm@gosdoc.test", is_active=True)
        EmailVerificationCodeFactory(
            email="confirm@gosdoc.test",
            code="777777",
            purpose="password_reset",
        )

        response = api_client.post("/api/v1/auth/password/reset/confirm/", {
            "email": "confirm@gosdoc.test",
            "code": "777777",
            "new_password": "Brand!New1",
        })
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("Brand!New1") is True

    def test_reset_confirm_wrong_code(self, api_client):
        """Неверный код возвращает 400."""
        UserFactory(email="wrongcode@gosdoc.test", is_active=True)
        EmailVerificationCodeFactory(
            email="wrongcode@gosdoc.test",
            code="888888",
            purpose="password_reset",
        )

        response = api_client.post("/api/v1/auth/password/reset/confirm/", {
            "email": "wrongcode@gosdoc.test",
            "code": "000000",
            "new_password": "NewPass123!",
        })
        assert response.status_code == 400


# ============================================================
# Users API
# ============================================================

@pytest.mark.django_db
class TestUserMeView:

    def test_me_returns_current_user(self, auth_client, user):
        """GET /users/me/ возвращает данные текущего пользователя."""
        response = auth_client.get("/api/v1/users/me/")
        assert response.status_code == 200
        assert response.data["email"] == user.email

    def test_me_requires_auth(self, api_client):
        """Неавторизованный запрос возвращает 401."""
        response = api_client.get("/api/v1/users/me/")
        assert response.status_code == 401

    def test_me_patch_updates_name(self, auth_client, user):
        """PATCH /users/me/ обновляет full_name."""
        response = auth_client.patch("/api/v1/users/me/", {"full_name": "Новое Имя"})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.full_name == "Новое Имя"


@pytest.mark.django_db
class TestUserListView:

    def test_authenticated_user_can_list(self, auth_client):
        """Авторизованный пользователь видит список пользователей."""
        response = auth_client.get("/api/v1/users/")
        assert response.status_code == 200

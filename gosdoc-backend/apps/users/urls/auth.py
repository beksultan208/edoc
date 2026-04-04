"""
ГосДок — URL аутентификации (apps/users/urls/auth.py)
Раздел 4.1 ТЗ
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import (
    ChangePasswordView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendCodeView,
    VerifyEmailView,
)

urlpatterns = [
    # POST /api/v1/auth/register/
    path("register/", RegisterView.as_view(), name="auth-register"),
    # POST /api/v1/auth/verify-email/
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    # POST /api/v1/auth/resend-code/
    path("resend-code/", ResendCodeView.as_view(), name="auth-resend-code"),
    # POST /api/v1/auth/login/
    path("login/", LoginView.as_view(), name="auth-login"),
    # POST /api/v1/auth/refresh/
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    # POST /api/v1/auth/logout/
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    # POST /api/v1/auth/password/change/
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    # POST /api/v1/auth/password/reset/
    path("password/reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    # POST /api/v1/auth/password/reset/confirm/
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
]

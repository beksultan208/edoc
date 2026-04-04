"""
ГосДок — Модель пользователя (apps/users/models.py)
Custom AbstractUser: email как логин, UUID PK, bcrypt-хэш пароля (раздел 3.2 ТЗ)
"""

import random
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Менеджер для кастомной модели пользователя с email-логином."""

    def create_user(self, email: str, full_name: str, password: str = None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)  # bcrypt через Django
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, full_name: str, password: str = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, full_name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Пользователь ГосДок.

    Поля по разделу 3.2 ТЗ:
    - id: UUID PK
    - email: логин (уникальный)
    - full_name: полное имя
    - phone: телефон
    - organization_id: FK → organizations
    - password (AbstractBaseUser): bcrypt-хэш
    - is_active, is_staff
    - created_at, last_login
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
    )
    email = models.EmailField(
        max_length=255,
        unique=True,
        verbose_name="Email",
        db_index=True,
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Полное имя",
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Телефон",
    )
    # FK → organizations устанавливается через строковую ссылку,
    # чтобы избежать циклических импортов
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Организация",
        db_index=True,
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    is_staff = models.BooleanField(default=False, verbose_name="Сотрудник")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    # last_login наследуется от AbstractBaseUser

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        db_table = "users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    @property
    def password_hash(self) -> str:
        """Алиас для совместимости с ТЗ (раздел 3.2)."""
        return self.password


class EmailVerificationCode(models.Model):
    """
    6-значный код подтверждения email.
    Используется при регистрации и сбросе пароля.
    """

    class Purpose(models.TextChoices):
        REGISTRATION = "registration", "Регистрация"
        PASSWORD_RESET = "password_reset", "Сброс пароля"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "email_verification_codes"
        indexes = [models.Index(fields=["email", "purpose"])]

    @classmethod
    def generate(cls, email: str, purpose: str) -> "EmailVerificationCode":
        """Создаёт новый код, инвалидирует предыдущие для этого email+purpose."""
        cls.objects.filter(email=email, purpose=purpose, is_used=False).update(is_used=True)
        code = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timezone.timedelta(minutes=15)
        return cls.objects.create(email=email, code=code, purpose=purpose, expires_at=expires_at)

    def is_valid(self, code: str) -> bool:
        return (
            not self.is_used
            and self.code == code
            and timezone.now() < self.expires_at
        )

    def __str__(self) -> str:
        return f"{self.email} [{self.purpose}] — {self.code}"

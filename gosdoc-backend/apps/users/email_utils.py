"""
ГосДок — Утилиты отправки email-кодов подтверждения.
"""

from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_verification_code(email: str, code: str, purpose: str) -> bool:
    """Отправляет 6-значный код на указанный email."""
    if purpose == "registration":
        subject = "Подтверждение регистрации — ГосДок"
        message = (
            f"Ваш код подтверждения для регистрации в системе ГосДок:\n\n"
            f"  {code}\n\n"
            f"Код действителен 15 минут.\n"
            f"Если вы не регистрировались — проигнорируйте это письмо."
        )
    else:
        subject = "Сброс пароля — ГосДок"
        message = (
            f"Ваш код для сброса пароля в системе ГосДок:\n\n"
            f"  {code}\n\n"
            f"Код действителен 15 минут.\n"
            f"Если вы не запрашивали сброс — проигнорируйте это письмо."
        )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Код подтверждения отправлен на %s [%s]", email, purpose)
        return True
    except Exception as exc:
        logger.error("Ошибка отправки email на %s: %s", email, exc)
        return False

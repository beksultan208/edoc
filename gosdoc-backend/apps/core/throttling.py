"""
ГосДок — Rate limiting (apps/core/throttling.py)
Раздел 6 ТЗ: 100 запросов/минуту на пользователя.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class StandardUserThrottle(UserRateThrottle):
    """100 запросов в минуту для аутентифицированных пользователей."""
    rate = "100/min"
    scope = "standard_user"


class AuthAnonThrottle(AnonRateThrottle):
    """10 запросов в минуту для анонимных (только auth эндпоинты)."""
    rate = "10/min"
    scope = "auth_anon"


class UploadThrottle(UserRateThrottle):
    """20 запросов в минуту на загрузку документов (тяжёлые операции)."""
    rate = "20/min"
    scope = "upload"

"""
ГосДок — Сериализаторы подписей
"""

from rest_framework import serializers
from .models import Signature


class SignatureSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Signature
        fields = [
            "id", "document", "user", "user_name",
            "signature_data", "certificate_id",
            "signed_at", "ip_address", "is_valid",
        ]
        read_only_fields = ["id", "user", "signed_at", "ip_address", "is_valid"]


class SignDocumentSerializer(serializers.Serializer):
    """Сериализатор для подписи документа."""
    signature_data = serializers.CharField(required=True, help_text="Base64-encoded данные подписи")
    certificate_id = serializers.CharField(required=False, allow_blank=True)

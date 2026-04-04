"""
ГосДок — Views подписей (apps/signatures/views.py)
Раздел 4.7 ТЗ

При подписи:
- Проверяем роль signer/owner/editor
- Сохраняем метаданные (время, IP, сертификат)
- Если все подписанты подписали → статус signed, блокируем редактирование
- Уведомляем всех участников (раздел 2.8 ТЗ)
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.workspaces.models import WorkspaceMember
from .models import Signature
from .serializers import SignDocumentSerializer, SignatureSerializer

logger = logging.getLogger(__name__)


class SignDocumentView(APIView):
    """
    POST /api/v1/documents/{id}/sign/
    JWT + Signer — подписать документ.
    Раздел 2.7 ТЗ: подписанный документ блокируется от редактирования.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace"),
            pk=pk,
        )

        # Только подписанты и выше (раздел 2.2 ТЗ)
        member = WorkspaceMember.objects.filter(
            workspace=document.workspace,
            user=request.user,
            role__in=[
                WorkspaceMember.Role.OWNER,
                WorkspaceMember.Role.EDITOR,
                WorkspaceMember.Role.SIGNER,
            ],
        ).first()

        if not member:
            return Response(
                {"detail": "Только подписанты (signer/editor/owner) могут подписывать документы."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Подписанный документ заблокирован (раздел 2.7 ТЗ)
        if document.status == Document.DocumentStatus.SIGNED:
            return Response(
                {"detail": "Документ уже подписан и заблокирован от изменений."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Архивный документ нельзя подписывать
        if document.status == Document.DocumentStatus.ARCHIVED:
            return Response(
                {"detail": "Архивный документ нельзя подписать."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем, не подписал ли пользователь уже этот документ
        if Signature.objects.filter(document=document, user=request.user, is_valid=True).exists():
            return Response(
                {"detail": "Вы уже подписали этот документ."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = SignDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Получаем IP-адрес (метаданные подписи, раздел 3.7 ТЗ)
        ip_address = self._get_client_ip(request)

        signature = Signature.objects.create(
            document=document,
            user=request.user,
            signature_data=serializer.validated_data["signature_data"],
            certificate_id=serializer.validated_data.get("certificate_id", "") or "",
            ip_address=ip_address,
        )

        logger.info(
            "Документ '%s' подписан пользователем %s (IP: %s)",
            document.title, request.user.email, ip_address,
        )

        # Проверяем: все ли обязательные подписанты подписали
        all_signed = self._check_all_signed(document)
        if all_signed:
            document.status = Document.DocumentStatus.SIGNED
            document.save(update_fields=["status", "updated_at"])
            logger.info("Документ '%s' полностью подписан — статус SIGNED", document.title)

            # Уведомляем всех участников (раздел 2.8 ТЗ)
            from apps.tasks.workflow import notify_document_signed
            notify_document_signed(document, request.user)

        return Response(
            {
                "signature": SignatureSerializer(signature).data,
                "document_fully_signed": all_signed,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _get_client_ip(request) -> str:
        """Извлекает реальный IP с учётом reverse proxy."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "0.0.0.0")

    @staticmethod
    def _check_all_signed(document) -> bool:
        """
        Проверяет, подписали ли документ все участники с ролью signer/owner.
        Возвращает True, если хотя бы один подписант есть и все подписали.
        """
        required_signers = WorkspaceMember.objects.filter(
            workspace=document.workspace,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.SIGNER],
        ).values_list("user_id", flat=True)

        if not required_signers:
            return False

        signed_users = Signature.objects.filter(
            document=document,
            is_valid=True,
        ).values_list("user_id", flat=True)

        return set(required_signers).issubset(set(signed_users))


class SignatureListView(generics.ListAPIView):
    """
    GET /api/v1/documents/{id}/signatures/
    JWT + Member — список подписей документа.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SignatureSerializer
    pagination_class = None  # возвращаем массив напрямую

    def get_queryset(self):
        document = get_object_or_404(
            Document.objects.filter(workspace__members__user=self.request.user),
            pk=self.kwargs["pk"],
        )
        return document.signatures.select_related("user").order_by("signed_at")


class SignatureVerifyView(APIView):
    """
    GET /api/v1/signatures/{id}/verify/
    JWT — верификация подписи.
    Раздел 2.7 ТЗ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        signature = get_object_or_404(
            Signature.objects.filter(
                document__workspace__members__user=request.user
            ).select_related("user", "document").distinct(),
            pk=pk,
        )

        return Response({
            "id": str(signature.id),
            "is_valid": signature.is_valid,
            "document": {
                "id": str(signature.document.id),
                "title": signature.document.title,
                "status": signature.document.status,
            },
            "signer": {
                "id": str(signature.user.id) if signature.user else None,
                "full_name": signature.user.full_name if signature.user else None,
                "email": signature.user.email if signature.user else None,
            },
            "signed_at": signature.signed_at,
            "ip_address": signature.ip_address,
            "certificate_id": signature.certificate_id or None,
        })

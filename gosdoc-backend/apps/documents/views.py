"""
ГосДок — Views документов и комментариев (apps/documents/views.py)
Разделы 4.5, 4.8 ТЗ

Схема загрузки документа (раздел 6 ТЗ — без проксирования):
  1. POST /api/v1/documents/request-upload/ → presigned POST URL
  2. Клиент загружает файл напрямую в S3
  3. POST /api/v1/documents/            → подтверждение, создание записи в БД

Схема загрузки новой версии:
  1. POST /api/v1/documents/{id}/versions/request-upload/ → presigned POST URL
  2. Клиент загружает файл напрямую в S3
  3. POST /api/v1/documents/{id}/versions/               → подтверждение
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.models import Workspace, WorkspaceMember
from .models import Comment, Document, DocumentVersion
from .serializers import (
    CommentSerializer,
    DocumentConfirmUploadSerializer,
    DocumentListSerializer,
    DocumentSerializer,
    DocumentUpdateSerializer,
    DocumentVersionListSerializer,
    DocumentVersionSerializer,
    NewVersionConfirmSerializer,
    NewVersionPresignedRequestSerializer,
    PresignedUploadRequestSerializer,
)
from .storage import (
    check_object_exists,
    compute_sha256,
    delete_from_s3,
    generate_presigned_post,
    generate_presigned_url,
    generate_storage_key,
    get_content_type,
    upload_to_s3,
)

logger = logging.getLogger(__name__)


# ============================================================
# Вспомогательные утилиты
# ============================================================

def get_workspace_role(user, workspace) -> str | None:
    """Возвращает роль пользователя в кабинете или None."""
    member = WorkspaceMember.objects.filter(workspace=workspace, user=user).first()
    return member.role if member else None


def assert_workspace_role(user, workspace, allowed_roles: list):
    """
    Поднимает PermissionDenied, если роль пользователя не в allowed_roles.
    Создатель кабинета всегда считается owner.
    """
    from rest_framework.exceptions import PermissionDenied
    # Создатель кабинета всегда имеет права owner
    if workspace.created_by_id == user.pk or user.is_staff:
        return
    role = get_workspace_role(user, workspace)
    if role not in allowed_roles:
        raise PermissionDenied(
            f"Требуется одна из ролей: {', '.join(allowed_roles)}. У вас: {role or 'нет доступа'}."
        )


# ============================================================
# 4.5 — Двухэтапная загрузка документа (presigned POST)
# ============================================================

class RequestUploadView(APIView):
    """
    POST /api/v1/documents/request-upload/
    JWT — возвращает presigned POST URL для прямой загрузки в S3.

    Шаг 1 из 2: клиент получает URL и поля формы, загружает файл в S3.
    После успешной загрузки вызывает POST /api/v1/documents/ (подтверждение).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=PresignedUploadRequestSerializer,
        summary="Получить presigned POST URL для загрузки документа в S3",
    )
    def post(self, request):
        serializer = PresignedUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        workspace = get_object_or_404(Workspace, pk=data["workspace"])
        assert_workspace_role(request.user, workspace, ["owner", "editor"])

        file_name = data["file_name"]
        content_type = get_content_type(file_name)
        storage_key = generate_storage_key(str(workspace.id), file_name)

        presigned = generate_presigned_post(
            storage_key=storage_key,
            content_type=content_type,
            max_size_bytes=data["file_size"],
            expiration=3600,
        )

        if not presigned:
            return Response(
                {"detail": "Не удалось сгенерировать URL для загрузки. Проверьте настройки S3."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Сгенерирован presigned POST: workspace=%s, file=%s, key=%s",
            workspace.id, file_name, storage_key,
        )

        return Response(
            {
                "upload_url": presigned["url"],
                "upload_fields": presigned["fields"],
                "storage_key": storage_key,
                "expires_in": 3600,
                # Передаём обратно для использования на шаге 2
                "meta": {
                    "workspace_id": str(workspace.id),
                    "title": data["title"],
                    "file_name": file_name,
                },
            },
            status=status.HTTP_200_OK,
        )


class DocumentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/documents/ — список документов пользователя (JWT + Member)
    POST /api/v1/documents/ — подтверждение загрузки документа (шаг 2 из 2)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DocumentConfirmUploadSerializer
        return DocumentListSerializer

    def get_queryset(self):
        qs = Document.objects.filter(
            workspace__members__user=self.request.user
        ).select_related(
            "workspace", "uploaded_by", "current_version"
        ).distinct().order_by("-created_at")

        # Фильтрация по статусу и кабинету
        status_filter = self.request.query_params.get("status")
        workspace_filter = self.request.query_params.get("workspace")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if workspace_filter:
            qs = qs.filter(workspace_id=workspace_filter)
        return qs

    def create(self, request, *args, **kwargs):
        """
        Шаг 2: клиент сообщает storage_key (полученный от request-upload/),
        Django проверяет наличие объекта в S3 и создаёт запись в БД.
        """
        serializer = DocumentConfirmUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        workspace = get_object_or_404(Workspace, pk=data["workspace"])
        assert_workspace_role(request.user, workspace, ["owner", "editor"])

        storage_key = data["storage_key"]
        file_name = data["file_name"]

        # Проверяем, что файл действительно загружен в S3
        if not check_object_exists(storage_key):
            return Response(
                {
                    "detail": "Файл не найден в хранилище. Убедитесь, что загрузка в S3 завершена.",
                    "storage_key": storage_key,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Определяем тип файла из имени
        file_ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

        # Создаём документ (пока без current_version — добавим ниже)
        document = Document.objects.create(
            workspace=workspace,
            title=data["title"],
            file_type=file_ext,
            storage_key=storage_key,
            uploaded_by=request.user,
            status=Document.DocumentStatus.DRAFT,
        )

        # Создаём первую версию (checksum можно заполнить позже через Celery,
        # здесь ставим заглушку — реальный checksum вычисляется при серверной загрузке)
        version = DocumentVersion.objects.create(
            document=document,
            version_number=1,
            storage_key=storage_key,
            checksum="pending",  # Будет обновлён Celery-задачей в этапе 3
            created_by=request.user,
        )

        # Связываем документ с первой версией
        document.current_version = version
        document.save(update_fields=["current_version"])

        # Запускаем Celery-задачу для вычисления SHA-256
        # (AI-diff для первой версии не нужен, задача обработает это сама)
        try:
            from apps.documents.tasks import analyze_version_diff_task
            analyze_version_diff_task.delay(str(version.id))
        except Exception as exc:
            logger.warning("Не удалось запустить задачу SHA-256 для версии %s: %s", version.id, exc)

        logger.info(
            "Документ создан (presigned POST): %s [workspace=%s]",
            document.title, workspace.id,
        )

        return Response(
            DocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/documents/{id}/ — JWT + Member
    PATCH  /api/v1/documents/{id}/ — JWT + Editor (только title)
    DELETE /api/v1/documents/{id}/ — JWT + Owner (мягкое архивирование)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return DocumentUpdateSerializer
        return DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(
            workspace__members__user=self.request.user
        ).select_related(
            "workspace", "uploaded_by", "current_version"
        ).distinct()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ("PATCH", "PUT"):
            assert_workspace_role(request.user, obj.workspace, ["owner", "editor"])
        elif request.method == "DELETE":
            assert_workspace_role(request.user, obj.workspace, ["owner"])

    def destroy(self, request, *args, **kwargs):
        """Мягкое удаление: переводим в статус archived."""
        document = self.get_object()
        document.status = Document.DocumentStatus.ARCHIVED
        document.save(update_fields=["status", "updated_at"])
        logger.info("Документ архивирован: %s (by %s)", document.title, request.user.email)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentDownloadView(APIView):
    """
    GET /api/v1/documents/{id}/download/
    JWT + Member — возвращает presigned GET URL (TTL 60 мин, раздел 6 ТЗ).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace"),
            pk=pk,
        )
        # Имя файла для Content-Disposition
        filename = f"{document.title}.{document.file_type}"
        url = generate_presigned_url(document.storage_key, filename=filename)

        if not url:
            return Response(
                {"detail": "Не удалось сгенерировать ссылку для скачивания."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "download_url": url,
            "expires_in": 3600,
            "file_name": filename,
            "file_type": document.file_type,
        })


# ============================================================
# 4.5 — Версии документов
# ============================================================

class DocumentVersionListView(generics.ListAPIView):
    """
    GET /api/v1/documents/{id}/versions/
    JWT + Member — история версий документа.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentVersionListSerializer
    pagination_class = None  # возвращаем массив напрямую

    def get_queryset(self):
        document = get_object_or_404(
            Document.objects.filter(workspace__members__user=self.request.user),
            pk=self.kwargs["pk"],
        )
        return document.versions.select_related("created_by").order_by("-version_number")


class RequestVersionUploadView(APIView):
    """
    POST /api/v1/documents/{id}/versions/request-upload/
    JWT + Editor — получить presigned POST URL для новой версии (шаг 1).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace"),
            pk=pk,
        )

        # Подписанный документ нельзя редактировать (раздел 2.7 ТЗ)
        if document.status == Document.DocumentStatus.SIGNED:
            return Response(
                {"detail": "Подписанный документ нельзя редактировать."},
                status=status.HTTP_403_FORBIDDEN,
            )

        assert_workspace_role(request.user, document.workspace, ["owner", "editor"])

        serializer = NewVersionPresignedRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_name = serializer.validated_data["file_name"]
        content_type = get_content_type(file_name)
        storage_key = generate_storage_key(str(document.workspace.id), file_name)

        presigned = generate_presigned_post(
            storage_key=storage_key,
            content_type=content_type,
            max_size_bytes=serializer.validated_data["file_size"],
            expiration=3600,
        )

        if not presigned:
            return Response(
                {"detail": "Не удалось сгенерировать URL для загрузки."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "upload_url": presigned["url"],
            "upload_fields": presigned["fields"],
            "storage_key": storage_key,
            "expires_in": 3600,
            "meta": {
                "document_id": str(document.id),
                "next_version": document.versions.count() + 1,
            },
        })


class DocumentVersionCreateView(APIView):
    """
    POST /api/v1/documents/{id}/versions/
    JWT + Editor — подтверждение загрузки новой версии (шаг 2).

    При создании новой версии:
    - Проверяем наличие файла в S3
    - Создаём DocumentVersion запись
    - Запускаем AI-анализ в фоне (Celery, этап 3)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace"),
            pk=pk,
        )

        if document.status == Document.DocumentStatus.SIGNED:
            return Response(
                {"detail": "Подписанный документ нельзя редактировать."},
                status=status.HTTP_403_FORBIDDEN,
            )

        assert_workspace_role(request.user, document.workspace, ["owner", "editor"])

        serializer = NewVersionConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        storage_key = serializer.validated_data["storage_key"]
        file_name = serializer.validated_data["file_name"]

        if not check_object_exists(storage_key):
            return Response(
                {"detail": "Файл не найден в хранилище. Завершите загрузку в S3."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        new_version_number = document.versions.count() + 1
        version = DocumentVersion.objects.create(
            document=document,
            version_number=new_version_number,
            storage_key=storage_key,
            checksum="pending",  # Будет обновлён Celery-задачей (этап 3)
            created_by=request.user,
        )

        # Обновляем текущую версию документа
        document.current_version = version
        document.save(update_fields=["current_version", "updated_at"])

        # Запускаем AI-анализ изменений асинхронно через Celery
        # (раздел 2.6 ТЗ, задача 8 этапа 3: SHA-256 + diff + LLM-резюме)
        try:
            from apps.documents.tasks import analyze_version_diff_task
            analyze_version_diff_task.delay(str(version.id))
        except Exception as exc:
            logger.warning("Не удалось запустить задачу AI-анализа для версии %s: %s", version.id, exc)

        logger.info(
            "Версия %d создана для документа '%s' (by %s)",
            new_version_number, document.title, request.user.email,
        )

        return Response(DocumentVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class DocumentVersionDiffView(APIView):
    """
    GET /api/v1/documents/{id}/versions/{vid}/diff/
    JWT + Member — AI-анализ изменений конкретной версии.
    Раздел 2.6 ТЗ: возвращает ai_diff_summary из DocumentVersion.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, vid):
        document = get_object_or_404(
            Document.objects.filter(workspace__members__user=request.user),
            pk=pk,
        )
        version = get_object_or_404(DocumentVersion, pk=vid, document=document)

        if version.version_number == 1:
            return Response({
                "version_number": 1,
                "ai_changes_detected": False,
                "ai_diff_summary": None,
                "detail": "Первая версия — нет предыдущей для сравнения.",
            })

        return Response({
            "version_id": str(version.id),
            "version_number": version.version_number,
            "ai_changes_detected": version.ai_changes_detected,
            "ai_diff_summary": version.ai_diff_summary,
            "checksum": version.checksum,
            "created_at": version.created_at,
        })


# ============================================================
# 4.5 — Жизненный цикл документа (workflow)
# ============================================================

class DocumentWorkflowStartView(APIView):
    """
    POST /api/v1/documents/{id}/workflow/start/
    JWT + Owner — запускает workflow: draft → review.
    Создаёт задачи для каждого участника по step_order.
    Раздел 2.3 ТЗ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace"),
            pk=pk,
        )

        assert_workspace_role(request.user, document.workspace, ["owner"])

        if document.status != Document.DocumentStatus.DRAFT:
            return Response(
                {
                    "detail": f"Workflow можно запустить только для черновика. "
                              f"Текущий статус: {document.get_status_display()}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем, что есть участники с step_order
        members_with_steps = document.workspace.members.filter(
            step_order__isnull=False
        ).order_by("step_order")

        if not members_with_steps.exists():
            return Response(
                {
                    "detail": "Нет участников с заданным step_order. "
                              "Добавьте порядок шагов участникам кабинета перед запуском workflow."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Переводим документ в статус review
        document.status = Document.DocumentStatus.REVIEW
        document.save(update_fields=["status", "updated_at"])

        # Создаём задачи и активируем первый шаг
        from apps.tasks.workflow import create_workflow_tasks
        tasks = create_workflow_tasks(document, document.workspace)

        logger.info(
            "Workflow запущен для документа '%s': %d задач (by %s)",
            document.title, len(tasks), request.user.email,
        )

        return Response({
            "detail": "Workflow запущен.",
            "status": document.status,
            "tasks_created": len(tasks),
        })


# ============================================================
# 4.8 — Комментарии
# ============================================================

class CommentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/documents/{id}/comments/ — JWT + Member
    POST /api/v1/documents/{id}/comments/ — JWT + Member
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer
    pagination_class = None  # возвращаем массив напрямую

    def _get_document(self):
        return get_object_or_404(
            Document.objects.filter(workspace__members__user=self.request.user),
            pk=self.kwargs["pk"],
        )

    def get_queryset(self):
        document = self._get_document()
        # Только корневые комментарии; ответы — через SerializerMethod
        return (
            document.comments
            .filter(parent__isnull=True)
            .select_related("author")
            .prefetch_related("replies__author")
            .order_by("created_at")
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["document_id"] = self.kwargs.get("pk")
        return ctx

    def perform_create(self, serializer):
        document = self._get_document()
        comment = serializer.save(document=document, author=self.request.user)

        # Уведомляем всех участников кабинета о новом комментарии (раздел 2.8 ТЗ)
        from apps.notifications.services import notify_new_comment
        notify_new_comment(comment)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    PATCH  /api/v1/comments/{id}/ — автор
    DELETE /api/v1/comments/{id}/ — автор или owner кабинета
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(
            document__workspace__members__user=self.request.user
        ).select_related("author", "document__workspace").distinct()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        from rest_framework.exceptions import PermissionDenied
        if request.method in ("PATCH", "PUT") and obj.author != request.user:
            raise PermissionDenied("Только автор может редактировать комментарий.")
        if request.method == "DELETE":
            is_workspace_owner = obj.document.workspace.members.filter(
                user=request.user, role="owner"
            ).exists()
            if obj.author != request.user and not is_workspace_owner:
                raise PermissionDenied("Недостаточно прав для удаления комментария.")


class CommentResolveView(APIView):
    """
    POST /api/v1/comments/{id}/resolve/
    JWT + Owner — закрывает комментарий.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        comment = get_object_or_404(
            Comment.objects.filter(
                document__workspace__members__user=request.user
            ).select_related("document__workspace").distinct(),
            pk=pk,
        )
        is_owner = comment.document.workspace.members.filter(
            user=request.user, role="owner"
        ).exists()
        if not is_owner:
            return Response(
                {"detail": "Только владелец кабинета может закрывать комментарии."},
                status=status.HTTP_403_FORBIDDEN,
            )

        comment.is_resolved = True
        comment.save(update_fields=["is_resolved"])
        logger.info("Комментарий %s закрыт пользователем %s", pk, request.user.email)
        return Response({"detail": "Комментарий закрыт."})

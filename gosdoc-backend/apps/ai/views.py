"""
ГосДок — Views AI-сервиса (apps/ai/views.py)

Endpoints:
  POST /api/v1/ai/generate/        — генерация текста документа по описанию
  POST /api/v1/ai/summarize/       — резюме и ключевые тезисы документа
  POST /api/v1/ai/search/          — семантический поиск по документам кабинета
  POST /api/v1/ai/embed/           — ручной запуск индексации документа в pgvector
  POST /api/v1/ai/classify/        — ML-классификация типа документа
  POST /api/v1/ai/chat/document/   — чат с конкретным документом (RAG)
  POST /api/v1/ai/chat/general/    — общий AI ассистент по кабинету
  GET  /api/v1/ai/chat/history/    — история сообщений чата
"""

import logging
import os
import tempfile

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.ai_diff import extract_text
from apps.documents.models import Document
from apps.workspaces.models import Workspace, WorkspaceMember
from .models import ChatMessage
from .serializers import (
    ChatHistoryQuerySerializer,
    ChatMessageSerializer,
    ChatWithDocumentSerializer,
    ClassifyDocumentSerializer,
    EmbedDocumentSerializer,
    GeneralChatSerializer,
    GenerateDocumentSerializer,
    SearchDocumentsSerializer,
    SummarizeDocumentSerializer,
)
from .services import AIService, get_ai_service

logger = logging.getLogger(__name__)


class GenerateDocumentView(APIView):
    """
    POST /api/v1/ai/generate/
    JWT — генерирует текст официального документа по описанию пользователя.

    Не создаёт Document в БД — возвращает только текст.
    Пользователь может скопировать текст, доработать и загрузить как файл.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=GenerateDocumentSerializer,
        summary="Генерация текста документа с помощью Claude AI",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Сгенерированный текст документа"},
                    "doc_type": {"type": "string"},
                },
            }
        },
    )
    def post(self, request):
        serializer = GenerateDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            ai = get_ai_service()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            content = ai.generate_document(
                description=data["description"],
                doc_type=data["doc_type"],
            )
        except Exception as exc:
            logger.error(
                "Ошибка генерации документа (user=%s, doc_type=%s): %s",
                request.user.email, data["doc_type"], exc,
            )
            return Response(
                {"detail": "Ошибка AI-сервиса. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info(
            "Документ сгенерирован: user=%s, doc_type=%s, chars=%d",
            request.user.email, data["doc_type"], len(content),
        )
        return Response({"content": content, "doc_type": data["doc_type"]})


class SummarizeDocumentView(APIView):
    """
    POST /api/v1/ai/summarize/
    JWT + Member — создаёт резюме и ключевые тезисы существующего документа.

    Алгоритм:
      1. Проверяем, что пользователь — участник кабинета документа
      2. Скачиваем файл из S3 во временный файл
      3. Извлекаем текст (PDF / DOCX / ODT)
      4. Отправляем в Claude → получаем {"summary": ..., "key_points": [...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=SummarizeDocumentSerializer,
        summary="Резюме документа с помощью Claude AI",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "key_points": {"type": "array", "items": {"type": "string"}},
                    "document_id": {"type": "string"},
                    "document_title": {"type": "string"},
                },
            }
        },
    )
    def post(self, request):
        serializer = SummarizeDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_id = serializer.validated_data["document_id"]

        # Проверяем доступ: пользователь должен быть участником кабинета
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace", "current_version").distinct(),
            pk=document_id,
        )

        try:
            ai = get_ai_service()
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        text = self._extract_document_text(document)

        if not text:
            return Response(
                {
                    "detail": (
                        "Не удалось извлечь текст из документа. "
                        "Поддерживаются форматы: PDF, DOCX, ODT."
                    )
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        try:
            result = ai.summarize_document(text)
        except Exception as exc:
            logger.error(
                "Ошибка резюме документа %s (user=%s): %s",
                document_id, request.user.email, exc,
            )
            return Response(
                {"detail": "Ошибка AI-сервиса. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info(
            "Резюме создано: document=%s, user=%s",
            document_id, request.user.email,
        )
        return Response({
            "document_id": str(document.id),
            "document_title": document.title,
            "summary": result["summary"],
            "key_points": result["key_points"],
        })

    # ------------------------------------------------------------------
    # Вспомогательный метод (S3 → temp file → text)
    # ------------------------------------------------------------------

    def _extract_document_text(self, document: Document) -> str:
        """
        Скачивает документ из S3 во временный файл и извлекает текст.
        При отсутствии S3 или ошибке — возвращает пустую строку.
        """
        from django.conf import settings

        if not settings.AWS_ACCESS_KEY_ID:
            logger.warning(
                "S3 не настроен — пропускаем извлечение текста для документа %s",
                document.id,
            )
            return ""

        from apps.documents.storage import get_s3_client

        storage_key = document.storage_key
        file_type = document.file_type.lower()

        if file_type not in {"pdf", "docx", "odt"}:
            logger.info(
                "Тип '%s' не поддерживает извлечение текста (документ %s)",
                file_type, document.id,
            )
            return ""

        tmp_path = None
        try:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            s3_client = get_s3_client()

            fd, tmp_path = tempfile.mkstemp(suffix=f".{file_type}")
            os.close(fd)

            s3_client.download_file(bucket, storage_key, tmp_path)
            return extract_text(tmp_path, file_type)

        except Exception as exc:
            logger.error(
                "Не удалось скачать/обработать документ %s из S3: %s",
                document.id, exc,
            )
            return ""

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


class SearchDocumentsView(APIView):
    """
    POST /api/v1/ai/search/
    JWT + Member — семантический поиск по документам кабинета.

    Алгоритм:
      1. Проверяем, что пользователь — участник кабинета (workspace_id)
      2. Генерируем embedding для запроса через sentence-transformers
      3. Ищем top_k ближайших чанков через pgvector (cosine distance)
      4. Возвращаем [{"document_id", "title", "chunk_text", "score"}]
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=SearchDocumentsSerializer,
        summary="Семантический поиск по документам кабинета (RAG)",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "chunk_text": {"type": "string"},
                                "score": {"type": "number", "description": "Cosine similarity [0..1]"},
                            },
                        },
                    }
                },
            }
        },
    )
    def post(self, request):
        serializer = SearchDocumentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        workspace_id = data["workspace_id"]

        # Проверяем, что пользователь — участник кабинета
        is_member = WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=request.user,
        ).exists()
        if not is_member:
            return Response(
                {"detail": "У вас нет доступа к этому кабинету."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            ai = AIService()
            results = ai.search_documents(
                query=data["query"],
                workspace_id=str(workspace_id),
                top_k=data.get("top_k", 5),
            )
        except Exception as exc:
            logger.error(
                "Ошибка поиска (user=%s, workspace=%s): %s",
                request.user.email, workspace_id, exc,
            )
            return Response(
                {"detail": "Ошибка AI-поиска. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info(
            "Поиск выполнен: user=%s, workspace=%s, query='%s...', results=%d",
            request.user.email, workspace_id, data["query"][:30], len(results),
        )
        return Response({"results": results})


class EmbedDocumentView(APIView):
    """
    POST /api/v1/ai/embed/
    JWT + Member — ручной запуск индексации документа в pgvector.

    Запускает Celery-задачу embed_document_task асинхронно.
    Обычно индексация происходит автоматически через post_save сигнал
    на DocumentVersion, этот endpoint — для повторной индексации.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=EmbedDocumentSerializer,
        summary="Запустить индексацию документа в pgvector (RAG)",
        responses={
            202: {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "ok"},
                    "detail": {"type": "string"},
                    "document_id": {"type": "string"},
                },
            }
        },
    )
    def post(self, request):
        serializer = EmbedDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_id = serializer.validated_data["document_id"]

        # Проверяем доступ: пользователь должен быть участником кабинета документа
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).distinct(),
            pk=document_id,
        )

        try:
            from apps.ai.tasks import embed_document_task
            embed_document_task.delay(str(document.id))
        except Exception as exc:
            logger.error(
                "Ошибка запуска embed_document_task (doc=%s, user=%s): %s",
                document.id, request.user.email, exc,
            )
            return Response(
                {"detail": "Не удалось поставить задачу в очередь."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info(
            "embed_document_task поставлена в очередь: document=%s, user=%s",
            document.id, request.user.email,
        )
        return Response(
            {
                "status": "ok",
                "detail": "Индексация запущена в фоне.",
                "document_id": str(document.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ClassifyDocumentView(APIView):
    """
    POST /api/v1/ai/classify/
    JWT + Member — ML-классификация типа документа.

    Алгоритм:
      1. Проверяем доступ: участник кабинета документа
      2. Скачиваем текст документа из S3
      3. Прогоняем через DocumentClassifier (TF-IDF + LR / keyword fallback)
      4. Сохраняем результат в Document.metadata["classification"]
      5. Возвращаем {"type", "confidence", "label"}
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ClassifyDocumentSerializer,
        summary="ML-классификация типа документа",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "example": "contract"},
                    "confidence": {"type": "number", "example": 0.95},
                    "label": {"type": "string", "example": "Договор"},
                },
            }
        },
    )
    def post(self, request):
        serializer = ClassifyDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_id = serializer.validated_data["document_id"]

        # Проверяем доступ: пользователь — участник кабинета документа
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).distinct(),
            pk=document_id,
        )

        try:
            result = AIService().classify_document(str(document.id))
        except Exception as exc:
            logger.error(
                "Ошибка classify_document (doc=%s, user=%s): %s",
                document.id, request.user.email, exc,
            )
            return Response(
                {"detail": "Ошибка классификации. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        logger.info(
            "classify_document: document=%s, user=%s, type=%s",
            document.id, request.user.email, result["type"],
        )
        return Response(result)


# ============================================================
# Чат с документом и общий ассистент
# ============================================================

class ChatWithDocumentView(APIView):
    """
    POST /api/v1/ai/chat/document/
    JWT + Member — задаёт вопрос по конкретному документу.

    Алгоритм:
      1. Проверяем доступ: участник кабинета документа
      2. Загружаем последние 10 сообщений как chat_history
      3. Сохраняем сообщение пользователя в ChatMessage
      4. Запрашиваем Gemini через RAG по чанкам документа
      5. Сохраняем ответ ассистента в ChatMessage
      6. Возвращаем {"reply": ..., "context_chunks": [...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ChatWithDocumentSerializer,
        summary="Чат с конкретным документом (RAG)",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                    "context_chunks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chunk_text": {"type": "string"},
                                "chunk_index": {"type": "integer"},
                            },
                        },
                    },
                },
            }
        },
    )
    def post(self, request):
        serializer = ChatWithDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        document_id = data["document_id"]
        message = data["message"]

        # Проверяем доступ: пользователь — участник кабинета документа
        document = get_object_or_404(
            Document.objects.filter(
                workspace__members__user=request.user
            ).select_related("workspace").distinct(),
            pk=document_id,
        )

        # Загружаем последние 10 сообщений как историю диалога
        history_qs = (
            ChatMessage.objects
            .filter(user=request.user, document=document)
            .order_by("-created_at")[:10]
        )
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in reversed(list(history_qs))
        ]

        # Сохраняем сообщение пользователя до вызова AI
        ChatMessage.objects.create(
            user=request.user,
            document=document,
            role=ChatMessage.ROLE_USER,
            content=message,
        )

        try:
            result = AIService().chat_with_document(
                document_id=str(document.id),
                message=message,
                chat_history=chat_history,
            )
        except Exception as exc:
            logger.error(
                "Ошибка chat_with_document (doc=%s, user=%s): %s",
                document.id, request.user.email, exc,
            )
            return Response(
                {"detail": "Ошибка AI-сервиса. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Сохраняем ответ ассистента
        ChatMessage.objects.create(
            user=request.user,
            document=document,
            role=ChatMessage.ROLE_ASSISTANT,
            content=result["reply"],
        )

        logger.info(
            "chat_with_document: document=%s, user=%s, chunks=%d",
            document.id, request.user.email, len(result["context_chunks"]),
        )
        return Response({
            "reply": result["reply"],
            "context_chunks": result["context_chunks"],
        })


class GeneralChatView(APIView):
    """
    POST /api/v1/ai/chat/general/
    JWT + Member — общий AI ассистент по документам кабинета.

    Алгоритм:
      1. Проверяем доступ: участник кабинета
      2. Загружаем последние 10 сообщений как chat_history
      3. Сохраняем сообщение пользователя в ChatMessage
      4. Запрашиваем Gemini через RAG по кабинету
      5. Сохраняем ответ ассистента в ChatMessage
      6. Возвращаем {"reply": ..., "sources": [...]}
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=GeneralChatSerializer,
        summary="Общий AI ассистент по документам кабинета",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "chunk_text": {"type": "string"},
                                "score": {"type": "number"},
                            },
                        },
                    },
                },
            }
        },
    )
    def post(self, request):
        serializer = GeneralChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        workspace_id = data["workspace_id"]
        message = data["message"]

        # Проверяем доступ: пользователь — участник кабинета
        is_member = WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=request.user,
        ).exists()
        if not is_member:
            return Response(
                {"detail": "У вас нет доступа к этому кабинету."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Загружаем последние 10 сообщений как историю диалога
        history_qs = (
            ChatMessage.objects
            .filter(user=request.user, workspace_id=workspace_id)
            .order_by("-created_at")[:10]
        )
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in reversed(list(history_qs))
        ]

        # Сохраняем сообщение пользователя до вызова AI
        ChatMessage.objects.create(
            user=request.user,
            workspace_id=workspace_id,
            role=ChatMessage.ROLE_USER,
            content=message,
        )

        try:
            result = AIService().general_chat(
                message=message,
                workspace_id=str(workspace_id),
                chat_history=chat_history,
            )
        except Exception as exc:
            logger.error(
                "Ошибка general_chat (workspace=%s, user=%s): %s",
                workspace_id, request.user.email, exc,
            )
            return Response(
                {"detail": "Ошибка AI-сервиса. Попробуйте позже."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Сохраняем ответ ассистента
        ChatMessage.objects.create(
            user=request.user,
            workspace_id=workspace_id,
            role=ChatMessage.ROLE_ASSISTANT,
            content=result["reply"],
        )

        logger.info(
            "general_chat: workspace=%s, user=%s, sources=%d",
            workspace_id, request.user.email, len(result["sources"]),
        )
        return Response({
            "reply": result["reply"],
            "sources": result["sources"],
        })


class ChatHistoryView(APIView):
    """
    GET /api/v1/ai/chat/history/
    JWT — последние 50 сообщений чата.

    Query params (один обязателен):
      ?document_id=uuid  — история чата с документом
      ?workspace_id=uuid — история общего чата кабинета
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="История сообщений AI-чата",
        parameters=[
            {"name": "document_id", "in": "query", "schema": {"type": "string", "format": "uuid"}, "required": False},
            {"name": "workspace_id", "in": "query", "schema": {"type": "string", "format": "uuid"}, "required": False},
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                                "created_at": {"type": "string", "format": "date-time"},
                            },
                        },
                    }
                },
            }
        },
    )
    def get(self, request):
        query_serializer = ChatHistoryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        params = query_serializer.validated_data

        qs = ChatMessage.objects.filter(user=request.user)

        if "document_id" in params:
            # Проверяем доступ к документу
            document = get_object_or_404(
                Document.objects.filter(
                    workspace__members__user=request.user
                ).distinct(),
                pk=params["document_id"],
            )
            qs = qs.filter(document=document)
        else:
            # Проверяем доступ к кабинету
            is_member = WorkspaceMember.objects.filter(
                workspace_id=params["workspace_id"],
                user=request.user,
            ).exists()
            if not is_member:
                return Response(
                    {"detail": "У вас нет доступа к этому кабинету."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            qs = qs.filter(workspace_id=params["workspace_id"])

        messages = qs.order_by("-created_at")[:50]
        # Возвращаем в хронологическом порядке
        serializer = ChatMessageSerializer(reversed(list(messages)), many=True)
        return Response({"messages": serializer.data})

"""
ГосДок — AI-сервис на базе Google Gemini (apps/ai/services.py)

Централизованный класс для всех LLM-операций:
  - generate_document:  генерация текста официального документа по описанию
  - summarize_document: резюме и ключевые тезисы документа
  - analyze_diff:       анализ изменений между двумя версиями (используется в ai_diff.py)
  - embed_document:       индексация документа в pgvector (чанки + embeddings)
  - search_documents:     семантический поиск по кабинету через cosine similarity
  - chat_with_document:   чат с конкретным документом (RAG по чанкам документа)
  - general_chat:         общий AI ассистент (RAG по кабинету + свободный режим)
  - classify_document:    ML-классификация типа документа (TF-IDF + keyword fallback)

SDK: google-genai >= 1.0  (google.genai, не google.generativeai)
"""

import logging
import os
import tempfile
from typing import Optional

from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

# Параметры чанкинга текста для RAG
_CHUNK_SIZE = 500
_CHUNK_OVERLAP = 50

# Кэш SentenceTransformer на уровне процесса.
# Модель ~80MB и грузится ~7 сек — без кэша блокирует воркер на каждом AI-запросе.
_encoder_cache = None


def _get_encoder():
    """Singleton SentenceTransformer('all-MiniLM-L6-v2') на процесс."""
    global _encoder_cache
    if _encoder_cache is None:
        from sentence_transformers import SentenceTransformer
        _encoder_cache = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder_cache

# Человекочитаемые названия типов документов для промптов
DOC_TYPE_LABELS = {
    "contract": "договор",
    "order": "приказ",
    "act": "акт",
    "invoice": "счёт-фактура",
}


class AIService:
    """
    Обёртка над Google Gemini API (google-genai >= 1.0).

    Использует genai.Client вместо глобального genai.configure().
    Один экземпляр на запрос — клиент stateless.
    """

    def __init__(self):
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")

    # ------------------------------------------------------------------
    # Внутренние хелперы
    # ------------------------------------------------------------------

    def _generate(
        self,
        system_instruction: str,
        prompt: str,
        max_output_tokens: int = 1024,
    ) -> str:
        """Однократный запрос generate_content с системным промптом."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=max_output_tokens,
            ),
        )
        return response.text.strip()

    def _chat(
        self,
        system_instruction: str,
        history: list,
        message: str,
    ) -> str:
        """
        Multi-turn chat: создаёт сессию с историей и отправляет сообщение.

        Args:
            system_instruction: системный промпт для модели
            history:            список types.Content (конвертированный chat_history)
            message:            текущее сообщение пользователя
        """
        chat = self._client.chats.create(
            model=self._model_name,
            history=history,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
            ),
        )
        response = chat.send_message(message)
        return response.text.strip()

    # ------------------------------------------------------------------
    # Генерация документа
    # ------------------------------------------------------------------

    def generate_document(self, description: str, doc_type: str) -> str:
        """
        Генерирует текст официального документа по описанию.

        Args:
            description: произвольное описание содержания документа
            doc_type:    тип документа (contract | order | act | invoice)

        Returns:
            Сгенерированный текст документа в виде строки.
        """
        label = DOC_TYPE_LABELS.get(doc_type, doc_type)

        system_instruction = (
            "Ты — юридический ассистент для государственных органов Казахстана. "
            "Составляй официальные документы на русском языке в соответствии с "
            "требованиями делопроизводства РК. Используй деловой стиль, "
            "стандартные реквизиты и формальные формулировки."
        )

        prompt = (
            f"Составь {label} на основании следующего описания:\n\n"
            f"{description}\n\n"
            "Требования:\n"
            "- Деловой официальный стиль\n"
            "- Все необходимые реквизиты документа\n"
            "- Структурированный текст с разделами\n"
            "- Только текст документа, без пояснений от себя"
        )

        return self._generate(system_instruction, prompt, max_output_tokens=2048)

    # ------------------------------------------------------------------
    # Резюме документа
    # ------------------------------------------------------------------

    def summarize_document(self, text: str) -> dict:
        """
        Создаёт краткое резюме и список ключевых тезисов документа.

        Args:
            text: извлечённый текст документа

        Returns:
            {"summary": str, "key_points": list[str]}
        """
        # Обрезаем текст до разумного предела, чтобы не превышать контекст
        truncated = text[:12_000] if len(text) > 12_000 else text

        system_instruction = (
            "Ты — аналитик официальных документов. "
            "Отвечай строго на русском языке, кратко и по делу."
        )

        prompt = (
            "Проанализируй следующий документ и верни ответ в точно таком формате:\n\n"
            "РЕЗЮМЕ:\n<одно-два предложения с сутью документа>\n\n"
            "КЛЮЧЕВЫЕ ТЕЗИСЫ:\n"
            "- <тезис 1>\n"
            "- <тезис 2>\n"
            "- <тезис 3>\n"
            "(от 3 до 7 тезисов)\n\n"
            f"Документ:\n{truncated}"
        )

        raw = self._generate(system_instruction, prompt, max_output_tokens=512)
        return _parse_summary_response(raw)

    # ------------------------------------------------------------------
    # Анализ diff между версиями (используется в ai_diff.py)
    # ------------------------------------------------------------------

    def analyze_diff(self, old_text: str, new_text: str) -> Optional[str]:
        """
        Генерирует краткое резюме изменений между двумя версиями документа.
        Вызывается из apps/documents/ai_diff.py.

        Args:
            old_text: текст предыдущей версии
            new_text: текст новой версии

        Returns:
            Строка с резюме изменений (2–3 предложения) или None при ошибке.
        """
        old_trunc = old_text[:6_000] if len(old_text) > 6_000 else old_text
        new_trunc = new_text[:6_000] if len(new_text) > 6_000 else new_text

        system_instruction = (
            "Ты — ассистент для анализа изменений в официальных документах. "
            "Отвечай на русском языке, кратко и по существу."
        )

        prompt = (
            "Сравни две версии документа и напиши краткое резюме изменений "
            "(2–3 предложения). Укажи: что добавлено, что удалено, что изменено по смыслу.\n\n"
            f"=== ПРЕДЫДУЩАЯ ВЕРСИЯ ===\n{old_trunc}\n\n"
            f"=== НОВАЯ ВЕРСИЯ ===\n{new_trunc}"
        )

        return self._generate(system_instruction, prompt, max_output_tokens=300)

    # ------------------------------------------------------------------
    # RAG: индексация документа в pgvector
    # ------------------------------------------------------------------

    def embed_document(self, document_id: str) -> None:
        """
        Читает текст документа из S3, разбивает на чанки, генерирует
        embeddings через sentence-transformers и сохраняет в DocumentEmbedding.

        Удаляет старые embeddings для документа перед созданием новых —
        идемпотентная операция (можно вызывать повторно).

        Args:
            document_id: UUID строкой для documents.Document
        """
        from apps.documents.models import Document
        from apps.ai.models import DocumentEmbedding

        try:
            document = Document.objects.select_related("workspace").get(pk=document_id)
        except Document.DoesNotExist:
            logger.error("embed_document: Document %s не найден", document_id)
            return

        text = _download_and_extract_text(document)
        if not text:
            logger.warning(
                "embed_document: текст не извлечён для документа %s (тип=%s)",
                document_id, document.file_type,
            )
            return

        chunks = _chunk_text(text, _CHUNK_SIZE, _CHUNK_OVERLAP)
        if not chunks:
            logger.warning("embed_document: нет чанков для документа %s", document_id)
            return

        # Генерируем embeddings через sentence-transformers (закэшированный энкодер)
        encoder = _get_encoder()
        vectors = encoder.encode(chunks, show_progress_bar=False, normalize_embeddings=True)

        # Удаляем старые embeddings и записываем новые одним bulk_create
        DocumentEmbedding.objects.filter(document_id=document_id).delete()

        DocumentEmbedding.objects.bulk_create([
            DocumentEmbedding(
                document=document,
                chunk_text=chunk,
                chunk_index=idx,
                embedding=vector.tolist(),
            )
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors))
        ])

        logger.info(
            "embed_document: документ '%s' проиндексирован (%d чанков)",
            document.title, len(chunks),
        )

    # ------------------------------------------------------------------
    # RAG: семантический поиск по кабинету
    # ------------------------------------------------------------------

    def search_documents(
        self,
        query: str,
        workspace_id: str,
        top_k: int = 5,
    ) -> list:
        """
        Ищет top_k наиболее релевантных чанков по cosine similarity.

        Args:
            query:        поисковый запрос
            workspace_id: UUID кабинета — фильтр по document__workspace_id
            top_k:        количество результатов

        Returns:
            list[dict] с ключами: document_id, title, chunk_text, score
        """
        from pgvector.django import CosineDistance
        from apps.ai.models import DocumentEmbedding

        encoder = _get_encoder()
        query_vector = encoder.encode(query, normalize_embeddings=True).tolist()

        results = (
            DocumentEmbedding.objects
            .annotate(distance=CosineDistance("embedding", query_vector))
            .filter(document__workspace_id=workspace_id)
            .select_related("document")
            .order_by("distance")[:top_k]
        )

        return [
            {
                "document_id": str(row.document_id),
                "title": row.document.title,
                "chunk_text": row.chunk_text,
                # cosine distance ∈ [0, 2]; similarity = 1 − distance (для нормализованных векторов)
                "score": round(max(0.0, 1.0 - float(row.distance)), 4),
            }
            for row in results
        ]

    # ------------------------------------------------------------------
    # Чат с конкретным документом (RAG по чанкам одного документа)
    # ------------------------------------------------------------------

    def chat_with_document(
        self,
        document_id: str,
        message: str,
        chat_history: list,
    ) -> dict:
        """
        Отвечает на вопрос по конкретному документу, используя RAG.

        Алгоритм:
          1. Ищет top-5 релевантных чанков документа по cosine similarity
          2. Формирует контекст из найденных чанков
          3. Отправляет в Gemini chat с историей диалога
          4. Возвращает {"reply": str, "context_chunks": list[dict]}

        Args:
            document_id:  UUID строкой для documents.Document
            message:      текущее сообщение пользователя
            chat_history: предыдущие сообщения [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            {"reply": str, "context_chunks": [{"chunk_text": str, "chunk_index": int}]}
        """
        from pgvector.django import CosineDistance
        from apps.ai.models import DocumentEmbedding

        encoder = _get_encoder()
        query_vector = encoder.encode(message, normalize_embeddings=True).tolist()

        chunk_rows = (
            DocumentEmbedding.objects
            .annotate(distance=CosineDistance("embedding", query_vector))
            .filter(document_id=document_id)
            .order_by("distance")[:5]
        )

        context_chunks = [
            {"chunk_text": row.chunk_text, "chunk_index": row.chunk_index}
            for row in chunk_rows
        ]

        context_text = "\n\n---\n\n".join(c["chunk_text"] for c in context_chunks)

        system_instruction = (
            "Ты помощник для анализа документов. Отвечай на вопросы "
            "основываясь ТОЛЬКО на тексте документа. Язык ответа: "
            "русский. Если ответа нет в документе — скажи об этом."
        )

        prompt = (
            f"Контекст из документа:\n\n{context_text}\n\n"
            f"Вопрос пользователя: {message}"
        ) if context_text else message

        reply = self._chat(
            system_instruction=system_instruction,
            history=_build_gemini_history(chat_history),
            message=prompt,
        )

        return {
            "reply": reply,
            "context_chunks": context_chunks,
        }

    # ------------------------------------------------------------------
    # ML-классификация типа документа
    # ------------------------------------------------------------------

    def classify_document(self, document_id: str) -> dict:
        """
        Классифицирует тип документа: contract / order / act / invoice /
        report / letter / other.

        Скачивает текст документа из S3, прогоняет через DocumentClassifier
        и сохраняет результат в Document.metadata["classification"].

        Args:
            document_id: UUID строкой для documents.Document

        Returns:
            {"type": str, "confidence": float, "label": str}
        """
        from apps.documents.models import Document
        from apps.ai.classifier import DocumentClassifier, TYPE_LABELS

        try:
            document = Document.objects.get(pk=document_id)
        except Document.DoesNotExist:
            logger.error("classify_document: Document %s не найден", document_id)
            return {"type": "other", "confidence": 0.0, "label": TYPE_LABELS["other"]}

        text = _download_and_extract_text(document)
        if not text:
            logger.warning(
                "classify_document: текст не извлечён для документа %s",
                document_id,
            )
            return {"type": "other", "confidence": 0.0, "label": TYPE_LABELS["other"]}

        result = DocumentClassifier().classify(text)

        metadata = document.metadata or {}
        metadata["classification"] = result
        document.metadata = metadata
        document.save(update_fields=["metadata", "updated_at"])

        logger.info(
            "classify_document: документ '%s' → %s (confidence=%.2f)",
            document.title, result["type"], result["confidence"],
        )
        return result

    # ------------------------------------------------------------------
    # Общий AI ассистент (RAG по кабинету + свободный режим)
    # ------------------------------------------------------------------

    def general_chat(
        self,
        message: str,
        workspace_id: str,
        chat_history: list,
    ) -> dict:
        """
        Общий AI ассистент с поддержкой RAG по документам кабинета.

        Алгоритм:
          1. Ищет релевантные документы через search_documents() (top 3)
          2. Если нашёл — использует их как контекст для ответа
          3. Если не нашёл — отвечает как общий ассистент без контекста
          4. Возвращает {"reply": str, "sources": list[dict]}

        Args:
            message:      текущее сообщение пользователя
            workspace_id: UUID кабинета — контекст поиска
            chat_history: предыдущие сообщения [{"role": "user"|"assistant", "content": "..."}]

        Returns:
            {"reply": str, "sources": [{"document_id", "title", "chunk_text", "score"}]}
        """
        system_instruction = (
            "Ты AI ассистент для системы документооборота ГосДок. "
            "Помогаешь пользователям работать с документами, "
            "отвечаешь на вопросы, генерируешь документы по запросу. "
            "Язык ответа: русский."
        )

        # Ищем релевантные документы через RAG
        sources = self.search_documents(message, workspace_id, top_k=3)

        if sources:
            context_parts = [
                f"[{s['title']}]\n{s['chunk_text']}"
                for s in sources
            ]
            context_text = "\n\n---\n\n".join(context_parts)
            prompt = (
                f"Контекст из документов кабинета:\n\n{context_text}\n\n"
                f"Запрос пользователя: {message}"
            )
        else:
            prompt = message

        reply = self._chat(
            system_instruction=system_instruction,
            history=_build_gemini_history(chat_history),
            message=prompt,
        )

        return {
            "reply": reply,
            "sources": sources,
        }


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------

def _build_gemini_history(chat_history: list) -> list:
    """
    Конвертирует chat_history из формата {"role": "user"|"assistant", "content": "..."}
    в список types.Content для google-genai >= 1.0.

    Gemini использует role="model" вместо "assistant".
    """
    result = []
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        result.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])],
            )
        )
    return result


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    """
    Разбивает текст на перекрывающиеся чанки.

    Args:
        text:       исходный текст
        chunk_size: максимальный размер чанка в символах
        overlap:    перекрытие между соседними чанками в символах

    Returns:
        Список непустых строк-чанков.
    """
    chunks = []
    stride = chunk_size - overlap
    start = 0
    while start < len(text):
        chunk = text[start: start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += stride
    return chunks


def _download_and_extract_text(document) -> str:
    """
    Скачивает файл документа из S3 во временный файл и извлекает текст.
    Возвращает пустую строку при ошибке или отсутствии S3.
    """
    from apps.documents.ai_diff import extract_text

    file_type = document.file_type.lower()
    if file_type not in {"pdf", "docx", "odt"}:
        logger.info(
            "_download_and_extract_text: тип '%s' не поддерживается (doc=%s)",
            file_type, document.id,
        )
        return ""

    if not settings.AWS_ACCESS_KEY_ID:
        logger.warning(
            "_download_and_extract_text: S3 не настроен — пропускаем (doc=%s)",
            document.id,
        )
        return ""

    from apps.documents.storage import get_s3_client

    tmp_path = None
    try:
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3 = get_s3_client()

        fd, tmp_path = tempfile.mkstemp(suffix=f".{file_type}")
        os.close(fd)

        s3.download_file(bucket, document.storage_key, tmp_path)
        return extract_text(tmp_path, file_type)

    except Exception as exc:
        logger.error(
            "_download_and_extract_text: ошибка S3/извлечения для doc=%s: %s",
            document.id, exc,
        )
        return ""

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _parse_summary_response(text: str) -> dict:
    """
    Разбирает ответ Gemini в формате РЕЗЮМЕ / КЛЮЧЕВЫЕ ТЕЗИСЫ.
    Возвращает {"summary": str, "key_points": list[str]}.
    При ошибке разбора — возвращает весь текст как summary.
    """
    summary = ""
    key_points = []

    try:
        parts = text.split("КЛЮЧЕВЫЕ ТЕЗИСЫ:")
        if len(parts) == 2:
            summary_part, points_part = parts
            summary = summary_part.replace("РЕЗЮМЕ:", "").strip()
            for line in points_part.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    key_points.append(line[2:].strip())
                elif line:
                    key_points.append(line)
        else:
            summary = text
    except Exception:
        summary = text

    return {"summary": summary, "key_points": key_points}


def get_ai_service() -> AIService:
    """
    Фабрика: возвращает экземпляр AIService.
    Бросает RuntimeError, если GEMINI_API_KEY не задан.
    """
    if not getattr(settings, "GEMINI_API_KEY", ""):
        raise RuntimeError(
            "GEMINI_API_KEY не настроен. "
            "Добавьте переменную окружения и перезапустите сервис."
        )
    return AIService()

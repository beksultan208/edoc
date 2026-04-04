"""
ГосДок — Celery-задачи для документов (apps/documents/tasks.py)
Раздел 2.6 ТЗ — AI-детектор изменений.
Задача 8 этапа 3: AI-diff запускается асинхронно после загрузки новой версии.

Алгоритм:
  1. Скачиваем текущую версию из S3 во временный файл
  2. Вычисляем SHA-256 и обновляем checksum (было "pending")
  3. Если версия > 1 и тип поддерживается (PDF/DOCX/ODT):
       — скачиваем предыдущую версию
       — запускаем analyze_document_diff()
       — сохраняем ai_diff_summary (JSONB) и ai_changes_detected
"""

import hashlib
import logging
import os
import tempfile

from celery import shared_task

logger = logging.getLogger(__name__)

# Типы файлов, поддерживающие текстовую экстракцию (раздел 2.6 ТЗ)
SUPPORTED_DIFF_TYPES = {"pdf", "docx", "odt"}


@shared_task(
    name="apps.documents.tasks.analyze_version_diff_task",
    bind=True,
    max_retries=3,
    default_retry_delay=120,  # повтор через 2 мин при сбое S3 / OpenAI
)
def analyze_version_diff_task(self, version_id: str):
    """
    Асинхронный AI-анализ изменений между двумя версиями документа.

    Вызывается из DocumentVersionCreateView (новая версия) и из
    DocumentListCreateView (первая версия — только SHA-256, без diff).

    Args:
        version_id: UUID строкой для DocumentVersion.
    """
    from django.conf import settings
    from botocore.exceptions import ClientError

    from apps.documents.ai_diff import analyze_document_diff
    from apps.documents.models import DocumentVersion
    from apps.documents.storage import get_s3_client

    # ----------------------------------------------------------------
    # Загружаем запись DocumentVersion
    # ----------------------------------------------------------------
    try:
        version = DocumentVersion.objects.select_related("document").get(pk=version_id)
    except DocumentVersion.DoesNotExist:
        logger.error("DocumentVersion %s не найдена — задача прервана", version_id)
        return  # не повторяем: объект не существует

    document = version.document
    file_type = document.file_type.lower()

    # ----------------------------------------------------------------
    # Dev-режим: S3 не настроен — пропускаем загрузку
    # ----------------------------------------------------------------
    if not settings.AWS_ACCESS_KEY_ID:
        logger.warning(
            "S3 не настроен (AWS_ACCESS_KEY_ID пуст) — "
            "пропускаем SHA-256 и AI-анализ для версии %s",
            version_id,
        )
        version.checksum = "s3-not-configured"
        version.save(update_fields=["checksum"])
        return

    bucket = settings.AWS_STORAGE_BUCKET_NAME
    s3_client = get_s3_client()

    new_tmp_path = None
    old_tmp_path = None

    try:
        # ----------------------------------------------------------------
        # Шаг 1: скачиваем текущую версию во временный файл
        # ----------------------------------------------------------------
        fd, new_tmp_path = tempfile.mkstemp(suffix=f".{file_type}")
        os.close(fd)  # boto3 откроет сам

        logger.info(
            "Скачиваем версию %d документа '%s' из S3: %s",
            version.version_number, document.title, version.storage_key,
        )
        s3_client.download_file(bucket, version.storage_key, new_tmp_path)

        # ----------------------------------------------------------------
        # Шаг 2: вычисляем SHA-256 checksum (раздел 2.5 ТЗ)
        # ----------------------------------------------------------------
        sha256 = hashlib.sha256()
        with open(new_tmp_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()

        version.checksum = checksum
        version.save(update_fields=["checksum"])

        logger.info(
            "SHA-256 обновлён: версия %d, документ '%s', checksum=%s…",
            version.version_number, document.title, checksum[:16],
        )

        # ----------------------------------------------------------------
        # Шаг 3: AI-анализ — только для версий > 1 и поддерживаемых типов
        # ----------------------------------------------------------------
        if version.version_number <= 1:
            # Первая версия — предыдущей нет, анализ не нужен
            return

        if file_type not in SUPPORTED_DIFF_TYPES:
            logger.info(
                "Тип '%s' не поддерживает AI-анализ (поддерживаются: %s)",
                file_type, ", ".join(SUPPORTED_DIFF_TYPES),
            )
            return

        # Предыдущая версия
        prev_version = (
            DocumentVersion.objects
            .filter(
                document=document,
                version_number=version.version_number - 1,
            )
            .first()
        )

        if not prev_version:
            logger.warning(
                "Предыдущая версия %d не найдена для документа '%s' — diff пропущен",
                version.version_number - 1, document.title,
            )
            return

        # Скачиваем предыдущую версию
        fd, old_tmp_path = tempfile.mkstemp(suffix=f".{file_type}")
        os.close(fd)

        logger.info(
            "Скачиваем предыдущую версию %d документа '%s' из S3: %s",
            prev_version.version_number, document.title, prev_version.storage_key,
        )
        s3_client.download_file(bucket, prev_version.storage_key, old_tmp_path)

        # ----------------------------------------------------------------
        # Шаг 4: запускаем AI-анализ изменений (раздел 2.6 ТЗ)
        # ----------------------------------------------------------------
        diff_result = analyze_document_diff(old_tmp_path, new_tmp_path, file_type)

        version.ai_changes_detected = diff_result.get("ai_changes_detected", False)
        version.ai_diff_summary = diff_result
        version.save(update_fields=["ai_changes_detected", "ai_diff_summary"])

        logger.info(
            "AI-анализ завершён: версия %d, документ '%s', "
            "changes=%s, +%d/-%d строк",
            version.version_number, document.title,
            version.ai_changes_detected,
            diff_result.get("additions_count", 0),
            diff_result.get("deletions_count", 0),
        )

    except ClientError as exc:
        # Ошибки S3 — повторяем задачу
        logger.error(
            "Ошибка S3 при анализе версии %s: %s",
            version_id, exc,
        )
        raise self.retry(exc=exc)

    except Exception as exc:
        # Прочие ошибки (OpenAI, PyMuPDF, etc.) — повторяем
        logger.error(
            "Ошибка AI-анализа для версии %s: %s",
            version_id, exc,
        )
        raise self.retry(exc=exc)

    finally:
        # Гарантированно удаляем временные файлы
        for tmp_path in (new_tmp_path, old_tmp_path):
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError as e:
                    logger.warning("Не удалось удалить временный файл %s: %s", tmp_path, e)

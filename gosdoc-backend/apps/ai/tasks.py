"""
ГосДок — Celery-задачи и сигналы AI-сервиса (apps/ai/tasks.py)

Задачи:
  embed_document_task(document_id)    — индексирует документ в pgvector
  classify_document_task(document_id) — ML-классификация типа документа

Сигналы:
  on_document_version_post_save — запускает embed_document_task → classify_document_task
    при создании новой DocumentVersion (post_save, created=True)
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.ai.tasks.embed_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # повтор через 1 мин при сбое S3 / sentence-transformers
)
def embed_document_task(self, document_id: str):
    """
    Асинхронная индексация документа в pgvector.

    Скачивает файл из S3, разбивает на чанки, генерирует embeddings
    через sentence-transformers (all-MiniLM-L6-v2) и сохраняет
    в DocumentEmbedding. Идемпотентно: старые embeddings удаляются.

    После успешной индексации запускает classify_document_task.

    Args:
        document_id: UUID строкой для documents.Document
    """
    try:
        from apps.ai.services import AIService
        AIService().embed_document(document_id)
    except Exception as exc:
        logger.error(
            "embed_document_task: ошибка для document=%s: %s",
            document_id, exc,
        )
        raise self.retry(exc=exc)

    # Запускаем классификацию отдельной задачей — её сбой не должен ломать embed.
    try:
        classify_document_task.delay(document_id)
    except Exception as exc:
        logger.warning(
            "embed_document_task: не удалось поставить classify_document_task "
            "в очередь для document=%s: %s",
            document_id, exc,
        )


@shared_task(
    name="apps.ai.tasks.classify_document_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def classify_document_task(self, document_id: str):
    """
    Асинхронная ML-классификация типа документа.
    Сохраняет результат в Document.metadata["classification"].
    """
    try:
        from apps.ai.services import AIService
        AIService().classify_document(document_id)
    except Exception as exc:
        logger.error(
            "classify_document_task: ошибка для document=%s: %s",
            document_id, exc,
        )
        raise self.retry(exc=exc)


# ------------------------------------------------------------------
# Обработчик сигнала: новая версия документа → переиндексация
# ------------------------------------------------------------------

def on_document_version_post_save(sender, instance, created, **kwargs):
    """
    Запускает embed_document_task при создании новой DocumentVersion.
    Подключается в AiConfig.ready() через post_save.connect().
    """
    if not created:
        return

    document_id = str(instance.document_id)
    logger.info(
        "post_save DocumentVersion: запускаем embed_document_task(document=%s)",
        document_id,
    )

    try:
        embed_document_task.delay(document_id)
    except Exception as exc:
        # Celery недоступен (dev без брокера) — не ломаем основной flow
        logger.warning(
            "on_document_version_post_save: не удалось поставить задачу в очередь "
            "для document=%s: %s",
            document_id, exc,
        )

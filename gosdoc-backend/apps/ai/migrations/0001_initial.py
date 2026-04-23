"""
ГосДок — Начальная миграция AI-приложения (apps/ai/migrations/0001_initial.py)

Порядок операций:
  1. CREATE EXTENSION IF NOT EXISTS vector  — активирует pgvector в PostgreSQL
  2. CreateModel DocumentEmbedding          — таблица с VectorField(384)
"""

import uuid

import django.db.models.deletion
import pgvector.django
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # Ссылаемся на последнюю миграцию documents (ForeignKey → Document)
        ("documents", "0002_documentauditlog"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Шаг 1: активируем расширение pgvector в PostgreSQL.
        # reverse_sql пустой — расширение не удаляем при откате миграции,
        # т.к. другие таблицы могут его использовать.
        # ----------------------------------------------------------------
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql=migrations.RunSQL.noop,
        ),

        # ----------------------------------------------------------------
        # Шаг 2: создаём таблицу DocumentEmbedding с VectorField(384)
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name="DocumentEmbedding",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("chunk_text", models.TextField(verbose_name="Текст фрагмента")),
                (
                    "chunk_index",
                    models.IntegerField(verbose_name="Порядковый номер фрагмента"),
                ),
                (
                    "embedding",
                    pgvector.django.VectorField(
                        dimensions=384,
                        verbose_name="Векторное представление",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Создан",
                    ),
                ),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embeddings",
                        to="documents.document",
                        verbose_name="Документ",
                    ),
                ),
            ],
            options={
                "verbose_name": "Векторное представление документа",
                "verbose_name_plural": "Векторные представления документов",
                "ordering": ["document", "chunk_index"],
            },
        ),

        # ----------------------------------------------------------------
        # Шаг 3: индекс для быстрого поиска по документу + порядку чанка
        # ----------------------------------------------------------------
        migrations.AddIndex(
            model_name="documentembedding",
            index=models.Index(
                fields=["document", "chunk_index"],
                name="ai_docembed_doc_chunk_idx",
            ),
        ),
    ]

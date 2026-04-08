import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Создаёт таблицы documents, document_versions, comments."""

    initial = True
    dependencies = [
        ("workspaces", "0001_workspace_organization_nullable"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ---- Document (без current_version FK — добавим после DocumentVersion) ----
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255, verbose_name="Название документа")),
                ("file_type", models.CharField(max_length=20, verbose_name="Тип файла")),
                ("storage_key", models.TextField(verbose_name="Ключ S3")),
                ("storage_url", models.TextField(blank=True, null=True, verbose_name="URL файла")),
                ("status", models.CharField(
                    choices=[("draft", "Черновик"), ("review", "На согласовании"), ("signed", "Подписан"), ("archived", "Архив")],
                    db_index=True, default="draft", max_length=20, verbose_name="Статус",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Дата обновления")),
                ("workspace", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="documents", to="workspaces.workspace", verbose_name="Кабинет",
                )),
                ("uploaded_by", models.ForeignKey(
                    db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="uploaded_documents", to=settings.AUTH_USER_MODEL, verbose_name="Загрузил",
                )),
            ],
            options={"verbose_name": "Документ", "verbose_name_plural": "Документы", "db_table": "documents"},
        ),
        # ---- DocumentVersion ----
        migrations.CreateModel(
            name="DocumentVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("version_number", models.IntegerField(verbose_name="Номер версии")),
                ("storage_key", models.TextField(verbose_name="Ключ S3")),
                ("checksum", models.CharField(max_length=64, verbose_name="SHA-256")),
                ("ai_changes_detected", models.BooleanField(default=False, verbose_name="AI: изменения обнаружены")),
                ("ai_diff_summary", models.JSONField(blank=True, null=True, verbose_name="AI: описание изменений")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("document", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="versions", to="documents.document", verbose_name="Документ",
                )),
                ("created_by", models.ForeignKey(
                    db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_versions", to=settings.AUTH_USER_MODEL, verbose_name="Создал",
                )),
            ],
            options={
                "verbose_name": "Версия документа", "verbose_name_plural": "Версии документа",
                "db_table": "document_versions", "ordering": ["-version_number"],
            },
        ),
        # ---- current_version FK on Document (after DocumentVersion exists) ----
        migrations.AddField(
            model_name="document",
            name="current_version",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="current_for_documents", to="documents.documentversion",
                verbose_name="Текущая версия",
            ),
        ),
        # ---- Comment ----
        migrations.CreateModel(
            name="Comment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("content", models.TextField(verbose_name="Текст комментария")),
                ("is_resolved", models.BooleanField(default=False, verbose_name="Закрыт")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("document", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="comments", to="documents.document", verbose_name="Документ",
                )),
                ("author", models.ForeignKey(
                    db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="comments", to=settings.AUTH_USER_MODEL, verbose_name="Автор",
                )),
                ("parent", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="replies", to="documents.comment", verbose_name="Родительский комментарий",
                )),
            ],
            options={"verbose_name": "Комментарий", "verbose_name_plural": "Комментарии", "db_table": "comments", "ordering": ["created_at"]},
        ),
        # ---- Indexes ----
        migrations.AddIndex(model_name="document", index=models.Index(fields=["workspace"], name="documents_workspace_idx")),
        migrations.AddIndex(model_name="document", index=models.Index(fields=["status"], name="documents_status_idx")),
        migrations.AddIndex(model_name="document", index=models.Index(fields=["uploaded_by"], name="documents_uploaded_by_idx")),
        migrations.AddIndex(model_name="document", index=models.Index(fields=["created_at"], name="documents_created_at_idx")),
        migrations.AddIndex(model_name="documentversion", index=models.Index(fields=["document"], name="docver_document_idx")),
        migrations.AddIndex(model_name="documentversion", index=models.Index(fields=["created_by"], name="docver_created_by_idx")),
        migrations.AddIndex(model_name="documentversion", index=models.Index(fields=["created_at"], name="docver_created_at_idx")),
        migrations.AlterUniqueTogether(name="documentversion", unique_together={("document", "version_number")}),
        migrations.AddIndex(model_name="comment", index=models.Index(fields=["document"], name="comments_document_idx")),
        migrations.AddIndex(model_name="comment", index=models.Index(fields=["author"], name="comments_author_idx")),
        migrations.AddIndex(model_name="comment", index=models.Index(fields=["parent"], name="comments_parent_idx")),
    ]

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Создаёт таблицу tasks."""

    initial = True
    dependencies = [
        ("workspaces", "0001_workspace_organization_nullable"),
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("step_order", models.IntegerField(verbose_name="Порядок шага")),
                ("title", models.CharField(max_length=255, verbose_name="Название задачи")),
                ("status", models.CharField(
                    choices=[("pending", "Ожидает"), ("in_progress", "В работе"), ("done", "Завершена"), ("skipped", "Пропущена")],
                    db_index=True, default="pending", max_length=20, verbose_name="Статус",
                )),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="Срок выполнения")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="Дата завершения")),
                ("workspace", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="tasks", to="workspaces.workspace", verbose_name="Кабинет",
                )),
                ("document", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="tasks", to="documents.document", verbose_name="Документ",
                )),
                ("assigned_to", models.ForeignKey(
                    db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="assigned_tasks", to=settings.AUTH_USER_MODEL, verbose_name="Исполнитель",
                )),
            ],
            options={"verbose_name": "Задача", "verbose_name_plural": "Задачи", "db_table": "tasks", "ordering": ["step_order"]},
        ),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["workspace"], name="tasks_workspace_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["document"], name="tasks_document_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["assigned_to"], name="tasks_assigned_to_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["status"], name="tasks_status_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["step_order"], name="tasks_step_order_idx")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["due_date"], name="tasks_due_date_idx")),
    ]

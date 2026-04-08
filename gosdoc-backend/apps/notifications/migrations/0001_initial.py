import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Создаёт таблицу notifications."""

    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("type", models.CharField(
                    choices=[
                        ("task_assigned", "Задача назначена"), ("step_completed", "Шаг завершён"),
                        ("document_signed", "Документ подписан"), ("new_comment", "Новый комментарий"),
                        ("deadline_approaching", "Срок истекает"), ("document_rejected", "Документ отклонён"),
                    ],
                    db_index=True, max_length=50, verbose_name="Тип уведомления",
                )),
                ("title", models.CharField(max_length=255, verbose_name="Заголовок")),
                ("message", models.TextField(blank=True, null=True, verbose_name="Текст")),
                ("entity_type", models.CharField(blank=True, max_length=50, null=True, verbose_name="Тип сущности")),
                ("entity_id", models.UUIDField(blank=True, null=True, verbose_name="ID сущности")),
                ("is_read", models.BooleanField(db_index=True, default=False, verbose_name="Прочитано")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
                ("user", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications", to=settings.AUTH_USER_MODEL, verbose_name="Пользователь",
                )),
            ],
            options={
                "verbose_name": "Уведомление", "verbose_name_plural": "Уведомления",
                "db_table": "notifications", "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(model_name="notification", index=models.Index(fields=["user"], name="notif_user_idx")),
        migrations.AddIndex(model_name="notification", index=models.Index(fields=["is_read"], name="notif_is_read_idx")),
        migrations.AddIndex(model_name="notification", index=models.Index(fields=["type"], name="notif_type_idx")),
        migrations.AddIndex(model_name="notification", index=models.Index(fields=["created_at"], name="notif_created_at_idx")),
    ]

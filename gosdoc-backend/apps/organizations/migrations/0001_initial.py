import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Создаёт таблицу organizations БЕЗ owner FK (circular dependency с users).
    Owner FK добавляется в 0002 после создания users.
    """

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, verbose_name="Название организации")),
                ("type", models.CharField(choices=[("individual", "Индивидуальный"), ("corporate", "Корпоративный")], max_length=20, verbose_name="Тип")),
                ("inn", models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name="ИНН")),
                ("address", models.TextField(blank=True, null=True, verbose_name="Адрес")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")),
            ],
            options={
                "verbose_name": "Организация",
                "verbose_name_plural": "Организации",
                "db_table": "organizations",
            },
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(fields=["type"], name="organizatio_type_idx"),
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(fields=["inn"], name="organizatio_inn_idx"),
        ),
    ]

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Создаёт таблицу signatures."""

    initial = True
    dependencies = [
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Signature",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("signature_data", models.TextField(verbose_name="Данные подписи")),
                ("certificate_id", models.CharField(blank=True, max_length=255, null=True, verbose_name="ID сертификата КЭП")),
                ("signed_at", models.DateTimeField(auto_now_add=True, verbose_name="Время подписания")),
                ("ip_address", models.GenericIPAddressField(verbose_name="IP-адрес")),
                ("is_valid", models.BooleanField(default=True, verbose_name="Действительна")),
                ("document", models.ForeignKey(
                    db_index=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name="signatures", to="documents.document", verbose_name="Документ",
                )),
                ("user", models.ForeignKey(
                    db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="signatures", to=settings.AUTH_USER_MODEL, verbose_name="Подписант",
                )),
            ],
            options={"verbose_name": "Подпись", "verbose_name_plural": "Подписи", "db_table": "signatures"},
        ),
        migrations.AddIndex(model_name="signature", index=models.Index(fields=["document"], name="signatures_document_idx")),
        migrations.AddIndex(model_name="signature", index=models.Index(fields=["user"], name="signatures_user_idx")),
        migrations.AddIndex(model_name="signature", index=models.Index(fields=["signed_at"], name="signatures_signed_at_idx")),
    ]

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Добавляет owner FK к Organization после создания User."""

    dependencies = [
        ("organizations", "0001_initial"),
        ("users", "0001_email_verification_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_organizations",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Владелец",
                db_index=True,
            ),
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(fields=["owner"], name="organizatio_owner_idx"),
        ),
    ]

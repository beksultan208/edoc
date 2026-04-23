# Generated for ML classification (apps/ai/classifier.py)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_rename_comments_document_idx_comments_documen_6e3d29_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Произвольные метаданные документа (классификация AI и т.п.)',
                verbose_name='Метаданные',
            ),
        ),
    ]

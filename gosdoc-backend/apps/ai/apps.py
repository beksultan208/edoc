from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai"
    verbose_name = "AI-сервис"

    def ready(self):
        """Подключаем сигнал post_save на DocumentVersion при старте Django."""
        from django.db.models.signals import post_save
        from apps.documents.models import DocumentVersion
        from apps.ai.tasks import on_document_version_post_save

        post_save.connect(
            on_document_version_post_save,
            sender=DocumentVersion,
            dispatch_uid="ai.embed_on_new_version",
        )

from django.contrib import admin
from .models import Document, DocumentVersion, Comment


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "file_type", "status", "workspace", "uploaded_by", "created_at"]
    list_filter = ["status", "file_type"]
    search_fields = ["title"]
    raw_id_fields = ["workspace", "uploaded_by", "current_version"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_number", "checksum", "ai_changes_detected", "created_by", "created_at"]
    list_filter = ["ai_changes_detected"]
    raw_id_fields = ["document", "created_by"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["document", "author", "is_resolved", "created_at"]
    list_filter = ["is_resolved"]
    raw_id_fields = ["document", "author", "parent"]

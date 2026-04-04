from django.contrib import admin
from .models import Workspace, WorkspaceMember


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "organization", "status", "created_by", "created_at"]
    list_filter = ["type", "status"]
    search_fields = ["title"]
    raw_id_fields = ["organization", "created_by"]


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ["workspace", "user", "role", "step_order", "joined_at"]
    list_filter = ["role"]
    raw_id_fields = ["workspace", "user"]

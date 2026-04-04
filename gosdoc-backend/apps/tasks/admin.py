from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "document", "assigned_to", "step_order", "status", "due_date"]
    list_filter = ["status"]
    search_fields = ["title"]
    raw_id_fields = ["workspace", "document", "assigned_to"]

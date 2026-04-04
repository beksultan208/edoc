"""
ГосДок — Сериализаторы задач (apps/tasks/serializers.py)
"""

from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.full_name", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "workspace", "document", "document_title",
            "assigned_to", "assigned_to_name",
            "step_order", "title", "status", "due_date", "completed_at",
        ]
        read_only_fields = ["id", "completed_at"]

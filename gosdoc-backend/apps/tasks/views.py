"""
ГосДок — Views задач (apps/tasks/views.py)
Раздел 4.6 ТЗ
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Task
from .serializers import TaskSerializer
from .workflow import activate_next_task

logger = logging.getLogger(__name__)


class TaskListView(generics.ListAPIView):
    """GET /api/v1/tasks/ — список задач пользователя"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer
    filterset_fields = ["status", "workspace"]

    def get_queryset(self):
        return Task.objects.filter(
            assigned_to=self.request.user
        ).select_related("workspace", "document", "assigned_to")


class TaskDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/tasks/{id}/ — JWT + Assignee
    PATCH /api/v1/tasks/{id}/ — JWT + Owner
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            workspace__members__user=self.request.user
        ).distinct()


class TaskCompleteView(APIView):
    """POST /api/v1/tasks/{id}/complete/ — JWT + Assignee"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(
            Task.objects.filter(workspace__members__user=request.user).distinct(),
            pk=pk,
        )

        if task.assigned_to != request.user:
            return Response(
                {"detail": "Только исполнитель может завершить задачу."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if task.status != Task.TaskStatus.IN_PROGRESS:
            return Response(
                {"detail": "Задача не в статусе 'В работе'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.status = Task.TaskStatus.DONE
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "completed_at"])

        # Активируем следующий шаг workflow
        next_task = activate_next_task(task)
        logger.info("Задача завершена: %s", task.title)

        return Response({
            "detail": "Задача завершена.",
            "next_task": TaskSerializer(next_task).data if next_task else None,
        })


class TaskSkipView(APIView):
    """POST /api/v1/tasks/{id}/skip/ — JWT + Owner"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(
            Task.objects.filter(workspace__members__user=request.user).distinct(),
            pk=pk,
        )

        is_owner = task.workspace.members.filter(
            user=request.user, role="owner"
        ).exists()
        is_creator = task.workspace.created_by_id == request.user.pk
        if not is_owner and not is_creator and not request.user.is_staff:
            return Response({"detail": "Только владелец может пропускать задачи."}, status=status.HTTP_403_FORBIDDEN)

        task.status = Task.TaskStatus.SKIPPED
        task.save(update_fields=["status"])

        # Активируем следующий шаг
        activate_next_task(task)
        return Response({"detail": "Задача пропущена."})

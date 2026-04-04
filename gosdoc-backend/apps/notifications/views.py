"""
ГосДок — Views уведомлений (apps/notifications/views.py)
Раздел 4.9 ТЗ
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """GET /api/v1/notifications/ — список уведомлений пользователя"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    filterset_fields = ["is_read", "type"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationReadView(APIView):
    """POST /api/v1/notifications/{id}/read/ — отметить как прочитанное"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Уведомление не найдено."}, status=status.HTTP_404_NOT_FOUND)

        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"detail": "Отмечено как прочитанное."})


class NotificationReadAllView(APIView):
    """POST /api/v1/notifications/read-all/ — отметить все как прочитанные"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": f"Отмечено {count} уведомлений."})

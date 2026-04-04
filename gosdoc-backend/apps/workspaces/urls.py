"""
ГосДок — URL кабинетов (apps/workspaces/urls.py)
Раздел 4.4 ТЗ

Маршруты:
  GET    /workspaces/                        — список кабинетов
  POST   /workspaces/                        — создать кабинет
  GET    /workspaces/{id}/                   — детали
  PATCH  /workspaces/{id}/                   — обновить
  DELETE /workspaces/{id}/                   — закрыть
  GET    /workspaces/{id}/members/           — список участников
  POST   /workspaces/{id}/members/           — добавить участника
  PATCH  /workspaces/{id}/members/{uid}/     — изменить роль/step_order
  DELETE /workspaces/{id}/members/{uid}/     — удалить участника
"""

from django.urls import path

from .views import (
    WorkspaceDetailView,
    WorkspaceListCreateView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListCreateView,
)

urlpatterns = [
    # Кабинеты
    path("", WorkspaceListCreateView.as_view(), name="workspace-list"),
    path("<uuid:pk>/", WorkspaceDetailView.as_view(), name="workspace-detail"),

    # Участники (POST — добавить, GET — список на том же URL)
    path(
        "<uuid:pk>/members/",
        WorkspaceMemberListCreateView.as_view(),
        name="workspace-members",
    ),
    # Конкретный участник по user UUID
    path(
        "<uuid:pk>/members/<uuid:uid>/",
        WorkspaceMemberDetailView.as_view(),
        name="workspace-member-detail",
    ),
]

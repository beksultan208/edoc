"""
ГосДок — URL пользователей (apps/users/urls/users.py)
Раздел 4.2 ТЗ
"""

from django.urls import path

from apps.users.views import UserDetailView, UserListView, UserMeView

urlpatterns = [
    # GET  /api/v1/users/     — список (только Admin)
    path("", UserListView.as_view(), name="user-list"),
    # GET/PATCH /api/v1/users/me/
    path("me/", UserMeView.as_view(), name="user-me"),
    # GET/PATCH/DELETE /api/v1/users/{id}/
    path("<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
]

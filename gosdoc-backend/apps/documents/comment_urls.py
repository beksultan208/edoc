"""
ГосДок — URL комментариев (standalone, раздел 4.8 ТЗ)
"""

from django.urls import path

from .views import CommentDetailView, CommentResolveView

urlpatterns = [
    path("<uuid:pk>/", CommentDetailView.as_view(), name="comment-detail"),
    path("<uuid:pk>/resolve/", CommentResolveView.as_view(), name="comment-resolve"),
]

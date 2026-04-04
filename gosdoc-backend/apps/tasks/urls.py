from django.urls import path
from .views import TaskListView, TaskDetailView, TaskCompleteView, TaskSkipView

urlpatterns = [
    path("", TaskListView.as_view(), name="task-list"),
    path("<uuid:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("<uuid:pk>/complete/", TaskCompleteView.as_view(), name="task-complete"),
    path("<uuid:pk>/skip/", TaskSkipView.as_view(), name="task-skip"),
]

from django.urls import path
from .views import TaskListView, TaskDetailView
from apps.users.views import submit_file_for_processing

urlpatterns = [
    path("submit/", submit_file_for_processing, name="submit_file"),
    path("tasks/", TaskListView.as_view(), name="task_list"),
    path("tasks/<uuid:pk>/", TaskDetailView.as_view(), name="task_detail"),
]

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from .models import ProcessingTask
from .serializers import ProcessingTaskSerializer


class TaskListView(generics.ListAPIView):
    """
    GET /auth/files/tasks/
    Return all processing tasks for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessingTaskSerializer

    def get_queryset(self):
        return ProcessingTask.objects.filter(user=self.request.user)


class TaskDetailView(generics.RetrieveAPIView):
    """
    GET /auth/files/tasks/<uuid>/
    Return a single task's status and result.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ProcessingTaskSerializer

    def get_queryset(self):
        return ProcessingTask.objects.filter(user=self.request.user)

from rest_framework import serializers
from .models import ProcessingTask


class ProcessingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingTask
        fields = (
            "id", "filename", "file_size", "status",
            "task_type", "result", "error_message",
            "created_at", "updated_at",
        )
        read_only_fields = fields

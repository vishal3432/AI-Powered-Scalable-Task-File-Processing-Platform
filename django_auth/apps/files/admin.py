from django.contrib import admin
from .models import ProcessingTask


@admin.register(ProcessingTask)
class ProcessingTaskAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "status", "task_type", "file_size", "created_at")
    list_filter = ("status", "task_type")
    search_fields = ("filename", "user__email")
    readonly_fields = ("id", "created_at", "updated_at", "result", "error_message")
    ordering = ("-created_at",)

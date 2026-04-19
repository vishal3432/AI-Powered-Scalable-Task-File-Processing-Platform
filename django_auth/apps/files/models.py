from django.db import models
from django.conf import settings
import uuid


class ProcessingTask(models.Model):
    """
    Mirrors the processing_tasks table that FastAPI writes to.
    Django uses this for the admin panel and user history.
    """
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    TASK_TYPES = [
        ("summarize", "Summarize"),
        ("extract_keywords", "Extract Keywords"),
        ("sentiment", "Sentiment Analysis"),
        ("translate", "Translate"),
        ("qa", "Question & Answer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    task_type = models.CharField(max_length=50, choices=TASK_TYPES, default="summarize")
    result = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "processing_tasks"
        ordering = ["-created_at"]
        managed = False  # FastAPI also writes to this table; avoid migration conflicts

    def __str__(self):
        return f"{self.filename} [{self.status}] - {self.user.email}"

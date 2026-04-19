"""
Pydantic Schemas for FastAPI Request/Response Models
"""
from pydantic import BaseModel, UUID4
from typing import Optional, Literal
from datetime import datetime


class TaskSubmitResponse(BaseModel):
    """Response returned immediately (202 Accepted) when a task is submitted."""
    task_id: UUID4
    status: str = "pending"
    message: str = "File accepted. Processing in background."
    filename: str
    task_type: str


class TaskStatusResponse(BaseModel):
    """Full task status including result when completed."""
    task_id: UUID4
    status: Literal["pending", "processing", "completed", "failed"]
    filename: str
    task_type: str
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str


class WebSocketMessage(BaseModel):
    """Message pushed via WebSocket when a task completes."""
    event: Literal["task_completed", "task_failed", "task_started", "ping"]
    task_id: Optional[str] = None
    filename: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None

"""
FastAPI Processing Router
Handles: File upload, background AI processing, task status, WebSocket alerts
"""
import os
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional

import aiofiles
from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    HTTPException, UploadFile, status, WebSocket, WebSocketDisconnect
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from auth import get_current_user, TokenPayload
from database import get_db, ProcessingTaskDB
from websocket_manager import manager
from services.ai_service import run_full_pipeline
from models.schemas import TaskSubmitResponse, TaskStatusResponse
from config import settings

router = APIRouter(prefix="/process", tags=["🤖 AI Processing"])


# ─────────────────────────────────────────
# Background Task Worker
# ─────────────────────────────────────────
async def _background_process_file(
    task_id: str,
    file_path: str,
    filename: str,
    task_type: str,
    user_id: int,
):
    """
    This runs in FastAPI's internal thread pool AFTER the 202 is returned.
    Steps:
      1. Update status → 'processing'
      2. Extract text from file
      3. Call OpenAI API
      4. Write result to PostgreSQL
      5. Push WebSocket alert to user
    """
    async with AsyncSession(
        bind=(await _get_engine()),
        expire_on_commit=False,
    ) as db:
        # ── Step 1: Mark as processing ──
        await db.execute(
            update(ProcessingTaskDB)
            .where(ProcessingTaskDB.id == uuid.UUID(task_id))
            .values(status="processing")
        )
        await db.commit()

        # Notify user that processing has started
        await manager.send_to_user(user_id, {
            "event": "task_started",
            "task_id": task_id,
            "filename": filename,
            "message": f"Started processing '{filename}'...",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        try:
            # ── Step 2 + 3: Extract text & AI call ──
            result = await run_full_pipeline(file_path, filename, task_type)

            # ── Step 4: Write result to DB ──
            await db.execute(
                update(ProcessingTaskDB)
                .where(ProcessingTaskDB.id == uuid.UUID(task_id))
                .values(status="completed", result=result)
            )
            await db.commit()

            # ── Step 5: WebSocket push ──
            await manager.send_to_user(user_id, {
                "event": "task_completed",
                "task_id": task_id,
                "filename": filename,
                "status": "completed",
                "message": f"✅ Processing complete for '{filename}'",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        except Exception as e:
            error_msg = str(e)
            await db.execute(
                update(ProcessingTaskDB)
                .where(ProcessingTaskDB.id == uuid.UUID(task_id))
                .values(status="failed", error_message=error_msg)
            )
            await db.commit()

            await manager.send_to_user(user_id, {
                "event": "task_failed",
                "task_id": task_id,
                "filename": filename,
                "status": "failed",
                "message": f"❌ Processing failed for '{filename}': {error_msg}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            # Clean up temp file
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass


async def _get_engine():
    """Helper to get engine for background task (outside request scope)."""
    from database import engine
    return engine


# ─────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────

@router.post(
    "/submit",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskSubmitResponse,
    summary="Submit a file for AI processing",
    description="""
    Upload a file (.txt, .pdf, .docx) and select an AI task type.
    
    Returns **202 Accepted** immediately. Processing happens in the background.
    Connect to `/ws/{user_id}?token=<JWT>` for real-time completion alerts.
    """,
)
async def submit_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="File to process (.txt, .pdf, .docx)"),
    task_type: str = Form(
        "summarize",
        description="AI task: summarize | extract_keywords | sentiment | translate | qa",
    ),
    user_id: Optional[int] = Form(None, description="User ID (set by Django proxy)"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """
    **The main processing endpoint.**
    
    1. Validates JWT → gets user_id
    2. Saves file to temp storage
    3. Creates task record in PostgreSQL (status=pending)
    4. Returns 202 immediately
    5. Background thread does: AI processing → DB update → WebSocket push
    """
    # File size check
    file_content = await file.read()
    if len(file_content) > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Validate task type
    valid_tasks = {"summarize", "extract_keywords", "sentiment", "translate", "qa"}
    if task_type not in valid_tasks:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid task_type. Choose from: {', '.join(valid_tasks)}",
        )

    effective_user_id = user_id or current_user.user_id
    task_id = uuid.uuid4()

    # Save file temporarily
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_name = f"{task_id}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)

    # Create DB record
    task = ProcessingTaskDB(
        id=task_id,
        user_id=effective_user_id,
        filename=file.filename,
        file_size=len(file_content),
        status="pending",
        task_type=task_type,
    )
    db.add(task)
    await db.commit()

    # 🚀 Fire and forget — returns immediately
    background_tasks.add_task(
        _background_process_file,
        str(task_id),
        file_path,
        file.filename,
        task_type,
        effective_user_id,
    )

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        message="File accepted for processing. Connect to WebSocket for live updates.",
        filename=file.filename,
        task_type=task_type,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get task status and result",
)
async def get_task_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Poll the status of a processing task by its UUID."""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid task ID format.")

    result = await db.execute(
        select(ProcessingTaskDB).where(
            ProcessingTaskDB.id == task_uuid,
            ProcessingTaskDB.user_id == current_user.user_id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        filename=task.filename,
        task_type=task.task_type,
        result=task.result,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get(
    "/tasks",
    response_model=list[TaskStatusResponse],
    summary="List all tasks for current user",
)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """Return all processing tasks for the authenticated user."""
    result = await db.execute(
        select(ProcessingTaskDB)
        .where(ProcessingTaskDB.user_id == current_user.user_id)
        .order_by(ProcessingTaskDB.created_at.desc())
        .limit(50)
    )
    tasks = result.scalars().all()
    return [
        TaskStatusResponse(
            task_id=t.id,
            status=t.status,
            filename=t.filename,
            task_type=t.task_type,
            result=t.result,
            error_message=t.error_message,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]


# ─────────────────────────────────────────
# WebSocket — Live "Processing Complete" Alerts
# ─────────────────────────────────────────

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: Optional[str] = None,
):
    """
    **WebSocket endpoint for live alerts.**
    
    Connect: `ws://your-host/process/ws/{user_id}?token=<JWT>`
    
    Events pushed:
    - `task_started` — processing has begun
    - `task_completed` — AI result is ready
    - `task_failed` — an error occurred
    - `ping` — keepalive every 30s
    """
    # Validate JWT for WebSocket
    if token:
        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            token_user_id = payload.get("user_id")
            if int(token_user_id) != user_id:
                await websocket.close(code=4001)
                return
        except Exception:
            await websocket.close(code=4001)
            return

    await manager.connect(websocket, user_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "event": "connected",
            "message": f"Connected! Listening for task updates for user {user_id}.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Keep-alive loop
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_json({"event": "ping", "message": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"event": "ping", "message": "keepalive"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

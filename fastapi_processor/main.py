"""
FastAPI AI Processing Engine
AI-Powered Task & File Processing Platform

Swagger UI: http://localhost/docs
ReDoc:       http://localhost/redoc
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import engine, Base
from routers.process import router as process_router
from models.schemas import HealthResponse


# ─────────────────────────────────────────
# Startup / Shutdown
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (if they don't exist)."""
    print("🚀 FastAPI AI Engine starting up...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Note: Table creation is handled by postgres_init/init.sql
    # This is a safety fallback
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables verified.")
    yield
    print("🛑 FastAPI AI Engine shutting down...")
    await engine.dispose()


# ─────────────────────────────────────────
# App Instance
# ─────────────────────────────────────────
app = FastAPI(
    title="🤖 AI Task Processing Engine",
    description="""
## AI-Powered File Processing Platform — FastAPI Engine

This is the **high-speed AI processing engine** of the dual-engine platform.

### Capabilities
- 📄 **File Upload** — .txt, .pdf, .docx
- 🧠 **AI Tasks** — Summarize, Keywords, Sentiment, Translate, Q&A
- ⚡ **Async Processing** — Returns 202 immediately, processes in background
- 🔔 **Live Alerts** — WebSocket push when task completes
- 🔐 **JWT Auth** — Tokens issued by Django Auth engine

### Authentication
All endpoints require a **Bearer JWT token** issued by the Django `/auth/login/` endpoint.

### WebSocket
Connect to `/process/ws/{user_id}?token=<JWT>` for real-time "Processing Complete" notifications.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ─────────────────────────────────────────
# Middleware
# ─────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:3000", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# Routers
# ─────────────────────────────────────────
app.include_router(process_router)


# ─────────────────────────────────────────
# System Endpoints
# ─────────────────────────────────────────
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health check endpoint."""
    # Quick DB ping
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok",
        service="FastAPI AI Processing Engine",
        version="1.0.0",
        database=db_status,
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — redirects to docs."""
    return JSONResponse({
        "service": "AI Task Processing Engine",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

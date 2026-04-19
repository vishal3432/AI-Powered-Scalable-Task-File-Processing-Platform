"""
FastAPI AI Processing Engine
AI-Powered Task & File Processing Platform

Swagger UI: http://localhost/docs
ReDoc:       http://localhost/redoc
"""
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import engine, Base
from routers.process import router as process_router
from models.schemas import HealthResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
# Startup / Shutdown
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup (if they don't exist)."""
    logger.info("🚀 FastAPI AI Engine starting up...")
    
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        logger.info(f"✅ Upload directory ready: {settings.UPLOAD_DIR}")
    except Exception as e:
        logger.warning(f"⚠️  Could not create upload directory: {e}")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables verified.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
    
    yield
    
    logger.info("🛑 FastAPI AI Engine shutting down...")
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
# CORS Middleware - Load from environment
# ─────────────────────────────────────────
cors_origins = settings.get_cors_origins()

logger.info(f"🔐 CORS Origins configured: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
    db_status = "unknown"
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
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
        "environment": settings.ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/config-check", tags=["System"])
async def config_check():
    """Check if all required configurations are present (for debugging)."""
    checks = {
        "jwt_secret_configured": bool(settings.JWT_SECRET_KEY),
        "openai_api_configured": bool(settings.OPENAI_API_KEY),
        "database_url_configured": bool(settings.DATABASE_URL or settings.POSTGRES_PASSWORD),
        "cors_origins_count": len(cors_origins),
        "environment": settings.ENV,
        "debug_mode": settings.DEBUG,
    }
    
    all_good = all(checks.values())
    return {
        "status": "ok" if all_good else "incomplete",
        "checks": checks,
    }

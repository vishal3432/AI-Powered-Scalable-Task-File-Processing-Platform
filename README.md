# 🤖 AI-Powered Scalable Task & File Processing Platform

> A production-grade, dual-engine Python platform that lets users upload documents and receive AI-generated analysis — with live WebSocket notifications, JWT authentication, Django admin, and full Docker orchestration.

---

## 🎯 Objective & Goal

**The Problem:** Processing large files with AI (summarization, sentiment analysis, keyword extraction) takes 5–30 seconds. A naive implementation would block the HTTP response thread, creating poor user experience and scalability issues.

**The Solution:** A dual-engine architecture that:
1. Accepts files instantly (202 Accepted)
2. Processes them asynchronously in the background
3. Pushes a WebSocket notification the moment processing completes
4. Stores all results in PostgreSQL for future retrieval

**End Result:** Users get a near-instant response and a real-time "✅ Processing Complete" ping — with zero polling required.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT (Browser / App)                   │
│              REST Requests + WebSocket Connection                │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP / WS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NGINX (Traffic Cop) :80                       │
│  ┌─────────────────────┐    ┌──────────────────────────────────┐│
│  │  /auth/*  → Django  │    │  /process/* → FastAPI            ││
│  │  /admin/* → Django  │    │  /ws/*      → FastAPI WebSocket  ││
│  │  /static/ → Static  │    │  /docs      → Swagger UI         ││
│  └─────────────────────┘    └──────────────────────────────────┘│
└────────┬──────────────────────────────┬────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────────┐
│  DJANGO ENGINE  │          │   FASTAPI ENGINE      │
│  (Auth / Admin) │          │  (AI / Processing)    │
│                 │          │                        │
│  • User Reg     │  JWT     │  • POST /process/submit│
│  • Login/Logout │ ──────►  │  • BackgroundTasks     │
│  • JWT Issue    │          │  • AI Summarization    │
│  • Admin Panel  │  Webhook │  • WebSocket Push      │
│  • Task History │ ◄──────  │  • Swagger Docs        │
│  Port: 8000     │          │  Port: 8001            │
└────────┬────────┘          └──────────┬─────────────┘
         │                              │
         └──────────────┬───────────────┘
                        ▼
           ┌─────────────────────────┐
           │    PostgreSQL :5432      │
           │                         │
           │  • users                │
           │  • processing_tasks     │
           │  (Shared by both engines)│
           └─────────────────────────┘
```

---

## 🔄 System Flow (Step-by-Step)

### Step 1 — User Registers & Logs In
```
POST /auth/register/   →  Django creates user, returns JWT
POST /auth/login/      →  Django validates credentials, issues JWT
```

### Step 2 — File Submission (Django as Gateway)
```
POST /auth/files/submit/  (with Bearer token + file)
  → Django validates JWT
  → Django increments user's API call count
  → Django proxies file to FastAPI at POST /process/submit
```

### Step 3 — FastAPI Accepts & Fires Background Task
```
POST /process/submit
  → FastAPI validates JWT (same secret key)
  → FastAPI saves file to disk
  → FastAPI creates DB record (status=pending)
  → FastAPI returns 202 Accepted IMMEDIATELY ◄── User gets response here
  → BackgroundTask starts in thread pool:
       ├── Update DB: status=processing
       ├── Push WebSocket: "task_started"
       ├── Extract text from file (.txt/.pdf/.docx)
       ├── Stream text to OpenAI API
       ├── Receive AI result
       ├── Update DB: status=completed, result=<AI output>
       └── Push WebSocket: "task_completed" ◄── User gets live alert here
```

### Step 4 — User Receives Live Notification
```
WebSocket /process/ws/{user_id}?token=<JWT>
  → Receives: {"event": "task_completed", "task_id": "...", "filename": "..."}
  → User can now fetch result via GET /process/tasks/{task_id}
```

---

## 🛠️ Technologies Used

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Auth Engine** | Django 4.2 + DRF | User management, JWT issuance, Admin panel |
| **Processing Engine** | FastAPI 0.109 | High-speed async file processing |
| **AI Provider** | OpenAI GPT-3.5/4 | Summarization, keywords, sentiment, translation |
| **Database** | PostgreSQL 15 | Shared persistent storage |
| **Task Queue** | FastAPI BackgroundTasks | In-process async task runner |
| **Real-time** | WebSockets (native FastAPI) | Live "Processing Complete" alerts |
| **API Docs** | Swagger UI / ReDoc | Auto-generated from FastAPI |
| **Reverse Proxy** | Nginx Alpine | Routing, load balancing, SSL termination |
| **Orchestration** | Docker Compose | Multi-container deployment |
| **Auth Tokens** | JWT (SimpleJWT) | Stateless authentication across engines |
| **ORM (Django)** | Django ORM | Model management, migrations |
| **ORM (FastAPI)** | SQLAlchemy (async) + asyncpg | Non-blocking DB queries |
| **File Parsing** | PyPDF2, python-docx | Extract text from PDF and DOCX |

---

## 🔄 Alternatives & Integrations

### Alternative AI Providers
| Provider | Integration | Notes |
|----------|-------------|-------|
| **Anthropic Claude** | `pip install anthropic` | Replace `openai` calls in `ai_service.py` |
| **Google Gemini** | `pip install google-generativeai` | Alternative to OpenAI |
| **Azure OpenAI** | `openai` SDK with `api_base` | Enterprise option |
| **Local LLM (Ollama)** | `ollama` + REST | Free, private, no API key needed |
| **Hugging Face** | `transformers` | Open-source models |

### Alternative Task Queues
| Queue | When to Use |
|-------|-------------|
| **Celery + Redis** | High volume (1000s of tasks/min), distributed workers |
| **FastAPI BackgroundTasks** *(current)* | Low-to-medium volume, simplicity |
| **ARQ** | Redis-backed, async-native replacement for Celery |
| **RQ (Redis Queue)** | Simple, Redis-backed, easy to scale |

### Frontend Integration
Connect any frontend via:
```javascript
// 1. Login
const { access } = await fetch('/auth/login/', { method:'POST', body: credentials })

// 2. Connect WebSocket for live updates
const ws = new WebSocket(`ws://your-host/process/ws/${userId}?token=${access}`)
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data)
  if (msg.event === 'task_completed') showResult(msg.task_id)
}

// 3. Submit file
const formData = new FormData()
formData.append('file', file)
formData.append('task_type', 'summarize')
const { task_id } = await fetch('/auth/files/submit/', {
  method: 'POST',
  headers: { Authorization: `Bearer ${access}` },
  body: formData
})
```

---

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- Git
- An OpenAI API key (get one at https://platform.openai.com)

### 1. Clone & Configure
```bash
git clone https://github.com/YOUR_USERNAME/ai-platform.git
cd ai-platform

# Create your environment file
cp .env.example .env
```

### 2. Edit `.env` — Fill in your secrets
```bash
# Open .env in your editor and change:
DJANGO_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(50))">
JWT_SECRET_KEY=<another random secret>
POSTGRES_PASSWORD=<choose a strong password>
OPENAI_API_KEY=sk-...   # Your real OpenAI API key
```

### 3. Build & Launch
```bash
docker compose up --build
```

Wait ~60 seconds for all services to start. You'll see:
```
✅ Database tables verified.
🚀 FastAPI AI Engine starting up...
```

### 4. Create Django Superuser (Admin Access)
```bash
docker compose exec django python manage.py createsuperuser
```

### 5. Access the Platform
| Service | URL |
|---------|-----|
| **Swagger UI (API Docs)** | http://localhost/docs |
| **ReDoc** | http://localhost/redoc |
| **Django Admin** | http://localhost/admin/ |
| **Health Check** | http://localhost/health |

---

## 📡 API Reference

### Authentication (Django — `/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/` | Register new user |
| POST | `/auth/login/` | Login, get JWT tokens |
| POST | `/auth/token/refresh/` | Refresh access token |
| GET | `/auth/profile/` | Get user profile |
| POST | `/auth/validate-token/` | Internal JWT validation |

### File Processing (FastAPI — `/process/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/process/submit` | Submit file for AI processing (202) |
| GET | `/process/tasks` | List all your tasks |
| GET | `/process/tasks/{id}` | Get task status & result |
| WS | `/process/ws/{user_id}` | Live WebSocket alerts |
| GET | `/health` | System health |

### Task Types
| Type | Description |
|------|-------------|
| `summarize` | 3-5 sentence document summary |
| `extract_keywords` | Top 10-15 keywords |
| `sentiment` | Positive/Negative/Neutral + confidence |
| `translate` | Translate to English (or improve grammar) |
| `qa` | Extract questions, answers, and follow-ups |

---

## 🔧 What You Need to Change / Replace

### ⚠️ REQUIRED Before Deployment

| File | Variable | What to Replace |
|------|----------|-----------------|
| `.env` | `OPENAI_API_KEY` | Your real OpenAI API key from platform.openai.com |
| `.env` | `DJANGO_SECRET_KEY` | Random 50+ char string |
| `.env` | `JWT_SECRET_KEY` | Different random string |
| `.env` | `POSTGRES_PASSWORD` | Strong database password |

### 🔧 Optional Customizations

| File | Change | Why |
|------|--------|-----|
| `fastapi_processor/services/ai_service.py` | Replace OpenAI client with Anthropic/Gemini | Use different AI provider |
| `.env` → `AI_MODEL` | `gpt-4` or `gpt-4-turbo` | Use more powerful (but expensive) model |
| `fastapi_processor/services/ai_service.py` → `TASK_PROMPTS` | Edit prompt templates | Customize AI behavior |
| `.env` → `MAX_FILE_SIZE_MB` | Increase limit | Allow larger files |
| `nginx/nginx.conf` | Add SSL config | HTTPS in production |

---

## ☁️ Deployment Guide

### Option 1: Deploy on a VPS (DigitalOcean / AWS EC2 / Hetzner)

```bash
# 1. SSH into your server
ssh user@your-server-ip

# 2. Install Docker
curl -fsSL https://get.docker.com | sh

# 3. Clone your repo
git clone https://github.com/YOUR_USERNAME/ai-platform.git
cd ai-platform
cp .env.example .env
nano .env   # Fill in your secrets

# 4. Launch
docker compose up -d

# 5. Create superuser
docker compose exec django python manage.py createsuperuser
```

### Option 2: Deploy on Railway / Render
- Each service in `docker-compose.yml` becomes a separate service
- Set all `.env` variables as environment variables in the dashboard
- PostgreSQL → use Railway's or Render's managed database

### Option 3: Local Development (No Docker)
```bash
# Terminal 1 — PostgreSQL
createdb ai_platform

# Terminal 2 — Django
cd django_auth
pip install -r requirements.txt
export DJANGO_SECRET_KEY=dev-key JWT_SECRET_KEY=jwt-key POSTGRES_DB=ai_platform
python manage.py migrate
python manage.py runserver 8000

# Terminal 3 — FastAPI
cd fastapi_processor
pip install -r requirements.txt
export OPENAI_API_KEY=sk-... JWT_SECRET_KEY=jwt-key
uvicorn main:app --port 8001 --reload
```

---

## 📁 Project Structure

```
ai-platform/
├── docker-compose.yml          # Orchestrates all 4 services
├── .env.example                # Environment template (copy to .env)
│
├── nginx/
│   └── nginx.conf              # Traffic routing rules
│
├── postgres_init/
│   └── init.sql                # DB schema initialization
│
├── django_auth/                # 🐍 Engine 1: Auth & Admin
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   ├── core/
│   │   ├── settings.py         # Django config + JWT settings
│   │   └── urls.py             # URL routing
│   └── apps/
│       ├── users/              # Registration, login, JWT
│       │   ├── models.py       # Extended User model
│       │   ├── views.py        # Auth endpoints + FastAPI proxy
│       │   ├── serializers.py
│       │   └── urls.py
│       └── files/              # Task history (read-only from Django)
│           ├── models.py       # ProcessingTask (managed=False)
│           ├── views.py
│           └── urls.py
│
└── fastapi_processor/          # ⚡ Engine 2: AI Processing
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py                 # FastAPI app + Swagger docs
    ├── config.py               # Settings via env vars
    ├── database.py             # Async SQLAlchemy + ORM models
    ├── auth.py                 # JWT validation middleware
    ├── websocket_manager.py    # Live alert broadcast system
    ├── routers/
    │   └── process.py          # All /process/* endpoints
    ├── services/
    │   └── ai_service.py       # OpenAI + file parsing logic
    └── models/
        └── schemas.py          # Pydantic request/response models
```

---

## 🔗 Access Links (After Deployment)

| Resource | URL |
|----------|-----|
| **API Documentation (Swagger)** | `http://YOUR_DOMAIN/docs` |
| **API Documentation (ReDoc)** | `http://YOUR_DOMAIN/redoc` |
| **Django Admin Panel** | `http://YOUR_DOMAIN/admin/` |
| **Health Check** | `http://YOUR_DOMAIN/health` |
| **Register** | `POST http://YOUR_DOMAIN/auth/register/` |
| **Login** | `POST http://YOUR_DOMAIN/auth/login/` |

> Replace `YOUR_DOMAIN` with `localhost` for local development.

---

## 🧪 Testing the Platform

### Quick Test with curl
```bash
# 1. Register
curl -X POST http://localhost/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"testpass123","password2":"testpass123"}'

# 2. Login (save the access token)
TOKEN=$(curl -s -X POST http://localhost/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])")

# 3. Submit a file
echo "The quick brown fox jumps over the lazy dog. This is a test document." > test.txt
curl -X POST http://localhost/auth/files/submit/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.txt" \
  -F "task_type=summarize"

# 4. Check task status (use task_id from previous response)
curl http://localhost/process/tasks/YOUR_TASK_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📝 License

MIT License — free to use, modify, and deploy.

---

*Built with ❤️ using Django, FastAPI, PostgreSQL, OpenAI, and Docker.*

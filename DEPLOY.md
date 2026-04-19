# Deployment Guide

## Prerequisites
- Docker ≥ 24.x
- Docker Compose ≥ 2.x
- An OpenAI API key → https://platform.openai.com

---

## 1 — Clone & Configure

```bash
git clone <your-repo-url>
cd AI-Powered-Scalable-Task-File-Processing-Platform

# Creates .env from the example template
make setup
```

Now **open `.env`** and fill in the required values:

| Variable | Description | How to generate |
|----------|-------------|-----------------|
| `POSTGRES_PASSWORD` | DB password | Pick a strong password |
| `DJANGO_SECRET_KEY` | Django secret | `python -c "import secrets; print(secrets.token_hex(50))"` |
| `JWT_SECRET_KEY` | Shared JWT secret | `python -c "import secrets; print(secrets.token_hex(50))"` |
| `OPENAI_API_KEY` | OpenAI key | https://platform.openai.com/api-keys |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | e.g. `localhost,127.0.0.1,api.yourdomain.com` |

> ⚠️ `JWT_SECRET_KEY` **must be identical** in both Django and FastAPI — they share it to validate tokens.

---

## 2 — Build & Start

```bash
make build   # Build Docker images (first time / after code changes)
make up      # Start all 4 services in the background
```

Services started:
| Service | Role | Internal port |
|---------|------|---------------|
| `postgres` | Database | 5432 |
| `django` | Auth + Admin | 8000 |
| `fastapi` | AI Processing | 8001 |
| `nginx` | Gateway / reverse proxy | **80 (public)** |

---

## 3 — Create a Superuser (first time)

```bash
make createsuperuser
```

Then visit **http://localhost/admin** to access the Django admin panel.

---

## 4 — Verify Everything Works

```bash
# Check all containers are running
make status

# Tail logs (Ctrl+C to stop)
make logs

# Hit the health endpoint
curl http://localhost/health
```

Expected health response:
```json
{ "status": "ok", "service": "FastAPI AI Processing Engine", "database": "connected" }
```

---

## API Quick Start

### Register & Login
```bash
# Register
curl -X POST http://localhost/auth/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"YourPassword123","first_name":"John","last_name":"Doe"}'

# Login → get JWT token
curl -X POST http://localhost/auth/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"YourPassword123"}'
```

### Upload & Process a File
```bash
TOKEN="<access token from login>"

curl -X POST http://localhost/process/upload/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "task_type=summarize"
```

### View API Docs
Open **http://localhost/docs** in your browser for the full interactive Swagger UI.

---

## Useful Commands

```bash
make logs           # All service logs
make logs-django    # Django logs only
make logs-fastapi   # FastAPI logs only
make restart        # Restart all services
make down           # Stop everything
make clean          # ⚠️ Stop + delete ALL data (volumes)
make shell-django   # Shell into Django container
make shell-fastapi  # Shell into FastAPI container
```

---

## Production Deployment (Cloud VM)

When deploying to a VPS / cloud server:

1. Set `DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com` in `.env`
2. Point your domain's DNS A-record to the server IP
3. For HTTPS, add a Certbot/Let's Encrypt step and update `nginx/nginx.conf` with SSL config
4. Make sure port 80 (and 443 for HTTPS) are open in your firewall/security group

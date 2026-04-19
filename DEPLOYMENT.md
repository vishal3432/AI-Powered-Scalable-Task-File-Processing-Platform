# 🚀 Deployment Guide

## Prerequisites

- Docker ≥ 24.0 and Docker Compose v2 installed on your server
- An OpenAI API key
- A domain name (optional — needed for HTTPS)

---

## Quick Start (Local / VPS)

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd AI-Powered-Scalable-Task-File-Processing-Platform
```

### 2. Generate secrets and fill in your `.env`

```bash
make generate-secrets   # prints fresh random keys
cp .env.example .env
nano .env               # paste the generated keys + your OpenAI key
```

Minimum required values in `.env`:

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Strong random password |
| `DJANGO_SECRET_KEY` | 50-char hex secret (use `make generate-secrets`) |
| `JWT_SECRET_KEY` | 50-char hex secret (use `make generate-secrets`) |
| `OPENAI_API_KEY` | From platform.openai.com |
| `DJANGO_ALLOWED_HOSTS` | Your domain, e.g. `api.myapp.com,myapp.com` |

### 3. Build and start

```bash
make build
make up
```

### 4. Create the Django admin superuser

```bash
make createsuperuser
```

### 5. Verify everything is healthy

```bash
make ps                           # all containers should be "healthy"
curl http://localhost/health      # → {"status": "ok"}
curl http://localhost/auth/health/ # → {"status": "ok"}
```

---

## Enabling HTTPS (Production)

### Option A — Let's Encrypt with Certbot (recommended)

```bash
# Install certbot on your server
sudo apt install certbot

# Get a cert (standalone — stop nginx first)
make down
sudo certbot certonly --standalone -d yourdomain.com

# Copy certs into the project
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem   nginx/ssl/

# Uncomment the HTTPS server block in nginx/nginx.conf
# and the HTTP→HTTPS redirect block
nano nginx/nginx.conf

make up
```

### Option B — Cloudflare Tunnel (zero-port-forwarding)

Use [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) to expose your local port 80 securely without opening firewall ports.

---

## Deploying to a Cloud VPS (Ubuntu)

```bash
# On fresh Ubuntu 22.04 / 24.04
sudo apt update && sudo apt install -y docker.io docker-compose-v2 make git
sudo usermod -aG docker $USER && newgrp docker

git clone <your-repo-url>
cd AI-Powered-Scalable-Task-File-Processing-Platform
make setup          # creates .env from .env.example
nano .env           # fill in secrets
make build && make up
make createsuperuser
```

---

## Useful Commands

```bash
make logs           # tail all logs
make logs s=django  # tail django only
make logs s=fastapi # tail fastapi only
make shell s=django # open shell in django container
make migrate        # run migrations manually
make restart        # restart all services
make down           # stop everything (keeps DB data)
make clean          # ⚠️  destroys everything including DB
```

---

## Environment Variables Reference

| Variable | Default | Required |
|---|---|---|
| `POSTGRES_DB` | `ai_platform` | No |
| `POSTGRES_USER` | `postgres` | No |
| `POSTGRES_PASSWORD` | — | **Yes** |
| `DJANGO_SECRET_KEY` | — | **Yes** |
| `DJANGO_DEBUG` | `False` | No |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Yes (for prod) |
| `JWT_SECRET_KEY` | — | **Yes** |
| `JWT_EXPIRY_HOURS` | `24` | No |
| `OPENAI_API_KEY` | — | **Yes** |
| `AI_MODEL` | `gpt-3.5-turbo` | No |
| `MAX_FILE_SIZE_MB` | `10` | No |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:80` | Yes (for prod) |

---

## Architecture

```
Internet
   │
[Nginx :80/:443]          ← reverse proxy, rate limiting, gzip, SSL
   ├── /auth/*  → Django :8000   ← auth, JWT, user management, admin
   ├── /admin/* → Django :8000
   ├── /process/* → FastAPI :8001 ← AI file processing, OpenAI
   ├── /ws/*    → FastAPI :8001   ← WebSocket live updates
   └── /health  → FastAPI :8001
         │
    [PostgreSQL :5432]    ← internal only, not exposed to host
```

---

## Security Checklist Before Going Live

- [ ] All `CHANGE_ME_*` values replaced with strong secrets
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` set to your actual domain(s)
- [ ] `CORS_ALLOWED_ORIGINS` set to your frontend origin(s)
- [ ] HTTPS enabled (SSL certs in `nginx/ssl/`)
- [ ] Firewall: only ports 80 and 443 open publicly (not 5432, 8000, 8001)
- [ ] `make createsuperuser` done with a strong password
- [ ] Regular DB backups configured

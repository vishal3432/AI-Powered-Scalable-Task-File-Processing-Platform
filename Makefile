# ══════════════════════════════════════════════════
# AI-Powered Task & File Processing Platform
# Deployment Makefile
# ══════════════════════════════════════════════════

.PHONY: help setup generate-secrets build up down logs restart clean ps

# ─────────────────────────────────────────
# Default target
# ─────────────────────────────────────────
help:
	@echo ""
	@echo "  AI Platform – Deployment Commands"
	@echo ""
	@echo "  make setup            Copy .env and generate secrets"
	@echo "  make generate-secrets Print new random secret keys"
	@echo "  make build            Build all Docker images"
	@echo "  make up               Start all services (detached)"
	@echo "  make down             Stop all services"
	@echo "  make logs             Tail logs for all services"
	@echo "  make logs s=django    Tail logs for a specific service"
	@echo "  make restart          Restart all services"
	@echo "  make ps               Show running containers"
	@echo "  make shell s=django   Open a shell in a service container"
	@echo "  make migrate          Run Django migrations manually"
	@echo "  make createsuperuser  Create Django admin user"
	@echo "  make clean            Remove containers, volumes, images"
	@echo ""

# ─────────────────────────────────────────
# Setup
# ─────────────────────────────────────────
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅  .env created from .env.example"; \
		echo "⚠️   Edit .env and fill in your secrets before running 'make up'"; \
	else \
		echo "ℹ️   .env already exists — skipping"; \
	fi

generate-secrets:
	@echo ""
	@echo "─── Copy these into your .env ───"
	@echo "DJANGO_SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_hex(50))')"
	@echo "JWT_SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_hex(50))')"
	@echo "POSTGRES_PASSWORD=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
	@echo ""

# ─────────────────────────────────────────
# Docker lifecycle
# ─────────────────────────────────────────
build:
	docker compose build --no-cache

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

ps:
	docker compose ps

logs:
	docker compose logs -f $(s)

shell:
	docker compose exec $(s) sh

# ─────────────────────────────────────────
# Django management
# ─────────────────────────────────────────
migrate:
	docker compose exec django python manage.py migrate

createsuperuser:
	docker compose exec django python manage.py createsuperuser

# ─────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────
clean:
	@echo "⚠️  This removes ALL containers, volumes (including DB data), and images!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker compose down -v --rmi all

.PHONY: help dev dev-build local down migrate revision downgrade current history

COMPOSE ?= docker compose
APP_SERVICE ?= app
MSG ?= update schema

help:
	@echo "Available commands:"
	@echo "  make dev                    Start Docker and follow app logs"
	@echo "  make dev-build              Build Docker images, start containers, and follow app logs"
	@echo "  make local                  Start postgres/redis, set up .venv, install deps, and run the app locally"
	@echo "  make down                   Stop and remove the Docker containers"
	@echo "  make migrate                 Apply all migrations to the latest revision"
	@echo "  make revision MSG='...'      Create a new autogenerate migration"
	@echo "  make downgrade              Roll back the last migration"
	@echo "  make current                 Show current migration version"
	@echo "  make history                 Show migration history"

dev:
	$(COMPOSE) up -d
	$(COMPOSE) logs -f $(APP_SERVICE)

dev-build:
	$(COMPOSE) up -d --build
	$(COMPOSE) logs -f $(APP_SERVICE)

local:
	$(COMPOSE) up -d postgres redis
	python3 -m venv .venv
	.venv/bin/pip install -e .
	RUN_MODE=dev sh ./start.sh

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) up -d
	$(COMPOSE) exec $(APP_SERVICE) alembic upgrade head

revision:
	$(COMPOSE) exec $(APP_SERVICE) alembic revision --autogenerate -m "$(MSG)"

downgrade:
	$(COMPOSE) exec $(APP_SERVICE) alembic downgrade -1

current:
	$(COMPOSE) exec $(APP_SERVICE) alembic current

history:
	$(COMPOSE) exec $(APP_SERVICE) alembic history

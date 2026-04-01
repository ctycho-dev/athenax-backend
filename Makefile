.PHONY: help dev dev-build local down migrate test revision downgrade current history check-head recreate logs

COMPOSE ?= docker compose
APP_SERVICE ?= app
PYTHON ?= $(shell command -v python3.13 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3)
MSG ?= update schema
HAS_REVISIONS := $(shell find alembic/versions -maxdepth 1 -name '*.py' -print -quit 2>/dev/null)

help:
	@echo "Available commands:"
	@echo "  make dev                    Start Docker and follow app logs"
	@echo "  make dev-build              Build Docker images, start containers, and follow app logs"
	@echo "  make local                  Start postgres/redis, set up .venv, install deps, and run the app locally"
	@echo "  make test                   Start the test database and run the test suite"
	@echo "  make recreate               Force-recreate the app container"
	@echo "  make logs                   Tail app container logs"
	@echo "  make down                   Stop and remove the Docker containers"
	@echo "  make migrate                Apply all migrations to the latest revision"
	@echo "  make revision MSG='...'     Create a new autogenerate migration"
	@echo "  make downgrade              Roll back the last migration"
	@echo "  make current                Show current migration version"
	@echo "  make history                Show migration history"

start:
	$(COMPOSE) up -d
	$(COMPOSE) logs -f $(APP_SERVICE)

start-build:
	$(COMPOSE) up -d --build
	$(COMPOSE) logs -f $(APP_SERVICE)

dev:
	$(COMPOSE) up -d postgres redis
	"$(PYTHON)" -m venv .venv
	.venv/bin/python -m pip install --upgrade pip setuptools wheel
	.venv/bin/pip install -e .
	@_port=$${PORT:-8000}; \
	if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:$$_port -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Port $$_port is already in use. Stop the existing local app before running 'make dev'."; \
		lsof -nP -iTCP:$$_port -sTCP:LISTEN; \
		exit 1; \
	fi
	MODE=dev RUN_MODE=dev REDIS_HOST=localhost sh ./start.sh

recreate:
	$(COMPOSE) up -d --force-recreate $(APP_SERVICE)

logs:
	$(COMPOSE) logs -f $(APP_SERVICE)

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic upgrade head

test:
	$(COMPOSE) --profile test up -d postgres-test
	.venv/bin/pytest

check-head:
	$(COMPOSE) up -d postgres redis
	@if [ -z "$$(find alembic/versions -maxdepth 1 -name '*.py' -print -quit 2>/dev/null)" ]; then \
		echo "No Alembic revision files found in alembic/versions."; \
		echo "Restore the migration files or create a first revision before running this command."; \
		exit 1; \
	fi
	@current_output="$$( $(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic current 2>/dev/null )"; \
	head="$$( $(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic heads 2>/dev/null | tail -n 1 | awk '{print $$1}' )"; \
	current="$$(printf '%s\n' "$$current_output" | tail -n 1 | awk '{print $$1}' )"; \
	if [ -z "$$current_output" ] || [ -z "$$head" ]; then \
		echo "Unable to read migration state. Make sure postgres/redis are running and alembic can connect."; \
		exit 1; \
	fi; \
	if printf '%s\n' "$$current_output" | grep -q "(head)"; then \
		exit 0; \
	fi; \
	if [ "$$current" != "$$head" ]; then \
		echo "Database is not at head. Run 'make migrate' before 'make revision'."; \
		echo "Current: $$current"; \
		echo "Head:    $$head"; \
		exit 1; \
	fi

revision:
	@if [ -n "$(HAS_REVISIONS)" ]; then $(MAKE) check-head; fi
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic revision --autogenerate -m "$(MSG)"

downgrade:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic downgrade -1

current:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic current

history:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps $(APP_SERVICE) alembic history

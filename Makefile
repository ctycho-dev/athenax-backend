.PHONY: help dev dev-build local down migrate revision downgrade current history check-head

COMPOSE ?= docker compose
APP_SERVICE ?= app
MSG ?= update schema
HAS_REVISIONS := $(shell find alembic/versions -maxdepth 1 -name '*.py' -print -quit 2>/dev/null)

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

check-head:
	@if [ -z "$$(find alembic/versions -maxdepth 1 -name '*.py' -print -quit 2>/dev/null)" ]; then \
		echo "No Alembic revision files found in alembic/versions."; \
		echo "Restore the migration files or create a first revision before running this command."; \
		exit 1; \
	fi
	@current_output="$$( $(COMPOSE) exec $(APP_SERVICE) alembic current 2>/dev/null )"; \
	head="$$( $(COMPOSE) exec $(APP_SERVICE) alembic heads 2>/dev/null | tail -n 1 | awk '{print $$1}' )"; \
	current="$$(printf '%s\n' "$$current_output" | tail -n 1 | awk '{print $$1}' )"; \
	if [ -z "$$current_output" ] || [ -z "$$head" ]; then \
		echo "Unable to read migration state. Make sure the app container is running."; \
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
	$(COMPOSE) exec $(APP_SERVICE) alembic revision --autogenerate -m "$(MSG)"

downgrade:
	$(COMPOSE) exec $(APP_SERVICE) alembic downgrade -1

current:
	$(COMPOSE) exec $(APP_SERVICE) alembic current

history:
	$(COMPOSE) exec $(APP_SERVICE) alembic history

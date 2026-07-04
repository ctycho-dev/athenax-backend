.PHONY: help dev dev-build local down migrate test revision downgrade current history check-head recreate logs seed seed\:categories seed\:w2 seed\:load validate upload-pending load-test-ui load-test load-test-smoke load-test-ratelimit

COMPOSE ?= docker compose
APP_SERVICE ?= app
PYTHON ?= $(shell command -v python3.13 2>/dev/null || command -v python3.12 2>/dev/null || command -v python3)
MSG ?= update schema
HAS_REVISIONS := $(shell find alembic/versions -maxdepth 1 -name '*.py' -print -quit 2>/dev/null)

help:
	@echo "Available commands:"
	@echo "  make start                  Start Docker containers and follow app logs"
	@echo "  make start-build            Build Docker images, start containers, and follow app logs"
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
	@echo "  make seed                   Seed the database with initial data"
	@echo "  make seed:categories        Seed only parent categories and subcategories from Categories.csv"
	@echo "  make seed:load              Seed 1000 products/200 articles/200 broadcasts for load testing"
	@echo "  make validate               Validate Projects.xlsx against Data Specs rules (ARGS='file.xlsx sheet_name' to override)"
	@echo "  make upload-pending         Import Projects.xlsx as pending (ARGS='file.xlsx sheet_name' to override)"
	@echo "  make load-test-ui           Start the locust web UI at http://localhost:8089 (HOST overridable)"
	@echo "  make load-test              Headless capacity run: 200 users, 5 min, exports CSV+HTML (HOST overridable)"
	@echo "  make load-test-smoke        Read-only smoke test: 50 users, 2 min (HOST overridable)"
	@echo "  make load-test-ratelimit    Rate-limit check: spoof off, 100 users, 2 min (HOST overridable)"

start:
	$(COMPOSE) up -d
	$(COMPOSE) logs -f $(APP_SERVICE)

start-build:
	$(COMPOSE) up -d --build
	$(COMPOSE) logs -f $(APP_SERVICE)

dev:
	$(COMPOSE) up -d postgres redis
	"$(PYTHON)" -m venv .venv
	".venv/bin/python" -m pip install --upgrade pip setuptools wheel
	".venv/bin/python" -m pip install -e .
	@_port=$${PORT:-8000}; \
	if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:$$_port -sTCP:LISTEN >/dev/null 2>&1; then \
		echo "Port $$_port is already in use. Stop the existing local app before running 'make dev'."; \
		lsof -nP -iTCP:$$_port -sTCP:LISTEN; \
		exit 1; \
	fi
	RUN_MODE=dev PORT=$${PORT:-8000} HOST=0.0.0.0 ".venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port $${PORT:-8000} --reload

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
	".venv/bin/python" -m pytest

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

seed:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app $(APP_SERVICE) python scripts/seed.py

seed\:categories:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app $(APP_SERVICE) python scripts/seed_categories.py

seed\:w2:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app $(APP_SERVICE) python scripts/seed.py w2

seed\:load:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app $(APP_SERVICE) python scripts/seed_load_data.py $(ARGS)

validate:
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app $(APP_SERVICE) python scripts/validate_xlsx.py $(ARGS)

upload-pending:
	$(COMPOSE) up -d postgres redis
	$(COMPOSE) run --rm --no-deps -e PYTHONPATH=/app $(APP_SERVICE) python scripts/upload_pending.py $(ARGS)

# Load test (locust) — override HOST and USERS on the command line, e.g.
#   make load-test HOST=http://dev.example.com
#   make load-test USERS=100 DURATION=3m
LOCUSTFILE ?= tests/load/locustfile.py
HOST       ?= http://localhost:8000
USERS      ?= 200
SPAWN_RATE ?= 20
DURATION   ?= 5m

load-test-ui:
	".venv/bin/python" -m locust -f $(LOCUSTFILE) --host $(HOST)

load-test:
	".venv/bin/python" -m locust -f $(LOCUSTFILE) --host $(HOST) \
		--headless -u $(USERS) -r $(SPAWN_RATE) -t $(DURATION) \
		--csv=load-test-results --html=load-test-results.html

load-test-smoke:
	".venv/bin/python" -m locust -f $(LOCUSTFILE) --host $(HOST) \
		--tags read --headless -u 50 -r 10 -t 2m

load-test-ratelimit:
	LOCUST_SPOOF_IP=0 ".venv/bin/python" -m locust -f $(LOCUSTFILE) --host $(HOST) \
		--headless -u 100 -r 20 -t 2m

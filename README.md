# FastAPI Production Starter

Production-ready FastAPI starter with a clean user domain flow:

- API -> Service -> Repository
- Async SQLAlchemy
- PostgreSQL + Redis
- Docker Compose for production and local development
- Integration tests for user APIs

## Prerequisites

- Docker + Docker Compose
- Python 3.12+

## Environment Setup

1. Create the env file:

```bash
cp .env.example .env
```

2. Adjust values in `.env` if needed.

## Run With Docker (Production Style)

Build and start app + postgres + redis:

```bash
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

Check logs:

```bash
docker compose logs -f app
```

Health check:

```bash
curl http://localhost:8844/health
```

Stop services:

```bash
docker compose down
```

## Run With Docker (Development Mode)

Run app in reload mode inside Docker:

```bash
RUN_MODE=dev docker compose up -d --build
```

Notes:

- `RUN_MODE=dev` enables `uvicorn --reload` in `start.sh`.
- `RUN_MODE=prod` runs a single `uvicorn` process without reload.

## Run Locally (Without Docker App Container)

Use Docker only for databases, and run FastAPI from your local venv:

```bash
docker compose up -d postgres redis
python3 -m venv .venv
.venv/bin/pip install -e .
RUN_MODE=dev sh ./start.sh
```

## User Integration Tests

Start test database:

```bash
docker compose --profile test up -d postgres-test
```

Run tests:

```bash
.venv/bin/pytest tests/integration/test_user_api.py -v
```

If you previously used a different `postgres-test` config, reset its volume once:

```bash
docker compose --profile test down -v
docker compose --profile test up -d postgres-test
```

## Runtime Variables (start.sh)

- `RUN_MODE`: `prod` or `dev`
- `HOST`: bind host (default `0.0.0.0`)
- `PORT`: bind port (default `8844`)
- `LOG_LEVEL`: app log level (default `info`)
- `RUN_MIGRATIONS`: set to `1` to run Alembic on startup

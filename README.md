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

## Run With Make

Start the app and follow logs:

```bash
make start
```

Build, start, and follow logs:

```bash
make start-build
```

Stop the stack:

```bash
make down
```

Health check:

```bash
curl http://localhost:8000/health
```

Notes:

- `make dev` starts Docker without forcing a rebuild.
- `make dev-build` rebuilds the images first.
- `RUN_MODE=dev` still enables `uvicorn --reload` in `start.sh`.
- `RUN_MODE=prod` runs a single `uvicorn` process without reload.

## Run Locally (Without Docker App Container)

Use this command to start Postgres and Redis, set up the local venv, install dependencies, and run the app:

```bash
make dev
```

## Model Change Workflow

When you change a SQLAlchemy model:

1. Update the model file in `app/domain/<feature>/model.py`
2. Create a migration:

```bash
make revision MSG='describe change'
```

3. Review the generated file in `alembic/versions/`
4. Apply it to the database:

```bash
make migrate
```

`make migrate` starts only the database services and runs Alembic in a one-off container.

If you only change the model and skip the migration step, the database will not change.

## User Integration Tests

Run the full test suite:

```bash
make test
```

If you previously used a different `postgres-test` config, reset its volume once:

```bash
docker compose --profile test down -v
docker compose --profile test up -d postgres-test
```

## Runtime Variables (start.sh)

- `RUN_MODE`: `prod` or `dev`
- `HOST`: bind host (default `0.0.0.0`)
- `PORT`: bind port (default `8000`)
- `LOG_LEVEL`: app log level (default `info`)

## Make Commands

- `make start`: start Docker and tail app logs
- `make start-build`: rebuild containers, start Docker, and tail app logs
- `make dev`: start Postgres and Redis, set up local venv, install dependencies, and run the app
- `make down`: stop and remove the stack
- `make test`: start the test database and run the test suite
- `make migrate`: start the database services if needed and apply migrations in a one-off container
- `make revision MSG='...'`: generate a new Alembic migration
- `make current`: show the current Alembic revision
- `make history`: show the Alembic revision history

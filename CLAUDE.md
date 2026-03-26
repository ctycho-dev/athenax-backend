# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development (local, no Docker)
make dev           # Start Postgres/Redis, create venv, install deps, run app

# Development (Docker)
make dev-build     # Build Docker images and start containers
make start         # Start containers and tail app logs

# Testing
make test          # Start test DB and run full pytest suite

# Run a single test file or test case
.venv/bin/pytest tests/integration/test_lab_api.py -v
.venv/bin/pytest tests/integration/test_lab_api.py::TestLabAPI::test_create_lab_success -v

# Database migrations
make migrate                       # Apply pending Alembic migrations
make revision MSG='add foo table'  # Autogenerate migration from model changes
make downgrade                     # Rollback last migration
make current                       # Show current migration revision
```

**Python version**: 3.12+
**Test database**: PostgreSQL on `localhost:5433` (started by `make test`)

## Architecture

FastAPI + async SQLAlchemy 2.0 backend using Domain-Driven Design with a strict four-layer architecture. Each domain (`user`, `university`, `lab`, `category`, `product`, `tag`) has identical internal structure.

### Layer Responsibilities

| Layer | File | Role |
|-------|------|------|
| API | `app/api/v1/<domain>.py` | Route handlers, rate limiting, dependency injection via `Depends()` |
| Service | `app/domain/<domain>/service.py` | Business logic, permission checks, orchestration |
| Repository | `app/domain/<domain>/repository.py` | Async SQLAlchemy queries, wraps errors into custom exceptions |
| Model/Schema | `app/domain/<domain>/model.py` + `schema.py` | ORM models (TimestampMixin) + Pydantic I/O schemas |

### Key Shared Infrastructure

- **`app/common/base_repository.py`** — Generic `BaseRepository[T, S, C]` providing `get_by_id`, `get_all`, `create`, `update`, `delete_by_id`, `soft_delete` with pagination. All repositories extend this.
- **`app/exceptions/exceptions.py`** — Custom exceptions (`NotFoundError`, `ValidationError`, `DatabaseError`, `RepositoryError`, `ExternalServiceError`) with centralized FastAPI handlers that log request ID + user email.
- **`app/api/dependencies/`** — Factory functions for dependency injection: `services.py` composes repositories into services; `auth.py` provides `get_current_user()` and `require_admin_user()` dependencies.
- **`app/core/config.py`** — Pydantic Settings loaded from `.env` (database URL, Redis, JWT secret, SMTP).

### Authentication Flow

JWT tokens signed with `SECRET_KEY` and stored in HTTP-only cookies. `get_current_user()` dependency validates the token; `require_admin_user()` additionally enforces `role == ADMIN`. Public endpoints (signup, login, email verify) skip auth.

### Schema Conventions

- All Pydantic schemas extend `CamelModel` which auto-converts snake_case fields to camelCase in API responses.
- Input schemas: e.g., `UserSignupSchema` (external) vs `UserCreateDBSchema` (internal, includes hashed password).
- Output schemas: e.g., `UserOutSchema` (excludes sensitive fields like `password_hash`).

### Middleware Stack (applied in order)

1. `AccessLogMiddleware` — Injects `X-Request-ID` header, logs request/response with structured fields.
2. `SlowAPIMiddleware` — Per-endpoint rate limiting via slowapi.
3. CORS middleware — Configurable origins from settings.

### Testing Patterns

Tests are async integration tests in `tests/integration/`. The `conftest.py` provides:
- A real test PostgreSQL database (tables created/dropped per session).
- `FakeEmailService` overriding SMTP to prevent actual email sends.
- `client` fixture with `AsyncClient` and dependency overrides for auth (mock `current_user`).

All test classes follow `TestXxxAPI` naming and test both success paths and error cases (404, 422, 403).

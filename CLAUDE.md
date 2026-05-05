# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comments

Add a short inline comment when the WHY is non-obvious — e.g. a discarded return value that exists only to trigger a side effect like raising `NotFoundError`. One line max.

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

| Layer        | File                                         | Role                                                                |
| ------------ | -------------------------------------------- | ------------------------------------------------------------------- |
| API          | `app/api/v1/<domain>.py`                     | Route handlers, rate limiting, dependency injection via `Depends()` |
| Service      | `app/domain/<domain>/service.py`             | Business logic, permission checks, orchestration                    |
| Repository   | `app/domain/<domain>/repository.py`          | Async SQLAlchemy queries, wraps errors into custom exceptions       |
| Model/Schema | `app/domain/<domain>/model.py` + `schema.py` | ORM models (TimestampMixin) + Pydantic I/O schemas                  |

### Key Shared Infrastructure

- **`app/common/base_repository.py`** — Generic `BaseRepository[T, S, C]` providing `get_by_id`, `get_all`, `create`, `update`, `delete_by_id`, `soft_delete` with pagination. All repositories extend this unless the model has a composite PK (e.g. association tables), in which case a plain class is used.
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

### Transaction Management

- `session_scope` rolls back on error but never commits — services own `commit()`.
- Repositories only `flush()` + `refresh()`, never `commit()`.
- Multi-step atomic ops (e.g. `signup_user`) must call internal helpers (e.g. `_upsert_profile`) directly, not the public service methods which each commit independently.

### Migrations

After any ORM model change (new column, new table, renamed field, changed type), always run:

```bash
make revision MSG='describe the change'
```

Never write migration files by hand — always use Alembic autogenerate. Run `make migrate` afterward to apply.

### Domain / Model Rules

- `Category` lives in `category/model.py`; `lab_category` association table stays in `lab/model.py`.
- Every model must be explicitly imported in `alembic/env.py` for autogenerate to detect it. (All models in a domain file, not just the primary one).
- Profile/extension tables belong in their parent domain (e.g. `user/model.py`), not a new folder.
- Never use `relationship()` when a join table exists — query explicitly.
- Repos return ORM objects only — no schema conversion. Services own `commit()`, `refresh()`, and `model_validate()`.
- When validating ORM → schema with extra fields: `result = OutSchema.model_validate(obj, from_attributes=True)` then set extra fields. Never `**schema.model_dump()`.
- Many-to-many updates: use `sync_association()` from `app/common/db_utils.py` — diffs existing vs new, never delete-all-reinsert.
- Association tables must be ORM classes extending `Base, TimestampMixin` with `PrimaryKeyConstraint`, not bare `Table(...)` constructs.
- Out schemas belong to their own domain, not the domain that uses them.
- Never add wrapper methods in repos for create/update (e.g. `create_for_product`, `update_text`). Services call `self.repo.create()` / `self.repo.update_instance()` directly with a dict. Repos only contain custom query methods.
- Repos are pure data access — no orchestration, no calling other repos, no mixed read/write methods (no `get_or_create`). Service owns all coordination.
- `sync_association()` is called from the service, not the repo.
- Categories are a managed resource (admin CRUD API). Clients pass `category_ids` only — never create categories as a side effect of another domain's create/update.
- In ORM queries, use mapped model attributes; use `__table__.c` only for explicit SQLAlchemy Core table-level access.

### Avoiding N+1 Queries

- Never call per-row queries inside a loop. Use batch repo methods for list paths.
- Write plural batch methods (`get_x(ids) -> dict[int, ...]`) that hold the SQL. Singular methods (`get_x(id)`) delegate to the plural with a single-element list — no duplicated SQL.
- In service `list()`: fetch IDs, call batch methods once each, assemble schemas in a loop with no DB calls inside.

### Pagination

- Wire `limit`/`offset` all the way: `Query` param → service arg → `repo.get_all()`.
- Defaults (`limit=50`, `offset=0`) belong only in the endpoint — service and repo take plain `int`.

### File Upload / R2 Storage

- `R2StorageService` (`app/common/storage.py`) — inject via `get_storage_service()`, pass as method arg not constructor.
- Upload order: validate → upload R2 → insert DB row → commit. R2 failure raises 502 before any DB write.
- Store `storage_key` in DB; compute full URL in service via `settings.r2.cdn_base_url`.
- `sort_order`: query `get_max_sort_order()` + 10 when not provided (spaced integers: 10, 20, 30…).
- R2 env vars: `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_ENDPOINT`, `R2_BUCKET`, `R2_CDN_BASE_URL`.

### Testing Patterns

Tests are async integration tests in `tests/integration/`. The `conftest.py` provides:

- A real test PostgreSQL database (tables created/dropped per session).
- `FakeEmailService` overriding SMTP to prevent actual email sends.
- `client` fixture with `AsyncClient` and dependency overrides for auth (mock `current_user`).

All test classes follow `TestXxxAPI` naming and test both success paths and error cases (404, 422, 403).

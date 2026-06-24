# CLAUDE.md

## Comments
Add a short inline comment only when the WHY is non-obvious. One line max.

## Commands
```bash
make dev           # local: start Postgres/Redis, venv, run app
make dev-build     # Docker: build images and start containers
make start         # Docker: start containers and tail logs
make test          # start test DB and run full pytest suite
make migrate       # apply pending Alembic migrations
make revision MSG='...'  # autogenerate migration from model changes
make downgrade / make current

.venv/bin/pytest tests/integration/test_lab_api.py -v
.venv/bin/pytest tests/integration/test_lab_api.py::TestLabAPI::test_create_lab_success -v
```
**Python**: 3.12+ | **Test DB**: PostgreSQL `localhost:5433`

## Architecture
FastAPI + async SQLAlchemy 2.0, Domain-Driven Design, four-layer structure per domain (`user`, `university`, `lab`, `category`, `product`, `tag`):

| Layer | File | Role |
|---|---|---|
| API | `app/api/v1/<domain>.py` | Routes, rate limiting, `Depends()` |
| Service | `app/domain/<domain>/service.py` | Business logic, permissions, orchestration |
| Repository | `app/domain/<domain>/repository.py` | Async SQLAlchemy queries, wraps errors |
| Model/Schema | `app/domain/<domain>/model.py` + `schema.py` | ORM models + Pydantic I/O |

**Shared infra:**
- `app/common/base_repository.py` — `BaseRepository[T,S,C]`: `get_by_id`, `get_all`, `create`, `update`, `delete_by_id`, `soft_delete`. Composite-PK models use a plain class.
- `app/exceptions/exceptions.py` — `NotFoundError`, `ValidationError`, `DatabaseError`, `RepositoryError`, `ExternalServiceError` with centralized handlers.
- `app/api/dependencies/` — `services.py` composes repos into services; `auth.py` provides `get_current_user()` / `require_admin_user()`.
- `app/core/config.py` — Pydantic Settings from `.env`.

**Auth:** JWT in HTTP-only cookies. `get_current_user()` validates token; `require_admin_user()` enforces `role == ADMIN`.

**Schemas:** All extend `CamelModel` (snake_case → camelCase). Input: `XxxSchema` (external) / `XxxCreateDBSchema` (internal). Output: `XxxOutSchema`.

## Transaction Management
- `session_scope` never commits — services own `commit()`.
- Repos only `flush()` + `refresh()`, never `commit()`.
- Multi-step atomic ops call internal helpers directly (not public service methods that each commit).

## Migrations
After any ORM model change run `make revision MSG='...'`, never write migration files by hand. Import every model in `alembic/env.py` for autogenerate to detect it.

## Domain / Model Rules
- `Category` in `category/model.py`; `lab_category` association table in `lab/model.py`.
- Profile/extension tables belong in their parent domain file.
- Never use `relationship()` when a join table exists — query explicitly.
- Repos return ORM objects only. Services own `commit()`, `refresh()`, and `model_validate()`.
- ORM → schema with extra fields: `result = OutSchema.model_validate(obj, from_attributes=True)` then set extras. Never `**schema.model_dump()`.
- Many-to-many updates: `sync_association()` from `app/common/db_utils.py` — called from service, not repo.
- Association tables: ORM classes extending `Base, TimestampMixin` with `PrimaryKeyConstraint`.
- Out schemas belong to their own domain.
- No wrapper repo methods (e.g. `create_for_product`). Services call `repo.create()` / `repo.update_instance()` with a dict directly.
- Repos are pure data access — no orchestration, no cross-repo calls, no `get_or_create`.
- Never create categories as a side effect — clients pass `category_ids` only.
- Use mapped model attributes in ORM queries; `__table__.c` only for SQLAlchemy Core access.

## Soft Delete
Main domain tables only (e.g. `Product`, `Article`, `Broadcast`) — add `SoftDeleteMixin`. `get_by_id`, `get_all`, `update` auto-exclude soft-deleted rows; all other custom queries add `.where(Model.deleted_at.is_(None))`. Services call `repo.soft_delete()`.

## Avoiding N+1 Queries
- No per-row DB calls inside loops. Plural batch methods (`get_x(ids) -> dict[int, ...]`) hold the SQL; singular methods delegate to plural.
- In service `list()`: fetch IDs → call batch methods once each → assemble schemas with no DB calls inside.

## Pagination
Wire `limit`/`offset`: Query param → service → `repo.get_all()`. Defaults (`limit=50`, `offset=0`) only in the endpoint.

## Uniqueness Constraints
Never pre-check uniqueness — race condition. Let the DB constraint guard. `BaseRepository` catches `IntegrityError` → `ValidationError` (400).

## List Endpoint Performance
- Use `SummarySchema` + `load_only(...)` in repo — heavy columns never fetched.
- Never `asyncio.gather()` multiple queries on the same `AsyncSession` — concurrent ops on one session raise `IllegalStateChangeError`. Await DB queries sequentially; only `gather()` work that uses separate sessions or no DB (e.g. Redis).
- Redis: serialize with `model_dump(mode="json")`. Cache anonymous responses only; admins bypass. Invalidate with `redis.delete_by_pattern(f"{PREFIX}:*")` on writes.
- Index columns used for filtering/sorting. Use `EXPLAIN (ANALYZE, BUFFERS)` to confirm index scans.
- Consolidate `COUNT(*)` calls with `COUNT(*) FILTER (WHERE ...)` aggregates.

## File Upload / R2 Storage
- `R2StorageService` (`app/common/storage.py`) — inject via `get_storage_service()`, pass as method arg.
- Order: validate → upload R2 → insert DB → commit. R2 failure raises 502 before any DB write.
- Store `storage_key` in DB; compute URL via `settings.r2.cdn_base_url`.
- `sort_order`: `get_max_sort_order()` + 10 when not provided.
- Env vars: `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_ENDPOINT`, `R2_BUCKET`, `R2_CDN_BASE_URL`.

## Testing
Async integration tests in `tests/integration/`. Real test Postgres DB (tables created/dropped per session). `FakeEmailService` overrides SMTP. `client` fixture uses `AsyncClient` with auth dependency overrides. Classes named `TestXxxAPI`; cover success + error cases (404, 422, 403).

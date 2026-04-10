# Redis Caching Strategy

## Overview

This document defines the backend Redis caching strategy for list endpoints. Redis is already provisioned for rate limiting — this extends its use to response caching.

Frontend uses Tanstack Query for client-side state management. This strategy is independent of that and focuses solely on server-side API response caching.

---

## Endpoint Classification

| Endpoint | Cache Type | Reason |
|---|---|---|
| `GET /api/v1/university` | Global | Public, admin-managed, rarely changes |
| `GET /api/v1/lab` | Global | Public, admin-managed, rarely changes |
| `GET /api/v1/category` | Global | Admin-only writes, very static |
| `GET /api/v1/product` (unauthenticated) | Global | Public, filterable by status |
| `GET /api/v1/product` (authenticated) | **Skip** | Includes per-user voted/bookmarked flags |
| `GET /api/v1/product/me` | User-specific | Per-user owned products |
| `GET /api/v1/product/me/voted` | User-specific | Per-user interaction data |
| `GET /api/v1/product/me/bookmarked` | User-specific | Per-user interaction data |
| `GET /api/v1/product/{id}/comments` | Global | Public, keyed by product_id |
| `GET /api/v1/paper` (unauthenticated) | Global | Public, filterable by verification_status |
| `GET /api/v1/paper` (authenticated) | **Skip** | Includes per-user flags |
| `GET /api/v1/paper/me` | User-specific | Per-user owned papers |
| `GET /api/v1/paper/{id}/related` | Global | Public, keyed by paper_id |
| `GET /api/v1/user` | **Skip** | Admin only, sensitive data |

---

## Cache Key Scheme

**Pattern:** `{domain}:list:{sorted_params}`

All query parameters are sorted alphabetically and concatenated. `None` values are written explicitly — never omitted — to avoid key ambiguity.

### Global List Keys

```
university:list:limit=50:offset=0
lab:list:limit=20:offset=0
category:list:limit=50:offset=0
product:list:limit=50:offset=0:status=None
product:list:limit=50:offset=0:status=published
product:comments:id=42:limit=50:offset=0
paper:list:limit=50:offset=0:verification_status=None
paper:list:limit=50:offset=0:verification_status=verified
paper:related:id=7:limit=5:offset=0
```

### User-Specific Keys

Prefix: `user:{user_id}:`

```
user:12:product:list:limit=50:offset=0:status=None
user:12:product:voted:limit=50:offset=0
user:12:product:bookmarked:limit=50:offset=0
user:12:paper:list:limit=50:offset=0
```

---

## TTL Strategy

| Endpoint Category | TTL | Rationale |
|---|---|---|
| University, Lab | 10 min | Admin-managed, very infrequent writes |
| Category | 15 min | Extremely static, admin-only |
| Product list (global/anon) | 2 min | Votes and bookmarks change frequently |
| Product comments | 1 min | High write frequency |
| Paper list (global/anon) | 5 min | Moderately dynamic |
| Paper related | 10 min | Computed relation, stable |
| User-specific lists (`/me/*`) | 2 min | Short TTL for per-user freshness |

---

## Cache-Aside Read Pattern

Every cached endpoint follows this flow:

```
1. Build deterministic cache key from request params
2. GET key from Redis
3. HIT  → deserialize JSON → return immediately (no DB hit)
4. MISS → execute service/DB query
5.       → serialize result to JSON → SET key with TTL
6.       → return result
```

**Serialization:** Each Pydantic schema in the response list is serialized via `.model_dump()` → `json.dumps()` before writing to Redis. On read, `json.loads()` produces a list of dicts which FastAPI returns directly as JSON without re-validation overhead.

---

## Invalidation Strategy

On any write operation, invalidate all cache keys matching the affected domain pattern. Use Redis `SCAN` + `UNLINK` (non-blocking delete) with a glob pattern.

| Write Event | Patterns to Invalidate |
|---|---|
| Product create / update / delete | `product:list:*` |
| Product vote (toggle) | `product:list:*`, `user:{voter_id}:product:voted:*` |
| Product bookmark (toggle) | `product:list:*`, `user:{user_id}:product:bookmarked:*` |
| Comment create | `product:comments:id={product_id}:*` |
| Paper create / update / delete | `paper:list:*`, `paper:related:*` |
| Paper verification status update | `paper:list:*` |
| Lab create / update / delete | `lab:list:*` |
| University create / update / delete | `university:list:*` |
| Category create / update / delete | `category:list:*` |

Invalidation runs **after** a write succeeds — never before.

---

## Architecture Placement

**Cache logic lives in the API layer (route handlers).**

The API layer is the correct home because:
- All key-building inputs (`limit`, `offset`, filters, `current_user`) are already in scope at the route handler
- Services remain pure — no Redis dependency injected into the service layer
- Invalidation naturally pairs with write handlers: after the service call commits, the handler fires cache busts
- Cache misses fall through to the existing service call with no service changes required

**Read flow** (in route handler):
```
check cache → hit? return → miss? call service → cache result → return
```

**Write flow** (in route handler):
```
call service → success? invalidate affected patterns → return
```

---

## User-Specific Flag Problem

Product and paper list responses for authenticated users include per-user fields (`voted`, `bookmarked`, `interested`). These differ per user and cannot be globally cached.

**Decision: skip global cache for authenticated list requests.**

- Anonymous requests to `GET /product` and `GET /paper` → globally cached (no user flags present)
- Authenticated requests to the same endpoints → bypass cache, always hit DB
- `/me/*` endpoints → user-keyed cache with 2-minute TTL

This avoids a two-layer merge approach (cache base list + user flags separately then combine), which would require two Redis lookups and a join in application code — adding complexity that erodes the caching benefit.

---

## Key Building Rules

1. Sort all params alphabetically before joining
2. Include `None` values explicitly: `status=None` not omitted
3. Use `:` as separator between param pairs
4. Domain prefix uses `:list:` for collection endpoints, domain-specific suffix for sub-resources (`:comments:`, `:voted:`, `:bookmarked:`, `:related:`)
5. User-scoped keys always start with `user:{user_id}:`

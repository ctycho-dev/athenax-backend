# Internal Service API

Service-to-service endpoints used by internal workers and bots. No user session required — callers authenticate with a shared secret header instead.

---

## Authentication

Every request to `/api/v1/internal/*` must include:

```
X-Internal-Key: <secret>
```

Missing or wrong key → **401 Unauthorized**.

The secret is configured via the `INTERNAL_API_KEY` environment variable. If the variable is empty or unset, **all internal endpoints reject every request** by default — they never open up accidentally.

Generate a key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Endpoints

Base path: `/api/v1/internal`

### Create product

```
POST /internal/products
X-Internal-Key: <secret>
Content-Type: application/json

{ "name": "AlphaFold 3", "categoryIds": [3], ... }
```

- Uses the same flow as user product submission.
- `created_by_id` is set to the system user (see [System User](#system-user)).
- Status is always **PENDING** — requires the normal admin approval flow to go live.
- Returns `ProductOutSchema` (201).

### Get category by name

```
GET /internal/categories/by-name?name=Biotech
X-Internal-Key: <secret>
```

Exact match, case-insensitive. Returns `CategoryOutSchema` (200) or 404.  
Only matches **parent** categories (no `parent_id`).

### Get subcategory by name

```
GET /internal/subcategories/by-name?name=Gene Editing
X-Internal-Key: <secret>
```

Exact match, case-insensitive. Returns `CategoryOutSchema` (200) or 404.  
Only matches **subcategories** (has a `parent_id`).

### Get product by name

```
GET /internal/products/by-name?name=AlphaFold 3
X-Internal-Key: <secret>
```

Exact match, case-insensitive. Returns `ProductOutSchema` (200) or 404.  
Returns products of **any status** including PENDING — the public API only returns APPROVED products, but internal callers are trusted.

---

## Typical workflow

```
1. Resolve category
   GET /internal/categories/by-name?name=Biotech
   → 200 { "id": 3, ... }          # use id in step 3
   → 404                            # admin must create this category first

2. Check if product already exists
   GET /internal/products/by-name?name=AlphaFold 3
   → 200 { "id": 42, "status": "pending", ... }   # already tracked, stop here
   → 404                                           # not found, create it

3. Create product
   POST /internal/products
   { "name": "AlphaFold 3", "categoryIds": [3] }
   → 201 { "id": 99, "status": "pending", "createdById": <system_user_id>, ... }
```

---

## System User

A dedicated database user owns everything created through these endpoints:

| Field           | Value                      |
|-----------------|----------------------------|
| `email`         | `system@athenax.internal`  |
| `role`          | `system`                   |
| `password_hash` | `!` (can never match bcrypt) |
| `verified`      | `false` (cannot log in)    |

Seeded by migration `e2b3c4d5f6a7`. To find everything the system user created:

```sql
SELECT * FROM products WHERE created_by_id = (
    SELECT id FROM users WHERE email = 'system@athenax.internal'
);
```

---

## BD Role

Users with role `bd` (business development) have admin-equivalent access to **all existing endpoints** — same as `admin`. BD users authenticate normally via JWT cookie; they do not use the internal key.

---

## Rate Limiting

60 requests / minute per IP. There is no logged-in user on internal requests, so the limiter uses the caller's IP address.

---

## Security Notes

- The key comparison uses `secrets.compare_digest` (constant-time) to prevent timing attacks.
- Rotate `INTERNAL_API_KEY` if it is ever exposed — update the env var and restart the service.
- The system user cannot log in through the normal auth flow regardless of the key value.
- Categories are **not** created as a side effect of product creation. The internal service must resolve a category ID before submitting a product; if the category doesn't exist, an admin must create it via the normal API.

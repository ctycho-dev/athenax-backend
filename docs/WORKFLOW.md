# Backend Workflow

This document collects the main day-to-day steps for this backend in one place.

## Available roles

| Role       | Value        | Profile table         |
| ---------- | ------------ | --------------------- |
| Admin      | `admin`      | —                     |
| User       | `user`       | —                     |
| Researcher | `researcher` | `researcher_profiles` |
| Sponsor    | `sponsor`    | `sponsor_profiles`    |
| Founder    | `founder`    | —                     |
| Investor   | `investor`   | `investor_profiles`   |

---


## Public signup flow

This is the flow the frontend should use for first-time user registration.

1. The frontend sends `POST /api/v1/user/signup`
2. The password is saved in a secure hashed form
3. The new user is stored in the database
4. The role from the request body is stored as part of the new user
5. If role-specific profile data is included in the request body, the profile is created in the **same transaction** as the user
6. The API sends a verification email to the user
7. The response tells the user to verify their email before logging in

### Signup response

```json
{
  "message": "Signup successful. Please verify your email."
}
```

### Signup request — basic user

```bash
curl -X POST "${API_URL}/api/v1/user/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "${NAME}",
    "email": "${EMAIL}",
    "password": "${PASSWORD}",
    "role": "user"
  }'
```

### Signup request — investor with inline profile

```bash
curl -X POST "${API_URL}/api/v1/user/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "${NAME}",
    "email": "${EMAIL}",
    "password": "${PASSWORD}",
    "role": "investor",
    "investorProfile": {
      "investorType": "Angel",
      "balance": 500000
    }
  }'
```

### Signup request — researcher with inline profile

```bash
curl -X POST "${API_URL}/api/v1/user/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "${NAME}",
    "email": "${EMAIL}",
    "password": "${PASSWORD}",
    "role": "researcher",
    "researcherProfile": {
      "labId": 1,
      "bio": "PhD candidate in machine learning"
    }
  }'
```

### Signup request — sponsor with inline profile

```bash
curl -X POST "${API_URL}/api/v1/user/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "${NAME}",
    "email": "${EMAIL}",
    "password": "${PASSWORD}",
    "role": "sponsor",
    "sponsorProfile": {
      "bio": "We fund deep-tech startups",
      "amount": 1000000
    }
  }'
```

---

## Email verification flow

This is the flow that starts when the user clicks the verification link in their inbox.

1. The email link opens `GET /api/v1/user/verify-email?token=...`
2. The backend verifies the token and marks the user as verified
3. The backend creates a JWT access token
4. The token is returned in an HTTP-only cookie
5. The user is now signed in and can continue into the app

### Verification response

```json
{
  "message": "Email verified successfully."
}
```

---

## Login flow

1. The frontend sends `POST /api/v1/user/login`
2. The backend checks the credentials
3. A JWT access token is created
4. The token is returned and also stored in an HTTP-only cookie

### Login request example

```bash
curl -X POST "${API_URL}/api/v1/user/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=${EMAIL}&password=${PASSWORD}"
```

### Login response

```json
{
  "access_token": "jwt-token-here",
  "token_type": "bearer"
}
```

---

## Get user with profile

`GET /api/v1/user/{user_id}` returns the user plus any role-specific profile and categories.

### Response shape

```json
{
  "id": 1,
  "name": "Jane Smith",
  "email": "jane@example.com",
  "role": "investor",
  "externalId": null,
  "verified": true,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "investorProfile": {
    "userId": 1,
    "investorType": "Angel",
    "balance": 500000,
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-01-01T00:00:00Z"
  },
  "researcherProfile": null,
  "sponsorProfile": null,
  "categories": [{ "categoryId": 3 }]
}
```

---

## Role-specific profile flow

Profiles can be created or updated after signup via dedicated endpoints. All profile endpoints are upserts (create on first call, update on subsequent calls).

### Investor profile

```bash
# Create / update
curl -X POST "${API_URL}/api/v1/user/${USER_ID}/investor-profile" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"investorType": "Venture Capital", "balance": 2000000}'

# Read
curl -X GET "${API_URL}/api/v1/user/${USER_ID}/investor-profile" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Researcher profile

```bash
# Create / update
curl -X POST "${API_URL}/api/v1/user/${USER_ID}/researcher-profile" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"labId": 1, "bio": "Researching LLM alignment"}'

# Read
curl -X GET "${API_URL}/api/v1/user/${USER_ID}/researcher-profile" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Sponsor profile

```bash
# Create / update
curl -X POST "${API_URL}/api/v1/user/${USER_ID}/sponsor-profile" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"bio": "Supporting AI safety research", "amount": 50000}'

# Read
curl -X GET "${API_URL}/api/v1/user/${USER_ID}/sponsor-profile" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

---

## User categories flow

Users can be linked to many categories (many-to-many via `user_category` table).

```bash
# Set categories (replaces all existing)
curl -X POST "${API_URL}/api/v1/user/${USER_ID}/categories" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"categoryIds": [1, 2, 3]}'

# Get categories
curl -X GET "${API_URL}/api/v1/user/${USER_ID}/categories" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"

# Remove a single category
curl -X DELETE "${API_URL}/api/v1/user/${USER_ID}/categories/2" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Categories response shape

```json
[{ "categoryId": 1 }, { "categoryId": 3 }]
```

---

## Category CRUD flow

Categories are a managed resource. Read endpoints are public. `POST`, `PATCH`, and `DELETE` require the `admin` role.

### Category response shape

```json
{
  "id": 1,
  "name": "Machine Learning"
}
```

### Category create request example

```bash
curl -X POST "${API_URL}/api/v1/category" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"name": "Machine Learning"}'
```

### Category list request example

```bash
curl -X GET "${API_URL}/api/v1/category?limit=50&offset=0" \
  -H "Accept: application/json"
```

### Category get request example

```bash
curl -X GET "${API_URL}/api/v1/category/1" \
  -H "Accept: application/json"
```

### Category update request example

```bash
curl -X PATCH "${API_URL}/api/v1/category/1" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"name": "Deep Learning"}'
```

### Category delete request example

```bash
curl -X DELETE "${API_URL}/api/v1/category/1" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

---

## University CRUD flow

Universities expose public read endpoints and admin-only write endpoints.

1. The frontend sends `POST /api/v1/university`
2. The backend creates the university record
3. The frontend can list, read, update, and delete universities with the matching `/api/v1/university` routes
4. `GET /api/v1/university` and `GET /api/v1/university/{university_id}` are public
5. `POST`, `PATCH`, and `DELETE` require an authenticated user with the `admin` role

### University create request example

```bash
curl -X POST "${API_URL}/api/v1/university" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "name": "University of California",
    "country": "USA",
    "focus": "Research"
  }'
```

### University list request example

```bash
curl -X GET "${API_URL}/api/v1/university?limit=50&offset=0" \
  -H "Accept: application/json"
```

### University get request example

```bash
curl -X GET "${API_URL}/api/v1/university/1" \
  -H "Accept: application/json"
```

### University update request example

```bash
curl -X PATCH "${API_URL}/api/v1/university/1" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "focus": "Applied Research"
  }'
```

### University delete request example

```bash
curl -X DELETE "${API_URL}/api/v1/university/1" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

---

## Lab CRUD flow

Labs expose public read endpoints and admin-only write endpoints. Labs support many-to-many categories.

1. The frontend sends `POST /api/v1/lab`
2. The backend creates the lab record linked to a university
3. Categories can be linked by existing ID (`categoryIds`) or created inline by name (`newCategories`)
4. The frontend can list, read, update, and delete labs with the matching `/api/v1/lab` routes
5. `GET /api/v1/lab` and `GET /api/v1/lab/{lab_id}` are public
6. `POST`, `PATCH`, and `DELETE` require an authenticated user with the `admin` role

### Lab response shape

```json
{
  "id": 1,
  "universityId": 1,
  "name": "AI Research Lab",
  "focus": "Machine Learning",
  "description": "Computer vision and applied ML projects",
  "categories": [
    { "id": 1, "name": "Robotics" },
    { "id": 2, "name": "Computer Vision" }
  ],
  "active": true,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### Lab create request example

`categoryIds` links existing categories by ID. `newCategories` creates new categories by name (optional, both default to empty).

```bash
curl -X POST "${API_URL}/api/v1/lab" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "universityId": 1,
    "name": "AI Research Lab",
    "focus": "Machine Learning",
    "description": "Computer vision and applied ML projects",
    "categoryIds": [1, 2],
    "newCategories": ["Robotics", "Computer Vision"],
    "active": true
  }'
```

### Lab list request example

```bash
curl -X GET "${API_URL}/api/v1/lab?limit=50&offset=0" \
  -H "Accept: application/json"
```

### Lab get request example

```bash
curl -X GET "${API_URL}/api/v1/lab/1" \
  -H "Accept: application/json"
```

### Lab update request example

```bash
curl -X PATCH "${API_URL}/api/v1/lab/1" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "active": false,
    "description": "Paused until the next intake"
  }'
```

### Lab delete request example

```bash
curl -X DELETE "${API_URL}/api/v1/lab/1" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

---

## Paper CRUD + voting flow

Papers are researcher-created resources with many-to-many categories and a vote count. `POST` requires the `researcher` role. `PATCH` and `DELETE` require ownership or `admin`. Read endpoints are public.

### Paper response shape

```json
{
  "id": 1,
  "userId": 1,
  "productId": null,
  "title": "Attention Is All You Need",
  "slug": "attention-is-all-you-need",
  "abstract": "We propose a new network architecture...",
  "status": "published",
  "publishedAt": "2026-01-01T00:00:00Z",
  "sourceType": "external",
  "externalUrl": "https://arxiv.org/abs/1706.03762",
  "content": null,
  "voteCount": 42,
  "categories": [{ "id": 1, "name": "Machine Learning" }],
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### Paper create request example — external source

```bash
curl -X POST "${API_URL}/api/v1/paper" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "title": "Attention Is All You Need",
    "sourceType": "link",
    "externalUrl": "https://arxiv.org/abs/1706.03762",
    "status": "draft",
    "categoryIds": [1, 2]
  }'
```

### Paper create request example — hosted content

```bash
curl -X POST "${API_URL}/api/v1/paper" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "title": "My Research Paper",
    "sourceType": "editor",
    "abstract": "This paper explores...",
    "content": "Full paper body goes here...",
    "status": "draft",
    "categoryIds": [1, 2]
  }'
```

### Paper list request example

```bash
curl -X GET "${API_URL}/api/v1/paper?limit=50&offset=0" \
  -H "Accept: application/json"
```

### Paper get request example

```bash
curl -X GET "${API_URL}/api/v1/paper/1" \
  -H "Accept: application/json"
```

### Paper update request example

```bash
curl -X PATCH "${API_URL}/api/v1/paper/1" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "status": "published",
    "categoryIds": [1, 3]
  }'
```

### Paper delete request example

```bash
curl -X DELETE "${API_URL}/api/v1/paper/1" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Paper vote request example

`voted: true` adds a vote, `voted: false` removes it. Duplicate votes are silently ignored.

```bash
curl -X PUT "${API_URL}/api/v1/paper/1/vote" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"voted": true}'
```

---

## Product CRUD + interactions flow

Products are founder-created resources with many-to-many categories, vote counts, bookmark counts, investor interest counts, and comments. `POST`, `PATCH`, and `DELETE` require the `founder` or `admin` role (with ownership enforced on `PATCH`/`DELETE`). Investor interest requires the `investor` role.

### Verification / approval workflow

Every product starts with `status: "pending"` and must be approved by an admin before it appears publicly. The possible statuses are:

| Status     | Meaning                                |
| ---------- | -------------------------------------- |
| `pending`  | Newly submitted, awaiting admin review |
| `approved` | Visible to everyone                    |
| `rejected` | Not visible publicly                   |

**Visibility rules:**

| Caller                      | What they see                                                                                  |
| --------------------------- | ---------------------------------------------------------------------------------------------- |
| Unauthenticated / non-admin | Approved products only, regardless of any `?status=` param passed                              |
| Admin                       | Any status via `?status=pending/approved/rejected`, or all products when `?status=` is omitted |
| Founder (`GET /me`)         | All of their own products across all statuses (pending, approved, rejected)                    |

**All interactions (vote, bookmark, investor interest, and comments) are blocked on non-approved products** — they return 404.

### Product list response shape

Returned by `GET /api/v1/product`. Includes `github`, `demo`, and `bookmarked` when the caller is authenticated (otherwise `bookmarked` is `null`).

```json
{
  "id": 1,
  "userId": 1,
  "slug": "axonos",
  "name": "Axonos",
  "description": "An AI-powered research assistant.",
  "stage": "Seed",
  "funding": 500000.0,
  "founded": 2024,
  "github": "https://github.com/org/axonos",
  "demo": "https://axonos.ai",
  "qualityBadge": null,
  "status": "approved",
  "voteCount": 12,
  "bookmarkCount": 5,
  "investorInterestCount": 3,
  "categoryIds": [1, 3],
  "bookmarked": true,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### Product detail response shape

Returned by `GET /api/v1/product/{product_id}` and `GET /api/v1/product/slug/{slug}`. Includes published papers only and user interaction state (`voted`, `bookmarked`, `interested`) when the caller is authenticated (otherwise `null`).

```json
{
  "id": 1,
  "userId": 1,
  "slug": "axonos",
  "name": "Axonos",
  "description": "An AI-powered research assistant.",
  "stage": "Seed",
  "funding": 500000.0,
  "founded": 2024,
  "github": "https://github.com/org/axonos",
  "demo": "https://axonos.ai",
  "qualityBadge": null,
  "status": "approved",
  "voteCount": 12,
  "bookmarkCount": 5,
  "investorInterestCount": 3,
  "categoryIds": [1, 3],
  "papers": [
    {
      "id": 7,
      "title": "Attention Is All You Need",
      "slug": "attention-is-all-you-need",
      "publishedAt": "2026-01-01T00:00:00Z"
    }
  ],
  "voted": false,
  "bookmarked": true,
  "interested": null,
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### Product create request example

Newly created products always start as `pending`. The backend generates `slug` from `name`.

```bash
curl -X POST "${API_URL}/api/v1/product" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "name": "Axonos",
    "description": "An AI-powered research assistant.",
    "stage": "Seed",
    "funding": 500000,
    "founded": 2024,
    "github": "https://github.com/org/axonos",
    "demo": "https://axonos.ai",
    "qualityBadge": "Top Rated",
    "categoryIds": [1, 2]
  }'
```

### Product list request example

Default returns approved products only. Admins can filter by status or omit `status` to get all.

```bash
# Public — approved products only
curl -X GET "${API_URL}/api/v1/product?limit=50&offset=0" \
  -H "Accept: application/json"

# Admin — pending products
curl -X GET "${API_URL}/api/v1/product?status=pending" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"

# Admin — all products regardless of status
curl -X GET "${API_URL}/api/v1/product" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### My products request example (founder)

Requires `founder` or `admin` role. Returns all of the caller's own products across all statuses. Supports the same `limit`, `offset`, and `status` query params.

```bash
# All statuses
curl -X GET "${API_URL}/api/v1/product/me" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"

# Filter to pending only
curl -X GET "${API_URL}/api/v1/product/me?status=pending" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Product get request example

Returns 404 for non-approved products.

```bash
curl -X GET "${API_URL}/api/v1/product/1" \
  -H "Accept: application/json"
```

### Product get by slug request example

Returns full detail including linked papers and user interaction state. Pass the auth cookie to get `voted`/`bookmarked`/`interested`.

```bash
# Unauthenticated — interaction fields are null
curl -X GET "${API_URL}/api/v1/product/slug/axonos" \
  -H "Accept: application/json"

# Authenticated — interaction fields populated
curl -X GET "${API_URL}/api/v1/product/slug/axonos" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Product update request example

```bash
curl -X PATCH "${API_URL}/api/v1/product/1" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "stage": "Series A",
    "funding": 2000000
  }'
```

### Product delete request example

```bash
curl -X DELETE "${API_URL}/api/v1/product/1" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

### Product status update request example

Admin-only. Sets the product status to `approved` or `rejected`.

```bash
curl -X PATCH "${API_URL}/api/v1/product/1/status" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"status": "approved"}'
```

### Product vote request example

`voted: true` adds a vote, `voted: false` removes it. Duplicate votes are silently ignored. Any authenticated user can vote. Returns 404 on non-approved products.

```bash
curl -X PUT "${API_URL}/api/v1/product/1/vote" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"voted": true}'
```

### Product bookmark request example

`bookmarked: true` adds a bookmark, `bookmarked: false` removes it. Any authenticated user can bookmark. Returns 404 on non-approved products.

```bash
curl -X PUT "${API_URL}/api/v1/product/1/bookmark" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"bookmarked": true}'
```

### Product investor interest request example

`interested: true` marks interest, `interested: false` removes it. Requires `investor` role. Returns 404 on non-approved products.

```bash
curl -X PUT "${API_URL}/api/v1/product/1/interest" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"interested": true}'
```

---

## Product comments flow

Comments are scoped to a product. Any authenticated user can create a comment. Only the comment owner or an admin can update or delete a comment. The list endpoint is public. All comment endpoints return 404 for non-approved products.

### Comment response shape

```json
{
  "id": 1,
  "productId": 1,
  "userId": 1,
  "text": "This looks promising!",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

### List comments request example

```bash
curl -X GET "${API_URL}/api/v1/product/1/comments?limit=50&offset=0" \
  -H "Accept: application/json"
```

### Create comment request example

```bash
curl -X POST "${API_URL}/api/v1/product/1/comments" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"text": "This looks promising!"}'
```

### Update comment request example

```bash
curl -X PATCH "${API_URL}/api/v1/product/1/comments/1" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{"text": "Updated thoughts."}'
```

### Delete comment request example

```bash
curl -X DELETE "${API_URL}/api/v1/product/1/comments/1" \
  -H "Cookie: access_token=${ACCESS_TOKEN}"
```

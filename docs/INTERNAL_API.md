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
```

- Uses the same flow as user product submission.
- `created_by_id` is set to the system user (see [System User](#system-user)).
- Status is always **PENDING** — requires the normal admin approval flow to go live.
- Returns `ProductOutSchema` (201).

#### Request body

All field names are **camelCase** in JSON. Only `name` is required; every other field defaults to `null` or `[]` if omitted.

| Field | JSON type | Required | Constraints | Description |
|---|---|---|---|---|
| `name` | string | **yes** | max 150 chars | Product display name |
| `url` | string or null | no | max 500 chars | Primary website URL |
| `shortDesc` | string or null | no | max 150 chars | One-line tagline shown in listing cards |
| `description` | string or null | no | — | Long-form description; markdown supported |
| `stage` | string or null | no | see allowed values below | Funding / development stage |
| `funding` | number or null | no | — | Total raised in USD as a plain number (e.g. `5000000` for $5 M) |
| `founded` | integer or null | no | — | Year the company was founded (e.g. `2021`) |
| `logo` | string or null | no | max 500 chars | Absolute URL to a logo image |
| `email` | string or null | no | max 200 chars | Public contact email |
| `backers` | array of strings | no | — | VC / investor names as plain strings (e.g. `["a16z", "Sequoia"]`) |
| `grants` | array of strings | no | — | Grant names as plain strings (e.g. `["NSF SBIR", "DARPA"]`) |
| `links` | array of link objects | no | — | Social and technical links; see link object schema below |
| `team` | array of team member objects | no | — | Founding / core team members; see team member object schema below |
| `categoryIds` | array of integers | no | — | Parent-category IDs; resolve first via `GET /internal/categories/by-name` |
| `subCategoryIds` | array of integers | no | — | Subcategory IDs; resolve first via `GET /internal/subcategories/by-name` |
| `otherSubcategoryName` | string or null | no | max 100 chars | Free-text subcategory suggestion when no existing one matches |
| `imported` | boolean | no | default `false` | Set to `true` for all agent-imported records so they are distinguishable from user submissions |
| `qualityBadge` | string or null | no | max 50 chars | Admin-controlled quality label — agents should leave this null |

##### Allowed values for `stage`

Exactly one of the following strings (case-sensitive):

| Value | Meaning |
|---|---|
| `"Pre-Seed"` | Pre-seed funding round |
| `"Seed"` | Seed round |
| `"Series A"` | Series A |
| `"Series B"` | Series B or later |
| `"Beta"` | Product in public or private beta |
| `"Launched"` | Publicly launched |
| `"Active"` | Actively operating |
| `"Active Development"` | Under active development, not yet launched |
| `"Acquired / Operating"` | Acquired but still operating |

##### Link object schema (each item in `links`)

| Field | JSON type | Required | Constraints | Description |
|---|---|---|---|---|
| `linkType` | string | **yes** | see allowed values below | Category of link |
| `url` | string | **yes** | max 500 chars | Full URL including scheme |
| `label` | string or null | no | max 100 chars | Optional display label shown in the UI |

Allowed values for `linkType` (case-sensitive):

| Value | Use for |
|---|---|
| `"website"` | Main product / company website |
| `"github"` | GitHub repository |
| `"twitter"` | Twitter / X profile |
| `"docs"` | Documentation site |
| `"demo"` | Live demo |
| `"discord"` | Discord server |
| `"linkedin"` | LinkedIn company page |
| `"youtube"` | YouTube channel or video |
| `"instagram"` | Instagram profile |
| `"telegram"` | Telegram channel or group |
| `"medium"` | Medium blog |
| `"tiktok"` | TikTok profile |
| `"other"` | Any other link |

##### Team member object schema (each item in `team`)

| Field | JSON type | Required | Constraints | Description |
|---|---|---|---|---|
| `name` | string | **yes** | max 100 chars | Full name of the team member |
| `roleLabel` | string or null | no | max 150 chars | Title or role (e.g. `"CEO"`, `"CTO"`) |
| `bioNote` | string or null | no | max 300 chars | Short bio or note about this person |
| `linkedinUrl` | string or null | no | max 200 chars | LinkedIn profile URL |
| `twitterUrl` | string or null | no | max 200 chars | Twitter / X profile URL |
| `githubUrl` | string or null | no | max 200 chars | GitHub profile URL |
| `otherUrl` | string or null | no | max 200 chars | Any other relevant URL |

Team members are created with status `"pending"` and go through the same admin approval flow as the product itself.

#### BD agent field mapping

| Agent collects | Field to populate | Example |
|---|---|---|
| GitHub repository URL | `links` — one object with `linkType: "github"` | `{ "linkType": "github", "url": "https://github.com/org/repo" }` |
| GitHub stars | Embed in `description` — there is no dedicated field | `"description": "... GitHub stars: 12 000+"` |
| Twitter / X handle | `links` — one object with `linkType: "twitter"` | `{ "linkType": "twitter", "url": "https://twitter.com/handle" }` |
| LinkedIn company page URL | `links` — one object with `linkType: "linkedin"` | `{ "linkType": "linkedin", "url": "https://linkedin.com/company/org" }` |
| YouTube channel or video URL | `links` — one object with `linkType: "youtube"` | `{ "linkType": "youtube", "url": "https://youtube.com/@org" }` |
| Instagram profile URL | `links` — one object with `linkType: "instagram"` | `{ "linkType": "instagram", "url": "https://instagram.com/org" }` |
| Telegram channel or group URL | `links` — one object with `linkType: "telegram"` | `{ "linkType": "telegram", "url": "https://t.me/org" }` |
| Medium blog URL | `links` — one object with `linkType: "medium"` | `{ "linkType": "medium", "url": "https://medium.com/@org" }` |
| TikTok profile URL | `links` — one object with `linkType: "tiktok"` | `{ "linkType": "tiktok", "url": "https://tiktok.com/@org" }` |
| VC / investor names | `backers` array of strings | `["Andreessen Horowitz", "Y Combinator"]` |
| Grant / government funding names | `grants` array of strings | `["NSF SBIR", "DARPA"]` |
| Funding stage | `stage` string | `"Seed"` |
| Total funding raised | `funding` number (USD) | `5000000` |

#### Full example

```json
{
  "name": "AlphaFold 3",
  "url": "https://alphafold.ebi.ac.uk",
  "shortDesc": "AI system for protein structure prediction",
  "description": "Predicts the structure of proteins and their interactions with other molecules.\n\nGitHub stars: 12 000+",
  "stage": "Launched",
  "funding": 0,
  "founded": 2020,
  "logo": "https://cdn.example.com/logos/alphafold.png",
  "email": "contact@deepmind.com",
  "backers": ["Google DeepMind"],
  "grants": ["NSF SBIR"],
  "imported": true,
  "categoryIds": [3],
  "subCategoryIds": [14],
  "links": [
    { "linkType": "github",   "url": "https://github.com/google-deepmind/alphafold" },
    { "linkType": "twitter",  "url": "https://twitter.com/DeepMind" },
    { "linkType": "docs",     "url": "https://alphafold.ebi.ac.uk/faq" },
    { "linkType": "linkedin", "url": "https://linkedin.com/company/deepmind" },
    { "linkType": "youtube",  "url": "https://youtube.com/@GoogleDeepMind" }
  ],
  "team": [
    {
      "name": "Demis Hassabis",
      "roleLabel": "CEO",
      "bioNote": "Co-founder of DeepMind, neuroscientist and AI researcher.",
      "linkedinUrl": null,
      "twitterUrl": "https://twitter.com/demishassabis",
      "githubUrl": null,
      "otherUrl": null
    }
  ]
}
```

#### Response body (201 Created)

| Field | JSON type | Description |
|---|---|---|
| `id` | integer | Assigned product ID |
| `slug` | string | URL-safe slug derived from name |
| `name` | string | Product name |
| `shortDesc` | string or null | Tagline |
| `description` | string or null | Full description |
| `stage` | string or null | Funding stage (see allowed values above) |
| `funding` | number or null | Total raised USD |
| `founded` | integer or null | Year founded |
| `logo` | string or null | Logo URL |
| `email` | string or null | Contact email |
| `status` | string | Always `"pending"` for newly created products |
| `imported` | boolean | Whether this was agent-imported |
| `qualityBadge` | string or null | Quality label |
| `voteCount` | integer | Always `0` on creation |
| `bookmarkCount` | integer | Always `0` on creation |
| `investorInterestCount` | integer | Always `0` on creation |
| `categories` | array of objects | Assigned parent categories, each `{ "id": int, "name": string, "subcategories": [...] }`. Each subcategory is `{ "id": int, "name": string, "status": "approved" \| "pending" }` — a subcategory created via `otherSubcategoryName` appears here with `status: "pending"` until an admin approves it. |
| `links` | array of link objects | Links as submitted |
| `backers` | array of objects | Each: `{ "id": int, "productId": int, "name": string }` |
| `grants` | array of objects | Each: `{ "id": int, "productId": int, "name": string }` |
| `createdById` | integer or null | System user ID |
| `createdAt` | string (ISO 8601) | Creation timestamp |
| `updatedAt` | string (ISO 8601) | Last-updated timestamp |
| `papers` | array | Always `[]` on creation |
| `media` | array | Always `[]` on creation |
| `team` | array | Team members as submitted with status `"pending"`; each object matches `TeamMemberOutSchema` |
| `voices` | array | Always `[]` on creation |
| `bounties` | array | Always `[]` on creation |
| `founder` | object or null | Always `null` for system-created products |
| `voted` | null | Not applicable for internal callers |
| `bookmarked` | null | Not applicable for internal callers |
| `interested` | null | Not applicable for internal callers |

### Update product

```
PATCH /internal/products/{productId}
X-Internal-Key: <secret>
Content-Type: application/json
```

- Partial update — only send the fields you want to change. Same field set as [create product](#create-product) (all optional), plus JSON `null` is not the same as omitting a field: omitted fields are left untouched, arrays sent as `[]` clear that relation (e.g. `"links": []` removes all links).
- Not restricted to system-created products — the internal caller may update any product regardless of who created it.
- `links`, `backers`, `grants` are replaced wholesale when included (existing rows not in the payload are deleted).
- `categoryIds` / `subCategoryIds` re-sync category assignments the same way as on create.
- Returns `ProductOutSchema` (200), same shape as the create response.

#### Example

```json
PATCH /internal/products/99
{ "funding": 6500000, "stage": "Series A" }
```

### Add media (by storage key)

```
POST /internal/products/{productId}/media
X-Internal-Key: <secret>
Content-Type: application/json
```

Use when the file has already been uploaded to R2 by another process and you just need to register it against the product.

| Field | JSON type | Required | Constraints | Description |
|---|---|---|---|---|
| `mediaType` | string | **yes** | e.g. `"image"` | Media type enum value |
| `storageKey` | string | **yes** | max 500 chars | R2 object key (not a full URL) |
| `sortOrder` | integer | no | default `0` | Display order, ascending |

Returns `ProductMediaOutSchema` (201): `{ "id", "mediaType", "sortOrder", "url" }` — `url` is derived from `storageKey` + the CDN base URL.

### Upload media (multipart)

```
POST /internal/products/{productId}/media/upload
X-Internal-Key: <secret>
Content-Type: multipart/form-data
```

Use when you have the raw file bytes and want the server to upload to R2 for you.

| Field | Form part | Required | Description |
|---|---|---|---|
| `file` | file | **yes** | Image file. Rejected with 422 if content type isn't allowed or the file exceeds the max size. |
| `sortOrder` | text field | no | Defaults to current max `sortOrder` for the product + 10 |

Upload is rejected (no DB write) if the file fails validation or the R2 upload fails. Returns `ProductMediaOutSchema` (201).

Rate limited to **10 requests/minute** per IP (stricter than the other internal endpoints, since it involves a file transfer).

### Get category by name

```
GET /internal/categories/by-name?name=Biotech
X-Internal-Key: <secret>
```

Query parameter `name` is matched exactly, case-insensitive. Only matches **parent** categories (not subcategories).

Returns **200** with the category object, or **404** if not found.

Response body:

| Field | JSON type | Description |
|---|---|---|
| `id` | integer | Use this value in `categoryIds` when creating a product |
| `name` | string | Category name as stored |
| `parentId` | null | Always null for parent categories |
| `status` | string | `"approved"` — only approved categories are returned |

### Get subcategory by name

```
GET /internal/subcategories/by-name?name=Gene Editing
X-Internal-Key: <secret>
```

Query parameter `name` is matched exactly, case-insensitive. Only matches **subcategories** (entries that belong to a parent category).

Returns **200** with the subcategory object, or **404** if not found.

Response body:

| Field | JSON type | Description |
|---|---|---|
| `id` | integer | Use this value in `subCategoryIds` when creating a product |
| `name` | string | Subcategory name as stored |
| `parentId` | integer | ID of the parent category this belongs to |
| `status` | string | `"approved"` |

### Get product by name

```
GET /internal/products/by-name?name=AlphaFold 3
X-Internal-Key: <secret>
```

Query parameter `name` is matched exactly, case-insensitive. Returns **200** with the full product object (same shape as the create response above), or **404** if not found.

Unlike the public API, this endpoint returns products of **any status** including `"pending"` — use it to check whether a product has already been imported before creating a duplicate.

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

Seeded by migration `e2b3c4d5f6a7`. The system user is treated as admin-equivalent for modify permissions, so it can update or add media to any product — not just ones it created itself. To find everything the system user created:

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

60 requests / minute per IP by default. There is no logged-in user on internal requests, so the limiter uses the caller's IP address.

Exception: `POST /internal/products/{productId}/media/upload` is limited to **10/minute** per IP.

---

## Security Notes

- The key comparison uses `secrets.compare_digest` (constant-time) to prevent timing attacks.
- Rotate `INTERNAL_API_KEY` if it is ever exposed — update the env var and restart the service.
- The system user cannot log in through the normal auth flow regardless of the key value.
- Categories are **not** created as a side effect of product creation. The internal service must resolve a category ID before submitting a product; if the category doesn't exist, an admin must create it via the normal API.

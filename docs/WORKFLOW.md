# Backend Workflow

This document collects the main day-to-day steps for this backend in one place.

## Available roles

| Role | Value | Profile table |
|------|-------|---------------|
| Admin | `admin` | — |
| User | `user` | — |
| Researcher | `researcher` | `researcher_profiles` |
| Sponsor | `sponsor` | `sponsor_profiles` |
| Founder | `founder` | — |
| Investor | `investor` | `investor_profiles` |

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
  "categories": [
    { "categoryId": 3 }
  ]
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
[
  { "categoryId": 1 },
  { "categoryId": 3 }
]
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

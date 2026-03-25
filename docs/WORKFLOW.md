# Backend Workflow

This document collects the main day-to-day steps for this backend in one place.

## Public signup flow

This is the flow the frontend should use for first-time user registration.

1. The frontend sends `POST /api/v1/user/signup`
2. The password is saved in a secure hashed form
3. The new user is stored in the database
4. The role from the request body is stored as part of the new user
5. The API sends a verification email to the user
6. The response tells the user to verify their email before logging in

### Signup response

```json
{
  "message": "Signup successful. Please verify your email."
}
```

### Signup request example

```bash
curl -X POST "${API_URL}/api/v1/user/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "${NAME}",
    "email": "${EMAIL}",
    "password": "${PASSWORD}",
    "role": "builder"
  }'
```

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

## Login flow

1. The frontend sends `POST /api/v1/user/login`
2. The backend checks the credentials
3. A JWT access token is created
4. The token is returned and also stored in an HTTP-only cookie

The login flow is still available for users who verified earlier and need to sign in later.

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

## Lab CRUD flow

Labs expose public read endpoints and admin-only write endpoints.

1. The frontend sends `POST /api/v1/lab`
2. The backend creates the lab record linked to a university
3. The frontend can list, read, update, and delete labs with the matching `/api/v1/lab` routes
4. `GET /api/v1/lab` and `GET /api/v1/lab/{lab_id}` are public
5. `POST`, `PATCH`, and `DELETE` require an authenticated user with the `admin` role

### Lab create request example

```bash
curl -X POST "${API_URL}/api/v1/lab" \
  -H "Content-Type: application/json" \
  -H "Cookie: access_token=${ACCESS_TOKEN}" \
  -d '{
    "universityId": 1,
    "name": "AI Research Lab",
    "focus": "Machine Learning",
    "description": "Computer vision and applied ML projects",
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

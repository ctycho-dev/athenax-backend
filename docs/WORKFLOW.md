# Backend Workflow

This document collects the main day-to-day steps for this backend in one place.

## Public signup flow

This is the flow the frontend should use for first-time user registration.

1. The frontend sends `POST /api/v1/user/signup`
2. The password is saved in a secure hashed form
3. The new user is stored in the database
4. The API creates a JWT token for the new user
5. The token is returned in the response and stored in an HTTP-only cookie

### Signup response

```json
{
  "access_token": "jwt-token-here",
  "token_type": "bearer"
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
    "role": "user"
  }'
```

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

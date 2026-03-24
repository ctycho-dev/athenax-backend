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

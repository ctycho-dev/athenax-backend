import pytest
from tests.conftest import ClientWithEmail


@pytest.mark.asyncio
class TestOnboardingAPI:
    """Integration tests for signup, verification, login, and password reset flows."""

    async def test_signup_sends_verification_email(self, client: ClientWithEmail, user_payload):
        response = await client.post("/api/v1/user/signup", json=user_payload)

        assert response.status_code == 201
        assert response.json()["message"] == "Signup successful. Please verify your email."
        assert len(client.fake_email_service.sent_emails) == 1
        assert client.fake_email_service.sent_emails[0]["type"] == "verification"
        assert client.fake_email_service.sent_emails[0]["email"] == user_payload["email"]

    async def test_signup_succeeds_when_verification_email_fails(
        self,
        client: ClientWithEmail,
        user_payload,
    ):
        client.fake_email_service.fail_verification = True

        response = await client.post("/api/v1/user/signup", json=user_payload)

        assert response.status_code == 201
        assert response.json()["message"] == (
            "Signup successful, but we could not send the verification email right now. "
            "Please try the resend verification endpoint later."
        )
        assert len(client.fake_email_service.sent_emails) == 0

    async def test_verify_email_allows_login(self, client: ClientWithEmail, user_payload):
        await client.post("/api/v1/user/signup", json=user_payload)
        verification_email = client.fake_email_service.sent_emails[-1]

        verify_response = await client.post(
            "/api/v1/user/verify-email",
            json={"token": verification_email["token"]},
        )

        assert verify_response.status_code == 200
        assert verify_response.json()["message"] == "Email verified successfully."

        response = await client.post(
            "/api/v1/user/login",
            data={"username": user_payload["email"], "password": user_payload["password"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "access_token" in response.cookies

    async def test_reset_token_cannot_verify_email(self, client: ClientWithEmail, user_payload):
        await client.post("/api/v1/user/signup", json=user_payload)
        verification_email = client.fake_email_service.sent_emails[-1]
        await client.post(
            "/api/v1/user/verify-email",
            json={"token": verification_email["token"]},
        )
        await client.post(
            "/api/v1/user/forgot-password",
            json={"email": user_payload["email"]},
        )
        reset_email = client.fake_email_service.sent_emails[-1]

        verify_response = await client.post(
            "/api/v1/user/verify-email",
            json={"token": reset_email["token"]},
        )

        assert verify_response.status_code == 400
        assert verify_response.json()["detail"] == "Invalid or expired verification token"

    async def test_verification_token_cannot_reset_password(
        self,
        client: ClientWithEmail,
        user_payload,
    ):
        await client.post("/api/v1/user/signup", json=user_payload)
        verification_email = client.fake_email_service.sent_emails[-1]

        reset_response = await client.post(
            "/api/v1/user/reset-password",
            json={"token": verification_email["token"], "password": "UpdatedPass123!"},
        )

        assert reset_response.status_code == 400
        assert reset_response.json()["detail"] == "Invalid or expired reset token"

    async def test_login_rejects_unverified_user(self, client: ClientWithEmail, user_payload):
        await client.post("/api/v1/user/signup", json=user_payload)

        response = await client.post(
            "/api/v1/user/login",
            data={"username": user_payload["email"], "password": user_payload["password"]}
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Email is not verified"

    async def test_login_invalid_credentials(self, client: ClientWithEmail):
        response = await client.post(
            "/api/v1/user/login",
            data={"username": "wrong@example.com", "password": "wrongpass"}
        )

        assert response.status_code == 403

    async def test_forgot_password_resets_password(self, client: ClientWithEmail, user_payload):
        await client.post("/api/v1/user/signup", json=user_payload)
        verification_email = client.fake_email_service.sent_emails[-1]
        await client.post(
            "/api/v1/user/verify-email",
            json={"token": verification_email["token"]},
        )

        forgot_response = await client.post(
            "/api/v1/user/forgot-password",
            json={"email": user_payload["email"]},
        )

        assert forgot_response.status_code == 200
        assert forgot_response.json()["message"] == "Password reset email has been sent."

        reset_email = client.fake_email_service.sent_emails[-1]
        assert reset_email["type"] == "password_reset"

        new_password = "UpdatedPass123!"
        reset_response = await client.post(
            "/api/v1/user/reset-password",
            json={"token": reset_email["token"], "password": new_password},
        )

        assert reset_response.status_code == 200
        assert reset_response.json()["message"] == "Password reset successfully."

        login_response = await client.post(
            "/api/v1/user/login",
            data={"username": user_payload["email"], "password": new_password}
        )

        assert login_response.status_code == 200

    async def test_forgot_password_returns_error_when_email_fails(
        self,
        client: ClientWithEmail,
        user_payload,
    ):
        await client.post("/api/v1/user/signup", json=user_payload)
        verification_email = client.fake_email_service.sent_emails[-1]
        await client.post(
            "/api/v1/user/verify-email",
            json={"token": verification_email["token"]},
        )
        client.fake_email_service.fail_password_reset = True

        forgot_response = await client.post(
            "/api/v1/user/forgot-password",
            json={"email": user_payload["email"]},
        )

        assert forgot_response.status_code == 503
        assert forgot_response.json()["detail"] == (
            "Could not send password reset email right now. Please try again later."
        )

    async def test_resend_verification_email_returns_error_when_email_fails(
        self,
        client: ClientWithEmail,
        user_payload,
    ):
        await client.post("/api/v1/user/signup", json=user_payload)
        client.fake_email_service.fail_verification = True

        resend_response = await client.post(
            "/api/v1/user/verify-email/resend",
            json={"email": user_payload["email"]},
        )

        assert resend_response.status_code == 503
        assert resend_response.json()["detail"] == (
            "Could not send verification email right now. Please try again later."
        )

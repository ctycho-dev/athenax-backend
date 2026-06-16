import resend
from urllib.parse import urlencode
from anyio import to_thread

from app.core.config import settings
from app.core.logger import get_logger
from app.infrastructure.email.renderer import render_email


logger = get_logger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when the email provider rejects or interrupts message delivery."""


class EmailService:
    def __init__(self) -> None:
        resend.api_key = settings.resend.api_key

    async def send_verification_email(self, email: str, name: str, token: str) -> None:
        action_url = self._build_url(settings.email_verify_url, token)
        html = render_email("action_email.html", {
            "name": name,
            "token": token,
            "title": "Verify your email",
            "intro": (
                "Welcome to AthenaX. Click the button below to verify your email "
                "address and activate your account."
            ),
            "cta_text": "Verify Email",
            "action_url": action_url,
            "footer_text": "If you did not create this account, you can ignore this email.",
        })
        await self.send_email(email, "Verify your AthenaX account", html)

    async def send_password_reset_email(self, email: str, name: str, token: str) -> None:
        action_url = self._build_url(settings.password_reset_url, token)
        html = render_email("action_email.html", {
            "name": name,
            "token": token,
            "title": "Reset your password",
            "intro": (
                "We received a request to reset your password. Click the button "
                "below to choose a new password."
            ),
            "cta_text": "Reset Password",
            "action_url": action_url,
            "footer_text": "If you did not request this change, you can ignore this email.",
        })
        await self.send_email(email, "Reset your AthenaX password", html)

    async def send_subscriber_welcome_email(self, email: str, unsubscribe_url: str) -> None:
        html = render_email("subscriber_welcome.html", {
            "email": email,
            "unsubscribe_url": unsubscribe_url,
        })
        await self.send_email(email, "You're subscribed to AthenaX", html)

    async def send_email(self, email: str, subject: str, html: str) -> None:
        params: resend.Emails.SendParams = {
            "from": settings.resend.from_address,
            "to": [email],
            "subject": subject,
            "html": html,
        }
        try:
            await to_thread.run_sync(lambda: resend.Emails.send(params))
        except Exception as exc:
            logger.exception("email_delivery_failed", extra={"recipient": email, "subject": subject})
            raise EmailDeliveryError("Email delivery failed") from exc

    @staticmethod
    def _build_url(base_url: str, token: str) -> str:
        target = base_url.rstrip("?")
        separator = "&" if "?" in target else "?"
        return f"{target}{separator}{urlencode({'token': token})}"

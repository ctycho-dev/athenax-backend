import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from anyio import to_thread

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when the SMTP provider rejects or interrupts message delivery."""


class EmailService:
    async def send_verification_email(self, email: str, name: str, token: str) -> None:
        verification_url = self._build_url(
            settings.EMAIL_VERIFY_URL,
            f"{settings.BASE_URL.rstrip('/')}{settings.api.v1.prefix}{settings.api.v1.user}/verify-email",
            token,
        )
        subject = "Verify your AthenaX account"
        body = (
            f"Hi {name},\n\n"
            "Welcome to AthenaX. Please verify your email address to activate your account.\n\n"
            f"Verification link: {verification_url}\n"
            f"Verification token: {token}\n\n"
            "If you did not create this account, you can ignore this email."
        )
        await self.send_email(email, subject, body)

    async def send_password_reset_email(self, email: str, name: str, token: str) -> None:
        reset_url = self._build_url(
            settings.PASSWORD_RESET_URL,
            f"{settings.BASE_URL.rstrip('/')}{settings.api.v1.prefix}{settings.api.v1.user}/reset-password",
            token,
        )
        subject = "Reset your AthenaX password"
        body = (
            f"Hi {name},\n\n"
            "We received a request to reset your password.\n\n"
            f"Reset link: {reset_url}\n"
            f"Reset token: {token}\n\n"
            "If you did not request this change, you can ignore this email."
        )
        await self.send_email(email, subject, body)

    async def send_email(self, email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        message["To"] = email
        message.set_content(body)

        await to_thread.run_sync(self._send_message, message)

    def _send_message(self, message: EmailMessage) -> None:
        try:
            if settings.SMTP_USE_SSL:
                with smtplib.SMTP_SSL(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=settings.SMTP_TIMEOUT,
                ) as smtp:
                    if settings.SMTP_USER and settings.SMTP_PASS:
                        smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
                    smtp.send_message(message)
                return

            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=settings.SMTP_TIMEOUT,
            ) as smtp:
                smtp.ehlo()
                if settings.SMTP_STARTTLS:
                    smtp.starttls()
                    smtp.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASS:
                    smtp.login(settings.SMTP_USER, settings.SMTP_PASS)
                smtp.send_message(message)
        except Exception as exc:  # pragma: no cover
            logger.exception("failed_to_send_email", extra={"email": message["To"]})
            raise EmailDeliveryError("Failed to send email") from exc

    @staticmethod
    def _build_url(base_url: str | None, fallback_url: str, token: str) -> str:
        target = (base_url or fallback_url).rstrip("?")
        separator = "&" if "?" in target else "?"
        return f"{target}{separator}{urlencode({'token': token})}"

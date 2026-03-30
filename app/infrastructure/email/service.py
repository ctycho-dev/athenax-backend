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
        plain = (
            f"Hi {name},\n\n"
            "Welcome to AthenaX. Please verify your email address to activate your account.\n\n"
            f"Verification link: {verification_url}\n\n"
            "If you did not create this account, you can ignore this email."
        )
        html = f"""<!DOCTYPE html>
<html>
  <body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:0;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center" style="padding:40px 0;">
        <table width="480" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;padding:40px;">
          <tr><td>
            <h2 style="margin:0 0 16px;color:#111111;">Verify your email</h2>
            <p style="color:#444444;line-height:1.6;">Hi {name},</p>
            <p style="color:#444444;line-height:1.6;">Welcome to AthenaX. Click the button below to verify your email address and activate your account.</p>
            <p style="text-align:center;margin:32px 0;">
              <a href="{verification_url}" style="background:#2563eb;color:#ffffff;text-decoration:none;padding:14px 32px;border-radius:6px;font-size:16px;font-weight:600;display:inline-block;">Verify Email</a>
            </p>
            <p style="color:#888888;font-size:11px;">Token: <code style="background:#f0f0f0;padding:2px 6px;border-radius:4px;font-family:monospace;">{token}</code></p>
            <p style="color:#888888;font-size:13px;">If you did not create this account, you can ignore this email.</p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""
        await self.send_email(email, subject, plain, html)

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

    async def send_email(self, email: str, subject: str, body: str, html: str | None = None) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM}>"
        message["To"] = email
        message.set_content(body)
        if html:
            message.add_alternative(html, subtype="html")

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

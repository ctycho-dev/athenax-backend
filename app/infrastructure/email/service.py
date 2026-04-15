import resend
from urllib.parse import urlencode
from anyio import to_thread

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when the email provider rejects or interrupts message delivery."""


class EmailService:
    def __init__(self) -> None:
        resend.api_key = settings.resend.api_key

    async def send_verification_email(self, email: str, name: str, token: str) -> None:
        await self._send_action_email(
            email=email,
            name=name,
            token=token,
            subject="Verify your AthenaX account",
            title="Verify your email",
            intro=(
                "Welcome to AthenaX. Click the button below to verify your email "
                "address and activate your account."
            ),
            cta_text="Verify Email",
            action_base_url=settings.email_verify_url,
            footer_text="If you did not create this account, you can ignore this email.",
        )

    async def send_password_reset_email(self, email: str, name: str, token: str) -> None:
        await self._send_action_email(
            email=email,
            name=name,
            token=token,
            subject="Reset your AthenaX password",
            title="Reset your password",
            intro=(
                "We received a request to reset your password. Click the button "
                "below to choose a new password."
            ),
            cta_text="Reset Password",
            action_base_url=settings.password_reset_url,
            footer_text="If you did not request this change, you can ignore this email.",
        )

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

    async def _send_action_email(
        self,
        email: str,
        name: str,
        token: str,
        subject: str,
        title: str,
        intro: str,
        cta_text: str,
        action_base_url: str,
        footer_text: str,
    ) -> None:
        action_url = self._build_url(action_base_url, token)
        html = self._build_action_email_html(
            name=name,
            token=token,
            title=title,
            intro=intro,
            cta_text=cta_text,
            action_url=action_url,
            footer_text=footer_text,
        )
        await self.send_email(email, subject, html)

    @staticmethod
    def _build_action_email_html(
        name: str,
        token: str,
        title: str,
        intro: str,
        cta_text: str,
        action_url: str,
        footer_text: str,
    ) -> str:
        return f"""<!DOCTYPE html>
<html>
  <body style="font-family:Inter,Segoe UI,Arial,sans-serif;background:#F2EFE9;margin:0;padding:0;color:#1c1c27;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center" style="padding:32px 12px;">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#F9F5DC;border:3px solid #1c1c27;border-radius:16px;box-shadow:0 8px 20px rgba(28,28,39,0.15);">
          <tr>
            <td style="padding:24px 28px;border-bottom:3px solid #1c1c27;background:#1c1c27;text-align:center;border-radius:13px 13px 0 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding:0;">
                    <img src="https://athenax.mypinx.store/Logo_Icon_White.png" alt="AthenaX" style="height:28px;width:auto;display:inline-block;margin-right:12px;vertical-align:middle;" />
                    <span style="color:#F2EFE9;font-size:20px;font-weight:900;letter-spacing:-0.5px;display:inline-block;vertical-align:middle;">AthenaX</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 28px;border-bottom:3px solid #1c1c27;background:#D4EDDA;">
              <span style="color:#3a3a4a;font-size:11px;font-weight:800;letter-spacing:1px;text-transform:uppercase;">Account Action Required</span>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 28px;">
              <h2 style="margin:0 0 20px 0;color:#1c1c27;font-size:32px;line-height:1.1;font-weight:900;">{title}<span style="color:#e8323c;">.</span></h2>
              <p style="margin:0 0 16px 0;color:#3a3a4a;line-height:1.6;font-size:16px;">Hi {name},</p>
              <p style="margin:0 0 28px 0;color:#3a3a4a;line-height:1.6;font-size:16px;">{intro}</p>
              <p style="margin:0;text-align:center;">
                <a href="{action_url}" style="background:#e8323c;color:#F2EFE9;text-decoration:none;padding:14px 40px;border:2px solid #1c1c27;border-radius:12px;font-size:16px;font-weight:800;display:inline-block;box-shadow:0 4px 12px rgba(232,50,60,0.25);">{cta_text}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 28px;border-top:3px solid #1c1c27;background:#F2EFE9;border-radius:0 0 13px 13px;">
              <p style="margin:0 0 8px 0;color:#6B6B7A;font-size:12px;line-height:1.5;">Token: <code style="background:#F9F5DC;padding:2px 6px;border:1px solid #1c1c27;font-family:Menlo,Consolas,monospace;color:#1c1c27;font-size:11px;">{token}</code></p>
              <p style="margin:0;color:#6B6B7A;font-size:13px;line-height:1.6;">{footer_text}</p>
            </td>
          </tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""

    @staticmethod
    def _build_url(base_url: str, token: str) -> str:
        target = base_url.rstrip("?")
        separator = "&" if "?" in target else "?"
        return f"{target}{separator}{urlencode({'token': token})}"

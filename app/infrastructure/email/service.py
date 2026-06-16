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

    async def send_subscriber_welcome_email(self, email: str, unsubscribe_url: str) -> None:
        html = self._build_subscriber_welcome_html(email, unsubscribe_url)
        await self.send_email(email, "You're subscribed to AthenaX", html)

    @staticmethod
    def _build_subscriber_welcome_html(email: str, unsubscribe_url: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Welcome to AthenaX</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700;800&display=swap');
  body,table,td,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%}}
  table,td{{mso-table-lspace:0pt;mso-table-rspace:0pt}}
  img{{-ms-interpolation-mode:bicubic;border:0;height:auto;line-height:100%;outline:none;text-decoration:none}}
  body{{margin:0;padding:0;width:100%!important;background-color:#F5F1E8}}
  @media only screen and (max-width:620px){{
    .wrapper{{width:100%!important;padding:0 16px!important}}
    .content-pad{{padding:24px 20px!important}}
    .hero-title{{font-size:26px!important}}
  }}
</style>
</head>
<body style="margin:0;padding:0;background-color:#F5F1E8;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#F5F1E8;">
<tr><td align="center" style="padding:32px 16px 48px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="520" class="wrapper" style="max-width:520px;width:100%;">

<!-- LOGO -->
<tr><td align="center" style="padding-bottom:28px;">
  <table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="padding-right:10px;vertical-align:middle;">
      <div style="width:36px;height:36px;background:#1a1a1a;border-radius:9px;display:inline-block;text-align:center;line-height:36px;">
        <img src="https://athenax.mypinx.store/Logo_Icon_White.png" alt="AthenaX" width="22" height="22" style="display:inline-block;vertical-align:middle;" />
      </div>
    </td>
    <td style="font-family:'Inter',-apple-system,sans-serif;font-size:22px;font-weight:800;color:#1a1a1a;letter-spacing:-0.03em;vertical-align:middle;">
      AthenaX
    </td>
    <td style="padding-left:6px;vertical-align:middle;">
      <span style="font-family:'JetBrains Mono',monospace;font-size:8px;background:#1a1a1a;color:#fff;padding:2px 5px;border-radius:3px;letter-spacing:0.06em;">BETA</span>
    </td>
  </tr></table>
</td></tr>

<!-- MAIN CARD -->
<tr><td>
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#FFFFFF;border:2px solid #1a1a1a;border-radius:8px;box-shadow:3px 3px 0 #1a1a1a;">

  <!-- Window bar -->
  <tr><td style="border-bottom:2px solid #1a1a1a;padding:8px 14px;">
    <table role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#E24B4A;margin-right:5px;"></span></td>
      <td><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#EF9F27;margin-right:5px;"></span></td>
      <td><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#639922;margin-right:10px;"></span></td>
      <td style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:0.04em;font-weight:500;color:#1a1a1a;">WELCOME.SYS</td>
    </tr></table>
  </td></tr>

  <!-- Body -->
  <tr><td class="content-pad" style="padding:32px 36px 36px;">
    <p style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#999;letter-spacing:0.15em;text-transform:uppercase;margin:0 0 16px;">SUBSCRIPTION CONFIRMED</p>
    <h1 class="hero-title" style="font-family:'Inter',-apple-system,sans-serif;font-size:30px;font-weight:800;color:#1a1a1a;margin:0 0 18px;letter-spacing:-0.03em;line-height:1.15;">You're in.</h1>
    <p style="font-family:'Inter',-apple-system,sans-serif;font-size:15px;color:#444;line-height:1.7;margin:0 0 14px;">
      Thanks for subscribing to the AthenaX newsletter. Every week, we'll send you a short roundup of what's happening across frontier tech:
    </p>
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 20px;">
      <tr>
        <td width="24" valign="top" style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#EF9F27;padding:6px 0;">&#8594;</td>
        <td style="font-family:'Inter',sans-serif;font-size:14px;color:#444;line-height:1.6;padding:5px 0;">Top launches of the week across AI, biotech, crypto, robotics, dev tools, and infrastructure</td>
      </tr>
      <tr>
        <td width="24" valign="top" style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#EF9F27;padding:6px 0;">&#8594;</td>
        <td style="font-family:'Inter',sans-serif;font-size:14px;color:#444;line-height:1.6;padding:5px 0;">Editorial context on what's being built across the frontier and why it matters</td>
      </tr>
      <tr>
        <td width="24" valign="top" style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#EF9F27;padding:6px 0;">&#8594;</td>
        <td style="font-family:'Inter',sans-serif;font-size:14px;color:#444;line-height:1.6;padding:5px 0;">New bounties, cohort updates, and community highlights <span style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#999;letter-spacing:0.04em;">(coming soon)</span></td>
      </tr>
    </table>
    <p style="font-family:'Inter',-apple-system,sans-serif;font-size:15px;color:#444;line-height:1.7;margin:0 0 24px;">
      Your first newsletter lands soon. In the meantime, come explore what's already live:
    </p>
    <table role="presentation" cellpadding="0" cellspacing="0" align="center">
    <tr><td>
      <a href="https://www.athenax.co/launch" style="display:inline-block;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;color:#fff;background:#E94842;border:2px solid #1a1a1a;border-radius:4px;padding:13px 28px;text-decoration:none;box-shadow:2px 2px 0 #1a1a1a;">Browse the Launch Feed &#8594;</a>
    </td></tr>
    </table>
  </td></tr>
</table>
</td></tr>

<!-- FOOTER -->
<tr><td style="padding-top:28px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr><td align="center">
    <p style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#aaa;letter-spacing:0.06em;margin:0 0 6px;">
      &gt;_ ATHENAX &middot; WHERE NEW PRODUCTS BEGIN
    </p>
    <p style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#bbb;margin:0 0 10px;">
      CC0 /// NO RIGHTS RESERVED /// OPEN SOURCE
    </p>
    <p style="font-family:'Inter',sans-serif;font-size:11px;color:#bbb;margin:0;">
      You're receiving this because {email} subscribed to AthenaX updates.
      <br/>
      <a href="{unsubscribe_url}" style="color:#999;text-decoration:underline;">Unsubscribe</a>
    </p>
  </td></tr>
</table>
</td></tr>

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

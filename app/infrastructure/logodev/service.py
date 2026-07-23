import httpx

from app.core.config import settings
from app.core.logger import get_logger
from app.common.storage import ALLOWED_CONTENT_TYPES
from app.exceptions.exceptions import ExternalServiceError

logger = get_logger(__name__)

# Bare domains never worth a Logo.dev lookup — the "logo" would be the platform's, not the product's.
LOGO_SKIP_DOMAINS = {
    # social media
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "tiktok.com",
    "youtube.com",
    "reddit.com",
    "discord.com",
    "discord.gg",
    "t.me",
    "telegram.org",
    "threads.net",
    "pinterest.com",
    "snapchat.com",
    # code hosting / free PaaS subdomains — product sites deployed under these
    # get the platform's logo, not the product's, since the domain is shared
    "github.com",
    "github.io",
    "gitlab.io",
    "bitbucket.io",
    "vercel.app",
    "vercel.dev",
    "netlify.app",
    "herokuapp.com",
    "onrender.com",
    "railway.app",
    "pages.dev",
    "web.app",
    "firebaseapp.com",
    "repl.co",
    "replit.app",
    "replit.dev",
    "glitch.me",
    "surge.sh",
    "webflow.io",
    "wixsite.com",
    "carrd.co",
    "notion.site",
    "framer.app",
    "framer.website",
    "linktr.ee",
}


def is_logo_skip_domain(domain: str) -> bool:
    """True if `domain` is (or is a subdomain of) a platform we never look up a logo for."""
    return domain in LOGO_SKIP_DOMAINS or any(
        domain.endswith(f".{platform}") for platform in LOGO_SKIP_DOMAINS
    )


class LogoDevService:
    """Fetches company logos from Logo.dev (https://logo.dev) by domain."""

    def __init__(self) -> None:
        self._timeout = httpx.Timeout(5.0)

    def build_logo_url(self, domain: str) -> str:
        return (
            f"https://img.logo.dev/{domain}"
            f"?token={settings.logo_dev.publishable_key}&size=256&format=webp"
        )

    async def fetch_logo(self, domain: str) -> tuple[bytes, str] | None:
        """Returns (bytes, content_type), or None if Logo.dev has no logo for this domain."""
        url = self.build_logo_url(domain)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Logo.dev request failed: {exc}") from exc

        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise ExternalServiceError(f"Logo.dev returned {resp.status_code}")

        # Logo.dev honors format=webp but doesn't always echo an exact allowed
        # MIME type in the header — the request param already guarantees payload type.
        content_type = resp.headers.get("content-type", "image/webp").split(";")[0].strip()
        if content_type not in ALLOWED_CONTENT_TYPES:
            content_type = "image/webp"
        return resp.content, content_type

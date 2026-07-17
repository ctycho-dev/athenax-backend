import httpx

from app.core.config import settings
from app.core.logger import get_logger
from app.common.storage import ALLOWED_CONTENT_TYPES
from app.exceptions.exceptions import ExternalServiceError

logger = get_logger(__name__)


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

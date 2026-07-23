from urllib.parse import urlparse


def validate_url(value: str) -> str:
    """Rejects placeholder/garbage text (e.g. "not found") masquerading as a URL."""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or " " in value:
        raise ValueError("must be a valid http:// or https:// URL")
    return value


def extract_domain(url: str) -> str | None:
    """Bare host (no scheme/www/path) for Logo.dev lookups."""
    parsed = urlparse(url if "://" in url else f"//{url}")
    host = (parsed.netloc or parsed.path).split("/")[0].split(":")[0].lower()
    if not host or " " in host or "." not in host:
        return None
    return host[4:] if host.startswith("www.") else host

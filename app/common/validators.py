from urllib.parse import urlparse


def validate_url(value: str) -> str:
    """Rejects placeholder/garbage text (e.g. "not found") masquerading as a URL."""
    value = value.strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or " " in value:
        raise ValueError("must be a valid http:// or https:// URL")
    return value

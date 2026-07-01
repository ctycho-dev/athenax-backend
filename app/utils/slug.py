import re
import secrets
from unicodedata import normalize


def slugify(title: str, max_length: int = 255) -> str:
    text = normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"
    return text[:max_length].rstrip("-")


def with_random_suffix(base: str) -> str:
    return f"{base}-{secrets.token_hex(2)}"

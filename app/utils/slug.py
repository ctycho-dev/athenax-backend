import re
import secrets
from unicodedata import normalize


def generate_slug(title: str, suffix_length: int = 4, max_length: int = 60) -> str:
    text = normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "paper"
    text = text[: max_length - suffix_length - 1].rstrip("-")
    suffix = secrets.token_hex((suffix_length + 1) // 2)[:suffix_length]
    return f"{text}-{suffix}"


def slugify(title: str, max_length: int = 255) -> str:
    text = normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "article"
    return text[:max_length].rstrip("-")

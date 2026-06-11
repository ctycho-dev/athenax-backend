"""Shared helpers for all Locust persona files.

Imported by anonymous.py, authenticated.py, investor.py, admin.py.
locustfile.py adds this directory to sys.path before importing persona modules.
"""
import os
import random
import threading
from typing import Any

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------

SPOOF_IP = os.getenv("LOCUST_SPOOF_IP", "1").lower() not in ("0", "false", "no")
P95_THRESHOLD_MS = int(os.getenv("LOAD_P95_THRESHOLD_MS", "2000"))
FAILURE_RATE_THRESHOLD = float(os.getenv("LOAD_FAILURE_THRESHOLD", "0.05"))
RATE_LIMITED_NAME = "RATE LIMITED (429)"

SORT_OPTIONS = ["newest", "oldest", "top"]
SEARCH_TERMS = ["ai", "data", "robot", "crypto", "bio", "tool", "lab", "open"]

# ---------------------------------------------------------------------------
# User credential pools
# ---------------------------------------------------------------------------
# Env override format: "email1:pass1,email2:pass2"
# Defaults match what scripts/seed_load_data.py creates.

_DEFAULT_PASSWORD = os.getenv("LOAD_TEST_USER_PASSWORD", "Testpass1!")


def _parse_pool(env_var: str, prefix: str) -> list[tuple[str, str]]:
    raw = os.getenv(env_var, "").strip()
    if raw:
        pairs = []
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" in entry:
                email, pw = entry.split(":", 1)
                pairs.append((email.strip(), pw.strip()))
        if pairs:
            return pairs
    return [(f"{prefix}-{n:02d}@test.athena", _DEFAULT_PASSWORD) for n in range(1, 11)]


USER_POOL: list[tuple[str, str]]     = _parse_pool("LOAD_USER_POOL",     "load-user")
INVESTOR_POOL: list[tuple[str, str]] = _parse_pool("LOAD_INVESTOR_POOL", "load-investor")
ADMIN_POOL: list[tuple[str, str]]    = _parse_pool("LOAD_ADMIN_POOL",    "load-admin")

# ---------------------------------------------------------------------------
# Shared ID cache — primed once per test run
# ---------------------------------------------------------------------------

CACHE: dict[str, list] = {
    "product_ids":    [],
    "product_slugs":  [],
    "category_ids":   [],
    "article_ids":    [],
    "article_slugs":  [],
    "broadcast_ids":  [],
    "broadcast_slugs": [],
}

_lock = threading.Lock()       # guards the IP counter only
_cache_lock = threading.Lock() # guards cache priming — never held across the network
_ip_counter = 0


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def handle(response, name: str) -> None:
    """429-aware result handler for catch_response=True requests.

    429 is the rate limiter doing its job — relabel into its own stats row
    and mark success. Everything 2xx/3xx is success. Anything else is a real failure.
    """
    if response.status_code == 429:
        response.request_meta["name"] = RATE_LIMITED_NAME
        response.success()
    elif response.status_code < 400:
        response.success()
    else:
        response.failure(f"{name} -> HTTP {response.status_code}")


def assign_fake_ip(user) -> None:
    """Give each simulated user a unique X-Forwarded-For so it gets its own rate-limit quota."""
    if not SPOOF_IP:
        return
    global _ip_counter
    with _lock:
        _ip_counter += 1
        n = _ip_counter
    ip = f"10.{(n >> 16) & 0xFF}.{(n >> 8) & 0xFF}.{(n & 0xFF) or 1}"
    user.client.headers["X-Forwarded-For"] = ip


def hot_pick(seq: list) -> Any:
    """Return an item with access skew: 80% from the first 10 (hot), 20% from full list.

    Reproduces real power-law access patterns that expose row-level contention.
    """
    if not seq:
        return None
    hot = seq[:10]
    if hot and random.random() < 0.8:
        return random.choice(hot)
    return random.choice(seq)


def populate_cache(client) -> None:
    """Prime the shared ID cache once per test run (double-checked locking)."""
    if CACHE["product_ids"]:
        return
    with _cache_lock:
        if CACHE["product_ids"]:
            return
        _do_populate(client)


def _do_populate(client) -> None:
    for url, key_id, key_slug in [
        ("/api/v1/product/?limit=50&sortBy=newest", "product_ids", "product_slugs"),
    ]:
        try:
            r = client.get(url, name="[cache] product list")
            if r.status_code == 200:
                items = r.json().get("items", [])
                CACHE["product_ids"]   = [i["id"]   for i in items if i.get("id")]
                CACHE["product_slugs"] = [i["slug"] for i in items if i.get("slug")]
        except Exception:  # noqa: BLE001 — cache priming is best-effort
            pass

    for url, id_key, slug_key in [
        ("/api/v1/category/?limit=50",  "category_ids",  None),
        ("/api/v1/article/?limit=50",   "article_ids",   "article_slugs"),
        ("/api/v1/broadcast/?limit=50", "broadcast_ids", "broadcast_slugs"),
    ]:
        try:
            r = client.get(url, name=f"[cache] {id_key.split('_')[0]} list")
            if r.status_code == 200:
                items = r.json()
                CACHE[id_key] = [i["id"] for i in items if i.get("id")]
                if slug_key:
                    CACHE[slug_key] = [i["slug"] for i in items if i.get("slug")]
        except Exception:  # noqa: BLE001
            pass


def login(client, email: str, password: str) -> bool:
    """POST /api/v1/user/login with OAuth2 form data.

    The server sets an HTTP-only cookie (access_token); the requests.Session
    inside Locust stores and resends it automatically on subsequent requests.
    Returns True on success.
    """
    try:
        r = client.post(
            "/api/v1/user/login",
            data={"username": email, "password": password},
            name="POST /user/login",
        )
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False

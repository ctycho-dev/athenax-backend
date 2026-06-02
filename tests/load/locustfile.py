"""Locust load test for the AthenaX backend.

Simulates anonymous visitors browsing the public read endpoints

Run:
    # Web UI:    .venv/bin/locust -f tests/load/locustfile.py --host http://localhost:8000
    # Headless:  ... --headless -u 200 -r 20 -t 2m

Rate limiting: slowapi limits per client IP, so all simulated users on one box would
share one quota and mostly 429. We give each user a unique X-Forwarded-For (uvicorn
rewrites client.host from it) so each gets its own quota and we test real concurrency.
Set LOCUST_SPOOF_IP=0 to disable and observe the rate-limit ceiling instead. Works on
localhost out of the box; for a remote target start it with --forwarded-allow-ips="*"
(dedicated load-test instances only). 429s show up as their own stats row, not failures.
"""

import os
import random
import threading

from locust import HttpUser, between, events, task

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SPOOF_IP = os.getenv("LOCUST_SPOOF_IP", "1").lower() not in ("0", "false", "no", "")
SORT_OPTIONS = ["newest", "oldest", "top"]
SEARCH_TERMS = ["ai", "data", "robot", "crypto", "bio", "tool", "lab", "open"]

# ---------------------------------------------------------------------------
# Shared state: an ID cache (so detail endpoints hit real rows) and a per-user
# fake-IP counter. 429s are surfaced via the stats table, not a global counter.
# ---------------------------------------------------------------------------

CACHE: dict[str, list] = {"product_ids": [], "product_slugs": [], "category_ids": []}

# Name 429s collapse into — one row in the web UI stats table.
RATE_LIMITED_NAME = "RATE LIMITED (429)"

_lock = threading.Lock()  # guards the IP counter only
_cache_lock = threading.Lock()  # guards cache priming — never held across the network
_ip_counter = 0


def _assign_fake_ip(user) -> None:
    """Give a simulated user a unique X-Forwarded-For so it gets its own quota."""
    if not SPOOF_IP:
        return
    global _ip_counter
    with _lock:
        _ip_counter += 1
        n = _ip_counter
    ip = f"10.{(n >> 16) & 0xFF}.{(n >> 8) & 0xFF}.{(n & 0xFF) or 1}"
    user.client.headers["X-Forwarded-For"] = ip


def _handle(response, name: str) -> None:
    """429-aware result handling for a `catch_response=True` request.

    429 is the rate limiter doing its job — re-label it into a single stats row
    (visible in the web UI) and mark it a success instead of a failure. Everything
    2xx/3xx is a success; the rest is a real failure.
    """
    if response.status_code == 429:
        response.request_meta["name"] = RATE_LIMITED_NAME
        response.success()
    elif response.status_code < 400:
        response.success()
    else:
        response.failure(f"{name} -> HTTP {response.status_code}")


def _populate_cache(client) -> None:
    """Fetch a page of products and categories once to seed the ID cache."""
    try:
        resp = client.get("/api/v1/product/?limit=50", name="[cache] product list")
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            CACHE["product_ids"] = [i["id"] for i in items if i.get("id") is not None]
            CACHE["product_slugs"] = [i["slug"] for i in items if i.get("slug")]
    except Exception:  # noqa: BLE001 - cache priming is best-effort
        pass

    try:
        resp = client.get("/api/v1/category/?limit=50", name="[cache] category list")
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            CACHE["category_ids"] = [i["id"] for i in items if i.get("id") is not None]
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Event hooks
# ---------------------------------------------------------------------------


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    # target_user_count / spawn_rate are set on the runner for both headless and
    # web-UI runs; parsed_options only has them for headless, so prefer the runner.
    runner = environment.runner
    opts = environment.parsed_options
    users = getattr(runner, "target_user_count", None) or getattr(opts, "num_users", None)
    spawn = getattr(runner, "spawn_rate", None) or getattr(opts, "spawn_rate", None)
    print("=" * 80)
    print("🚀 LOAD TEST STARTED")
    print(f"📊 Target: {environment.host} | users: {users} | spawn rate: {spawn}/s")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    stats = environment.stats.total
    # The 429 count lives in the stats table (a row Locust also shows in the UI).
    rl_entry = environment.stats.get(RATE_LIMITED_NAME, "GET")
    rate_limited = rl_entry.num_requests if rl_entry else 0
    print("=" * 80)
    print("🏁 LOAD TEST COMPLETED")
    print(f"📈 Total requests:     {stats.num_requests}")
    print(f"❌ Failures:           {stats.num_failures}")
    print(f"🔒 Rate limited (429): {rate_limited}", end="")
    if stats.num_requests:
        print(f"  ({rate_limited / stats.num_requests * 100:.1f}% of total)")
    else:
        print()
    if stats.num_requests:
        print(f"⏱️  Average:  {stats.avg_response_time:.1f} ms")
        print(f"📊 Median:   {stats.median_response_time} ms")
        print(f"📈 p95:      {stats.get_response_time_percentile(0.95)} ms")
        print(f"📈 p99:      {stats.get_response_time_percentile(0.99)} ms")
        print(f"🐌 Max:      {stats.max_response_time:.1f} ms")
        print(f"⚡ RPS:      {stats.total_rps:.1f}")
    print("=" * 80)


# ---------------------------------------------------------------------------
# Anonymous visitor — browses the public directory
# ---------------------------------------------------------------------------


class AnonymousVisitor(HttpUser):
    wait_time = between(0.1, 1.0)

    def on_start(self):
        _assign_fake_ip(self)
        # Prime the shared cache once. _cache_lock (not _lock) so the priming
        # HTTP calls don't block other users' IP assignment while held.
        if not CACHE["product_ids"]:
            with _cache_lock:
                if not CACHE["product_ids"]:
                    _populate_cache(self.client)

    @task(8)
    def browse_products(self):
        params: dict[str, object] = {
            "limit": random.choice([20, 50]),
            "offset": random.choice([0, 0, 20, 50]),
        }
        roll = random.random()
        if roll < 0.4:
            params["sortBy"] = random.choice(SORT_OPTIONS)
        elif roll < 0.6 and CACHE["category_ids"]:
            params["categoryId"] = random.choice(CACHE["category_ids"])
        elif roll < 0.75:
            params["q"] = random.choice(SEARCH_TERMS)
        with self.client.get(
            "/api/v1/product/", params=params, catch_response=True, name="GET /product/ (list)"
        ) as resp:
            _handle(resp, "product list")

    @task(5)
    def view_product_detail(self):
        if not CACHE["product_ids"]:
            return
        pid = random.choice(CACHE["product_ids"])
        with self.client.get(
            f"/api/v1/product/{pid}", catch_response=True, name="GET /product/[id]"
        ) as resp:
            _handle(resp, "product detail")

    @task(2)
    def view_product_by_slug(self):
        if not CACHE["product_slugs"]:
            return
        slug = random.choice(CACHE["product_slugs"])
        with self.client.get(
            f"/api/v1/product/slug/{slug}", catch_response=True, name="GET /product/slug/[slug]"
        ) as resp:
            _handle(resp, "product by slug")

    @task(1)
    def similar_products(self):
        if not CACHE["product_ids"]:
            return
        pid = random.choice(CACHE["product_ids"])
        with self.client.get(
            f"/api/v1/product/{pid}/similar?limit=5",
            catch_response=True,
            name="GET /product/[id]/similar",
        ) as resp:
            _handle(resp, "similar products")

    @task(1)
    def product_stats(self):
        with self.client.get(
            "/api/v1/product/stats", catch_response=True, name="GET /product/stats"
        ) as resp:
            _handle(resp, "product stats")

    @task(2)
    def list_categories(self):
        with self.client.get(
            "/api/v1/category/?limit=50", catch_response=True, name="GET /category/ (list)"
        ) as resp:
            _handle(resp, "category list")

    @task(2)
    def list_articles(self):
        with self.client.get(
            "/api/v1/article/?limit=50", catch_response=True, name="GET /article/ (list)"
        ) as resp:
            _handle(resp, "article list")

    @task(2)
    def list_broadcasts(self):
        with self.client.get(
            "/api/v1/broadcast/?limit=50", catch_response=True, name="GET /broadcast/ (list)"
        ) as resp:
            _handle(resp, "broadcast list")

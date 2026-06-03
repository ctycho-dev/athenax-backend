"""
AthenaX load-test suite — entry point.

Persona weights (set on each class):
    AnonymousVisitor   10  — public browse traffic (dominant)
    AuthenticatedUser   4  — logged-in browse + vote/bookmark/comment/create
    InvestorUser        1  — investor interest toggle
    AdminUser           1  — admin CRUD + optional upload tasks

Run profiles:
    Capacity (main)   LOCUST_SPOOF_IP=1 (default)  each user has unique IP → own quota
    Rate-limit        LOCUST_SPOOF_IP=0             shared IPs → observe 429 ceiling

Task tags:
    --tags read    Public reads only — safe smoke test
    --tags write   Authenticated + investor write tasks
    --tags admin   Admin CRUD tasks
    --tags upload  Multipart upload tasks (requires R2; skipped by default)

SLA thresholds (configurable via env):
    LOAD_P95_THRESHOLD_MS  (default 2000) — fail CI if p95 exceeds this
    LOAD_FAILURE_THRESHOLD (default 0.05) — fail CI if failure rate exceeds this

Prerequisites:
    make seed:load    # seeds test users + 1000 products + 200 articles + 200 broadcasts

Example runs:
    # Capacity profile — main run
    .venv/bin/locust -f tests/load/locustfile.py --host http://localhost:8000 \\
        --headless -u 200 -r 20 -t 5m --csv=run --html=run.html

    # Read-only smoke test
    .venv/bin/locust -f tests/load/locustfile.py --host http://localhost:8000 \\
        --tags read --headless -u 50 -r 10 -t 2m

    # Rate-limit verification
    LOCUST_SPOOF_IP=0 .venv/bin/locust -f tests/load/locustfile.py \\
        --host http://localhost:8000 --headless -u 100 -r 20 -t 2m

    # Web UI (interactive)
    .venv/bin/locust -f tests/load/locustfile.py --host http://localhost:8000
"""

import os
import sys

# Add this directory to sys.path so sibling modules (common, anonymous, …) are importable.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from locust import events

from admin import AdminUser
from anonymous import AnonymousVisitor
from authenticated import AuthenticatedUser
from common import FAILURE_RATE_THRESHOLD, P95_THRESHOLD_MS, RATE_LIMITED_NAME
from investor import InvestorUser

# Re-export so Locust discovers all personas when scanning this module.
__all__ = ["AnonymousVisitor", "AuthenticatedUser", "InvestorUser", "AdminUser"]


@events.test_start.add_listener
def on_test_start(environment, **_kwargs):
    runner = environment.runner
    opts = environment.parsed_options
    users = getattr(runner, "target_user_count", None) or getattr(opts, "num_users", None)
    spawn = getattr(runner, "spawn_rate", None) or getattr(opts, "spawn_rate", None)
    print("=" * 80)
    print("LOAD TEST STARTED")
    print(f"  Host:        {environment.host}")
    print(f"  Users:       {users}   Spawn rate: {spawn}/s")
    print(f"  SLA:         p95 < {P95_THRESHOLD_MS} ms  |  failures < {FAILURE_RATE_THRESHOLD * 100:.0f}%")
    print("=" * 80)


@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    stats = environment.stats.total
    rl_entry = environment.stats.get(RATE_LIMITED_NAME, "GET")
    rate_limited = rl_entry.num_requests if rl_entry else 0

    total = stats.num_requests or 1
    failure_rate = stats.num_failures / total
    p95 = stats.get_response_time_percentile(0.95) or 0
    p99 = stats.get_response_time_percentile(0.99) or 0

    print("=" * 80)
    print("LOAD TEST COMPLETED")
    print(f"  Total requests:     {stats.num_requests}")
    print(f"  Failures:           {stats.num_failures}  ({failure_rate * 100:.1f}%)")
    print(f"  Rate limited (429): {rate_limited}  ({rate_limited / total * 100:.1f}% of total)")
    if stats.num_requests:
        print(f"  Avg:  {stats.avg_response_time:.1f} ms")
        print(f"  p50:  {stats.median_response_time} ms")
        print(f"  p95:  {p95:.1f} ms")
        print(f"  p99:  {p99:.1f} ms")
        print(f"  Max:  {stats.max_response_time:.1f} ms")
        print(f"  RPS:  {stats.total_rps:.1f}")

    # SLA enforcement — sets process exit code to 1 so CI fails on regression.
    breaches = []
    if p95 > P95_THRESHOLD_MS:
        breaches.append(f"p95 {p95:.0f} ms > {P95_THRESHOLD_MS} ms")
    if failure_rate > FAILURE_RATE_THRESHOLD:
        breaches.append(f"failure rate {failure_rate * 100:.1f}% > {FAILURE_RATE_THRESHOLD * 100:.0f}%")

    if breaches:
        print(f"\nSLA BREACH: {', '.join(breaches)}")
        environment.process_exit_code = 1
    else:
        print("\nSLA OK")
    print("=" * 80)

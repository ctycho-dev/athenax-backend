"""Investor persona — public browse plus investor interest toggle.

Weight 1: rare traffic tier.
"""
import random

from locust import HttpUser, between, tag, task

from common import (
    CACHE,
    INVESTOR_POOL,
    assign_fake_ip,
    handle,
    hot_pick,
    login,
    populate_cache,
)


class InvestorUser(HttpUser):
    weight = 1
    wait_time = between(1.0, 3.0)

    def on_start(self):
        assign_fake_ip(self)
        email, password = random.choice(INVESTOR_POOL)
        login(self.client, email, password)
        populate_cache(self.client)

    @tag("read")
    @task(5)
    def browse_products(self):
        with self.client.get(
            "/api/v1/product/?limit=20", catch_response=True, name="GET /product/ (list)"
        ) as r:
            handle(r, "product list")

    @tag("read")
    @task(3)
    def view_product_detail(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}", catch_response=True, name="GET /product/[id]"
        ) as r:
            handle(r, "product detail")

    @tag("write")
    @task(2)
    def toggle_interest(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.put(
            f"/api/v1/product/{pid}/interest",
            json={"interested": random.choice([True, False])},
            catch_response=True,
            name="PUT /product/[id]/interest",
        ) as r:
            handle(r, "toggle interest")

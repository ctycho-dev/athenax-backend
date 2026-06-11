"""Anonymous visitor persona — public read endpoints only.

Weight 10: dominates traffic, as it does in production.
All tasks are tagged @tag("read") so --tags read gives a safe smoke test.
"""
import random

from locust import HttpUser, between, tag, task

from common import (
    CACHE,
    SEARCH_TERMS,
    SORT_OPTIONS,
    assign_fake_ip,
    handle,
    hot_pick,
    populate_cache,
)


class AnonymousVisitor(HttpUser):
    weight = 10
    wait_time = between(0.5, 2.0)

    def on_start(self):
        assign_fake_ip(self)
        populate_cache(self.client)

    # --- Product reads (core browse path) ---

    @tag("read")
    @task(10)
    def browse_products(self):
        params: dict[str, object] = {
            "limit": random.choice([20, 50]),
            "offset": random.choice([0, 0, 0, 20, 50]),
        }
        roll = random.random()
        if roll < 0.35 and CACHE["category_ids"]:
            params["categoryId"] = hot_pick(CACHE["category_ids"])
        elif roll < 0.55:
            params["sortBy"] = random.choice(SORT_OPTIONS)
        elif roll < 0.70:
            params["q"] = random.choice(SEARCH_TERMS)
        elif roll < 0.80:
            params["dateFilter"] = random.choice(["today", "this_week", "this_month", "this_year"])
        with self.client.get(
            "/api/v1/product/", params=params, catch_response=True, name="GET /product/ (list)"
        ) as r:
            handle(r, "product list")

    @tag("read")
    @task(6)
    def view_product_detail(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}", catch_response=True, name="GET /product/[id]"
        ) as r:
            handle(r, "product detail")

    @tag("read")
    @task(3)
    def view_by_slug(self):
        slug = hot_pick(CACHE["product_slugs"])
        if slug is None:
            return
        with self.client.get(
            f"/api/v1/product/slug/{slug}", catch_response=True, name="GET /product/slug/[slug]"
        ) as r:
            handle(r, "product by slug")

    @tag("read")
    @task(2)
    def similar_products(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/similar?limit=5",
            catch_response=True,
            name="GET /product/[id]/similar",
        ) as r:
            handle(r, "similar products")

    @tag("read")
    @task(2)
    def product_comments(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/comments?limit=20",
            catch_response=True,
            name="GET /product/[id]/comments",
        ) as r:
            handle(r, "product comments")

    @tag("read")
    @task(1)
    def product_links(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/links", catch_response=True, name="GET /product/[id]/links"
        ) as r:
            handle(r, "product links")

    @tag("read")
    @task(1)
    def product_media(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/media", catch_response=True, name="GET /product/[id]/media"
        ) as r:
            handle(r, "product media")

    @tag("read")
    @task(1)
    def product_team(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/team", catch_response=True, name="GET /product/[id]/team"
        ) as r:
            handle(r, "product team")

    @tag("read")
    @task(1)
    def product_backers(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/backers",
            catch_response=True,
            name="GET /product/[id]/backers",
        ) as r:
            handle(r, "product backers")

    @tag("read")
    @task(1)
    def product_voices(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/voices", catch_response=True, name="GET /product/[id]/voices"
        ) as r:
            handle(r, "product voices")

    @tag("read")
    @task(1)
    def product_bounties(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.get(
            f"/api/v1/product/{pid}/bounties",
            catch_response=True,
            name="GET /product/[id]/bounties",
        ) as r:
            handle(r, "product bounties")

    @tag("read")
    @task(1)
    def product_stats(self):
        with self.client.get(
            "/api/v1/product/stats", catch_response=True, name="GET /product/stats"
        ) as r:
            handle(r, "product stats")

    @tag("read")
    @task(1)
    def product_stages(self):
        # No rate limit on this endpoint
        with self.client.get(
            "/api/v1/product/stages", catch_response=True, name="GET /product/stages"
        ) as r:
            handle(r, "product stages")

    # --- Category / article / broadcast reads ---

    @tag("read")
    @task(3)
    def list_categories(self):
        with self.client.get(
            "/api/v1/category/?limit=50", catch_response=True, name="GET /category/ (list)"
        ) as r:
            handle(r, "category list")

    @tag("read")
    @task(3)
    def list_articles(self):
        with self.client.get(
            "/api/v1/article/?limit=50", catch_response=True, name="GET /article/ (list)"
        ) as r:
            handle(r, "article list")

    @tag("read")
    @task(2)
    def view_article_detail(self):
        aid = hot_pick(CACHE["article_ids"])
        if aid is None:
            return
        with self.client.get(
            f"/api/v1/article/{aid}", catch_response=True, name="GET /article/[id]"
        ) as r:
            handle(r, "article detail")

    @tag("read")
    @task(1)
    def view_article_by_slug(self):
        slug = hot_pick(CACHE["article_slugs"])
        if slug is None:
            return
        with self.client.get(
            f"/api/v1/article/slug/{slug}", catch_response=True, name="GET /article/slug/[slug]"
        ) as r:
            handle(r, "article by slug")

    @tag("read")
    @task(3)
    def list_broadcasts(self):
        with self.client.get(
            "/api/v1/broadcast/?limit=50", catch_response=True, name="GET /broadcast/ (list)"
        ) as r:
            handle(r, "broadcast list")

    @tag("read")
    @task(2)
    def view_broadcast_detail(self):
        bid = hot_pick(CACHE["broadcast_ids"])
        if bid is None:
            return
        with self.client.get(
            f"/api/v1/broadcast/{bid}", catch_response=True, name="GET /broadcast/[id]"
        ) as r:
            handle(r, "broadcast detail")

    @tag("read")
    @task(1)
    def view_broadcast_by_slug(self):
        slug = hot_pick(CACHE["broadcast_slugs"])
        if slug is None:
            return
        with self.client.get(
            f"/api/v1/broadcast/slug/{slug}", catch_response=True, name="GET /broadcast/slug/[slug]"
        ) as r:
            handle(r, "broadcast by slug")

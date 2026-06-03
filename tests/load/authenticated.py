"""Authenticated user persona — public reads plus vote, bookmark, comment, create-product.

Weight 4: secondary traffic tier after anonymous.
Write tasks are create-then-immediately-delete to avoid accumulating state.
"""
import random
import string

from locust import HttpUser, between, tag, task

from common import (
    CACHE,
    SORT_OPTIONS,
    USER_POOL,
    assign_fake_ip,
    handle,
    hot_pick,
    login,
    populate_cache,
)


def _rand(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


class AuthenticatedUser(HttpUser):
    weight = 4
    wait_time = between(1.0, 3.0)

    def on_start(self):
        assign_fake_ip(self)
        email, password = random.choice(USER_POOL)
        login(self.client, email, password)
        populate_cache(self.client)

    # --- Read tasks ---

    @tag("read")
    @task(8)
    def browse_products(self):
        params: dict[str, object] = {"limit": 20, "offset": random.choice([0, 0, 20])}
        roll = random.random()
        if roll < 0.4 and CACHE["category_ids"]:
            params["categoryId"] = hot_pick(CACHE["category_ids"])
        elif roll < 0.7:
            params["sortBy"] = random.choice(SORT_OPTIONS)
        with self.client.get(
            "/api/v1/product/", params=params, catch_response=True, name="GET /product/ (list)"
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

    @tag("read")
    @task(2)
    def list_my_products(self):
        with self.client.get(
            "/api/v1/product/me?limit=20", catch_response=True, name="GET /product/me"
        ) as r:
            handle(r, "my products")

    @tag("read")
    @task(1)
    def list_voted(self):
        with self.client.get(
            "/api/v1/product/me/voted?limit=20", catch_response=True, name="GET /product/me/voted"
        ) as r:
            handle(r, "voted products")

    @tag("read")
    @task(1)
    def list_bookmarked(self):
        with self.client.get(
            "/api/v1/product/me/bookmarked?limit=20",
            catch_response=True,
            name="GET /product/me/bookmarked",
        ) as r:
            handle(r, "bookmarked products")

    # --- Write tasks ---

    @tag("write")
    @task(3)
    def toggle_vote(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.put(
            f"/api/v1/product/{pid}/vote",
            json={"voted": random.choice([True, False])},
            catch_response=True,
            name="PUT /product/[id]/vote",
        ) as r:
            handle(r, "toggle vote")

    @tag("write")
    @task(3)
    def toggle_bookmark(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.put(
            f"/api/v1/product/{pid}/bookmark",
            json={"bookmarked": random.choice([True, False])},
            catch_response=True,
            name="PUT /product/[id]/bookmark",
        ) as r:
            handle(r, "toggle bookmark")

    @tag("write")
    @task(2)
    def post_then_delete_comment(self):
        """Create a comment then immediately delete it — net-zero state change."""
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.post(
            f"/api/v1/product/{pid}/comments",
            json={"text": f"Load test comment {_rand()}"},
            catch_response=True,
            name="POST /product/[id]/comments",
        ) as r:
            handle(r, "create comment")
            if r.status_code == 201:
                cid = r.json().get("id")
                if cid:
                    with self.client.delete(
                        f"/api/v1/product/{pid}/comments/{cid}",
                        catch_response=True,
                        name="DELETE /product/[id]/comments/[cid]",
                    ) as dr:
                        handle(dr, "delete comment")

    @tag("write")
    @task(1)
    def create_then_delete_product(self):
        """Create a product then immediately delete it — exercises the create/delete path."""
        category_id = hot_pick(CACHE["category_ids"])
        with self.client.post(
            "/api/v1/product",
            json={
                "name": f"Load Test Product {_rand(6)}",
                "shortDesc": "Automated load test product",
                "categoryIds": [category_id] if category_id else [],
            },
            catch_response=True,
            name="POST /product (create)",
        ) as r:
            handle(r, "create product")
            if r.status_code == 201:
                pid = r.json().get("id")
                if pid:
                    with self.client.delete(
                        f"/api/v1/product/{pid}",
                        catch_response=True,
                        name="DELETE /product/[id]",
                    ) as dr:
                        handle(dr, "delete product")

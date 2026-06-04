"""Admin persona — content management CRUD and isolated upload tasks.

Weight 1: rare traffic tier; uses longer think-time to reflect real admin cadence.

Upload tasks are tagged @tag("upload") and excluded from the default run.
Pass --tags upload explicitly to include them. They require R2 storage to be
configured on the target instance — never run against prod.
"""
import io
import random
import string

from locust import HttpUser, between, tag, task

from common import (
    CACHE,
    ADMIN_POOL,
    assign_fake_ip,
    handle,
    hot_pick,
    login,
    populate_cache,
)


def _rand(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=n))


class AdminUser(HttpUser):
    weight = 1
    wait_time = between(2.0, 5.0)

    def on_start(self):
        assign_fake_ip(self)
        email, password = random.choice(ADMIN_POOL)
        login(self.client, email, password)
        populate_cache(self.client)

    @tag("read")
    @task(3)
    def browse_products(self):
        with self.client.get(
            "/api/v1/product/?limit=50", catch_response=True, name="GET /product/ (list)"
        ) as r:
            handle(r, "product list")

    @tag("admin")
    @task(3)
    def patch_product_status(self):
        """Set status to approved — idempotent, safe to repeat."""
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.patch(
            f"/api/v1/product/{pid}/status",
            json={"status": "approved"},
            catch_response=True,
            name="PATCH /product/[id]/status",
        ) as r:
            handle(r, "patch product status")

    @tag("admin")
    @task(2)
    def create_delete_voice(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.post(
            f"/api/v1/product/{pid}/voices",
            json={
                "quote": f"Load test voice {_rand()}",
                "authorHandle": f"@tester_{_rand(4)}",
                "sortOrder": 0,
            },
            catch_response=True,
            name="POST /product/[id]/voices",
        ) as r:
            handle(r, "create voice")
            if r.status_code == 201:
                vid = r.json().get("id")
                if vid:
                    with self.client.delete(
                        f"/api/v1/product/{pid}/voices/{vid}",
                        catch_response=True,
                        name="DELETE /product/[id]/voices/[vid]",
                    ) as dr:
                        handle(dr, "delete voice")

    @tag("admin")
    @task(2)
    def create_delete_bounty(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.post(
            f"/api/v1/product/{pid}/bounties",
            json={
                "title": f"Load Test Bounty {_rand(5)}",
                "rewardAmount": "100.00",
                "externalUrl": "https://example.com/bounty",
            },
            catch_response=True,
            name="POST /product/[id]/bounties",
        ) as r:
            handle(r, "create bounty")
            if r.status_code == 201:
                bid = r.json().get("id")
                if bid:
                    with self.client.delete(
                        f"/api/v1/product/{pid}/bounties/{bid}",
                        catch_response=True,
                        name="DELETE /product/[id]/bounties/[bid]",
                    ) as dr:
                        handle(dr, "delete bounty")

    @tag("admin")
    @task(2)
    def create_delete_team_member(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.post(
            f"/api/v1/product/{pid}/team",
            json={
                "name": f"Load Tester {_rand(4).title()}",
                "roleLabel": "QA Engineer",
            },
            catch_response=True,
            name="POST /product/[id]/team",
        ) as r:
            handle(r, "create team member")
            if r.status_code == 201:
                mid = r.json().get("id")
                if mid:
                    with self.client.delete(
                        f"/api/v1/product/{pid}/team/{mid}",
                        catch_response=True,
                        name="DELETE /product/[id]/team/[mid]",
                    ) as dr:
                        handle(dr, "delete team member")

    @tag("admin")
    @task(1)
    def create_pin_delete_comment(self):
        """Create a comment, pin it, delete it — exercises the pin endpoint with no lasting state."""
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        with self.client.post(
            f"/api/v1/product/{pid}/comments",
            json={"text": f"Admin pin test {_rand()}"},
            catch_response=True,
            name="POST /product/[id]/comments",
        ) as r:
            handle(r, "create comment (admin)")
            if r.status_code == 201:
                cid = r.json().get("id")
                if cid:
                    with self.client.patch(
                        f"/api/v1/product/{pid}/comments/{cid}/pin",
                        json={"pinned": True},
                        catch_response=True,
                        name="PATCH /product/[id]/comments/[cid]/pin",
                    ) as pr:
                        handle(pr, "pin comment")
                    with self.client.delete(
                        f"/api/v1/product/{pid}/comments/{cid}",
                        catch_response=True,
                        name="DELETE /product/[id]/comments/[cid]",
                    ) as dr:
                        handle(dr, "delete comment (admin)")

    # --- Upload tasks — excluded from default run, require R2 storage ---
    # Run with: locust ... --tags upload

    @tag("upload")
    @task(1)
    def upload_media(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        # Minimal valid GIF so the upload doesn't fail image validation
        gif = io.BytesIO(
            b"GIF89a\x01\x00\x01\x00\x00\xff\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"
        )
        with self.client.post(
            f"/api/v1/product/{pid}/media/upload",
            files={"file": ("test.gif", gif, "image/gif")},
            data={"mediaType": "image"},
            catch_response=True,
            name="POST /product/[id]/media/upload",
        ) as r:
            handle(r, "upload media")

    @tag("upload")
    @task(1)
    def upload_logo(self):
        pid = hot_pick(CACHE["product_ids"])
        if pid is None:
            return
        gif = io.BytesIO(
            b"GIF89a\x01\x00\x01\x00\x00\xff\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"
        )
        with self.client.post(
            f"/api/v1/product/{pid}/logo/upload",
            files={"file": ("logo.gif", gif, "image/gif")},
            catch_response=True,
            name="POST /product/[id]/logo/upload",
        ) as r:
            handle(r, "upload logo")

"""End-to-end tests for the Blog Posts Manager API.

Data tests run against the configured Supabase project and clean up after
themselves: any post, comment or upload created during a test is deleted at
the end, so the suite never leaves artifacts behind.

When Supabase is not configured (for example in CI without secrets), data
tests are skipped and only the health check runs.
"""

import base64
import unittest

from starlette.testclient import TestClient

from app import app
from backend.supabase_client import is_supabase_configured
from backend.routes.upload import UPLOAD_DIR

client = TestClient(app)
DB_CONFIGURED = is_supabase_configured()

# Smallest valid PNG (1x1 transparent pixel).
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class TestHealth(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "OK")

    def test_api_health(self):
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["backend"], "FastAPI")


@unittest.skipUnless(DB_CONFIGURED, "Supabase is not configured")
class TestBlogFeatures(unittest.TestCase):
    def test_list_posts(self):
        response = client.get("/items")
        self.assertEqual(response.status_code, 200)
        posts = response.json()
        self.assertIsInstance(posts, list)
        self.assertGreaterEqual(len(posts), 1)
        for key in ("id", "title", "content", "author_name", "likes_count",
                    "comments_count", "shares_count", "is_liked"):
            self.assertIn(key, posts[0])

    def test_filters_and_sorting(self):
        recent = client.get("/items", params={"sort": "recent"}).json()
        popular = client.get("/items", params={"sort": "likes"}).json()
        self.assertEqual(len(recent), len(popular))

        design = client.get("/items", params={"category": "Design"}).json()
        self.assertTrue(all(post["category"] == "Design" for post in design))

        search = client.get("/items", params={"search": "fastapi"}).json()
        self.assertTrue(any("FastAPI" in post["title"] for post in search))

    def test_post_lifecycle(self):
        """Create -> like -> comment -> share -> delete (with cleanup)."""
        created = client.post(
            "/items",
            json={
                "title": "Continuous Integration Test Post",
                "content": "Temporary post created by the test-suite. It is deleted at the end of the test.",
                "category": "Engineering",
                "author_id": "user_admin",
            },
        )
        self.assertEqual(created.status_code, 201)
        post = created.json()
        post_id = post["id"]

        try:
            self.assertEqual(post["title"], "Continuous Integration Test Post")

            liked = client.post(f"/api/posts/{post_id}/like", json={"user_id": "user_admin"})
            self.assertEqual(liked.status_code, 200)
            self.assertTrue(liked.json()["liked"])

            unliked = client.post(f"/api/posts/{post_id}/like", json={"user_id": "user_admin"})
            self.assertFalse(unliked.json()["liked"])
            self.assertEqual(unliked.json()["likes_count"], 0)

            comment = client.post(
                f"/api/posts/{post_id}/comments",
                json={"content": "Testing comment functionality.", "author_id": "user_admin"},
            )
            self.assertEqual(comment.status_code, 201)
            comment_id = comment.json()["id"]

            comments = client.get(f"/api/posts/{post_id}/comments")
            self.assertEqual(len(comments.json()), 1)

            removed = client.delete(f"/api/comments/{comment_id}")
            self.assertEqual(removed.status_code, 200)
            self.assertEqual(client.get(f"/api/posts/{post_id}/comments").json(), [])

            share = client.post(
                f"/api/posts/{post_id}/share",
                json={"platform": "twitter", "user_id": "user_admin"},
            )
            self.assertEqual(share.status_code, 200)
            self.assertEqual(share.json()["shares_count"], 1)

            fetched = client.get(f"/api/posts/{post_id}")
            self.assertEqual(fetched.status_code, 200)
            self.assertEqual(fetched.json()["id"], post_id)
        finally:
            deleted = client.delete(f"/api/posts/{post_id}")
            self.assertEqual(deleted.status_code, 200)

        self.assertEqual(client.get(f"/api/posts/{post_id}").status_code, 404)

    def test_profiles(self):
        profiles = client.get("/api/profiles")
        self.assertEqual(profiles.status_code, 200)
        self.assertGreaterEqual(len(profiles.json()), 1)

        admin = client.get("/api/profiles/user_admin")
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(admin.json()["username"], "faruk_dev")
        self.assertIn("posts_count", admin.json())

    def test_upload_and_cleanup(self):
        response = client.post(
            "/api/upload",
            files={"file": ("pixel.png", PNG_BYTES, "image/png")},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["url"].startswith("/uploads/"))
        self.assertTrue(payload["size"] > 0)

        uploaded = UPLOAD_DIR / payload["filename"]
        self.assertTrue(uploaded.exists())
        uploaded.unlink()  # keep the uploads directory clean

    def test_rejects_unsupported_upload(self):
        response = client.post(
            "/api/upload",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

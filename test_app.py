"""End-to-end tests for the Blog Posts Manager API.

Data tests run against the configured Supabase project and clean up after
themselves: test users, posts, comments and uploads are all removed at the
end, so the suite never leaves artifacts behind. Test users are created
directly in the database (not via /signup) so they never claim the
first-user admin inheritance.

When Supabase is not configured (for example in CI without secrets), data
tests are skipped and only the health check runs.
"""

import base64
import unittest
import uuid

from starlette.testclient import TestClient

from app import app
from backend import database
from backend import embeddings as embedding_module
from backend.routes.upload import UPLOAD_DIR
from backend.security import hash_password
from backend.supabase_client import is_supabase_configured, supabase

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
class TestAuthAndBlog(unittest.TestCase):
    """Full feature suite against the live database, using a throwaway user."""

    @classmethod
    def setUpClass(cls):
        suffix = uuid.uuid4().hex[:10]
        cls.email = f"pytest-{suffix}@example.com"
        cls.password = "pytest-pass-123"
        cls.user = database.create_user(cls.email, hash_password(cls.password), is_admin=False)
        cls.user_id = str(cls.user["id"])
        cls.profile = database.create_profile(
            profile_id=cls.user_id,
            username=f"pytest_{suffix}",
            display_name="Pytest User",
            user_id=cls.user_id,
            email=cls.email,
        )
        cls.profile_id = cls.profile["id"]

        # Semantic model: warm once and backfill so vector tests are meaningful.
        cls.semantic = embedding_module.available()
        if cls.semantic:
            database.backfill_embeddings()

    @classmethod
    def tearDownClass(cls):
        # Remove everything this suite created.
        supabase.table("posts").delete().eq("author_id", cls.profile_id).execute()
        supabase.table("profiles").delete().eq("id", cls.profile_id).execute()
        database.delete_user(cls.user_id)

    # ---------------- helpers ----------------
    def login(self, email=None, password=None):
        response = client.post(
            "/api/auth/login",
            json={"email": email or self.email, "password": password or self.password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        return payload["access_token"], payload["refresh_token"]

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def create_post(self, token, **overrides):
        payload = {
            "title": "Pytest Post",
            "content": "Created by the test-suite and removed afterwards.",
            "category": "Engineering",
        }
        payload.update(overrides)
        response = client.post("/api/posts", json=payload, headers=self.auth(token))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    # ---------------- auth ----------------
    def test_01_health_gate_when_configured(self):
        self.assertTrue(DB_CONFIGURED)

    def test_02_signup_login_refresh_logout(self):
        email = f"pytest-signup-{uuid.uuid4().hex[:8]}@example.com"
        password = "signup-pass-123"

        signup = client.post(
            "/api/auth/signup",
            json={"email": email, "password": password, "display_name": "Signup Tester"},
        )
        self.assertEqual(signup.status_code, 201, signup.text)
        body = signup.json()
        self.assertFalse(body["user"]["is_admin"])  # users already exist in the DB
        token, refresh_token = body["access_token"], body["refresh_token"]

        try:
            # duplicate email is rejected
            duplicate = client.post(
                "/api/auth/signup", json={"email": email, "password": password}
            )
            self.assertEqual(duplicate.status_code, 409)

            # invalid email is rejected
            invalid = client.post(
                "/api/auth/signup", json={"email": "not-an-email", "password": password}
            )
            self.assertIn(invalid.status_code, (400, 422))

            # wrong password is rejected
            wrong = client.post(
                "/api/auth/login", json={"email": email, "password": "wrong-password"}
            )
            self.assertEqual(wrong.status_code, 401)

            # /me works with the access token
            me = client.get("/api/auth/me", headers=self.auth(token))
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["user"]["email"], email)

            # refresh rotates the token
            refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
            self.assertEqual(refreshed.status_code, 200, refreshed.text)
            new_refresh = refreshed.json()["refresh_token"]
            self.assertNotEqual(new_refresh, refresh_token)

            # old refresh token is revoked by rotation
            replay = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
            self.assertEqual(replay.status_code, 401)

            # logout revokes the new refresh token
            logout = client.post(
                "/api/auth/logout",
                json={"refresh_token": new_refresh},
                headers=self.auth(refreshed.json()["access_token"]),
            )
            self.assertEqual(logout.status_code, 204)
            after_logout = client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
            self.assertEqual(after_logout.status_code, 401)
        finally:
            user = database.get_user_by_email(email)
            if user:
                profile = database.get_profile_by_user_id(str(user["id"]))
                if profile:
                    supabase.table("posts").delete().eq("author_id", profile["id"]).execute()
                    database.delete_profile(profile["id"])
                database.delete_user(str(user["id"]))

    def test_03_password_change(self):
        token, _ = self.login()
        changed = client.put(
            "/api/auth/password",
            json={"current_password": self.password, "new_password": "new-pytest-pass-456"},
            headers=self.auth(token),
        )
        self.assertEqual(changed.status_code, 200, changed.text)

        # old password no longer works, new one does
        self.assertEqual(
            client.post("/api/auth/login", json={"email": self.email, "password": self.password}).status_code,
            401,
        )
        token2, _ = self.login(password="new-pytest-pass-456")

        # restore the original password for other tests
        restored = client.put(
            "/api/auth/password",
            json={"current_password": "new-pytest-pass-456", "new_password": self.password},
            headers=self.auth(token2),
        )
        self.assertEqual(restored.status_code, 200)

    def test_04_protected_endpoints_require_auth(self):
        self.assertEqual(client.post("/api/posts", json={"title": "x", "content": "y"}).status_code, 401)
        self.assertEqual(client.post("/api/posts/1/like", json={}).status_code, 401)
        self.assertEqual(client.post("/api/posts/1/comments", json={"content": "x"}).status_code, 401)
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertEqual(client.get("/api/posts?status=draft").status_code, 401)

    # ---------------- blog lifecycle ----------------
    def test_05_post_lifecycle(self):
        token, _ = self.login()
        post = self.create_post(token, title="Lifecycle Test", content="Lifecycle body with zanzibarium marker.")
        post_id = post["id"]

        try:
            self.assertEqual(post["status"], "published")
            self.assertTrue(post["slug"])

            updated = client.put(
                f"/api/posts/{post_id}",
                json={"title": "Lifecycle Test (edited)"},
                headers=self.auth(token),
            )
            self.assertEqual(updated.status_code, 200)
            self.assertEqual(updated.json()["title"], "Lifecycle Test (edited)")

            detail = client.get(f"/api/posts/{post_id}")
            self.assertEqual(detail.status_code, 200)
            self.assertGreaterEqual(detail.json()["views_count"], 1)

            liked = client.post(f"/api/posts/{post_id}/like", json={}, headers=self.auth(token))
            self.assertTrue(liked.json()["liked"])
            unliked = client.post(f"/api/posts/{post_id}/like", json={}, headers=self.auth(token))
            self.assertFalse(unliked.json()["liked"])

            comment = client.post(
                f"/api/posts/{post_id}/comments",
                json={"content": "Lifecycle comment"},
                headers=self.auth(token),
            )
            self.assertEqual(comment.status_code, 201)
            comment_id = comment.json()["id"]
            self.assertEqual(len(client.get(f"/api/posts/{post_id}/comments").json()), 1)
            self.assertEqual(
                client.delete(f"/api/comments/{comment_id}", headers=self.auth(token)).status_code, 200
            )

            share = client.post(
                f"/api/posts/{post_id}/share",
                json={"platform": "twitter"},
                headers=self.auth(token),
            )
            self.assertEqual(share.json()["shares_count"], 1)
        finally:
            self.assertEqual(
                client.delete(f"/api/posts/{post_id}", headers=self.auth(token)).status_code, 200
            )
        self.assertEqual(client.get(f"/api/posts/{post_id}").status_code, 404)

    def test_06_drafts(self):
        token, _ = self.login()
        draft = self.create_post(token, title="Draft Only Test", status="draft")
        draft_id = draft["id"]

        try:
            self.assertEqual(draft["status"], "draft")

            public = client.get("/api/posts", params={"limit": 50}).json()
            self.assertFalse(any(p["id"] == draft_id for p in public))

            self.assertEqual(client.get(f"/api/posts/{draft_id}").status_code, 404)

            mine = client.get("/api/posts", params={"status": "draft"}, headers=self.auth(token)).json()
            self.assertTrue(any(p["id"] == draft_id for p in mine))

            published = client.put(
                f"/api/posts/{draft_id}", json={"status": "published"}, headers=self.auth(token)
            )
            self.assertEqual(published.json()["status"], "published")
            self.assertEqual(client.get(f"/api/posts/{draft_id}").status_code, 200)
        finally:
            client.delete(f"/api/posts/{draft_id}", headers=self.auth(token))

    def test_07_ownership(self):
        token, _ = self.login()
        post = self.create_post(token, title="Ownership Test")
        post_id = post["id"]

        other_email = f"pytest-other-{uuid.uuid4().hex[:8]}@example.com"
        other_user = database.create_user(other_email, hash_password("other-pass-123"))
        other_user_id = str(other_user["id"])
        other_profile = database.create_profile(
            other_user_id, f"other_{uuid.uuid4().hex[:8]}", "Other User", other_user_id, other_email
        )

        try:
            _, other_refresh = self.login(other_email, "other-pass-123")
            other_login = client.post(
                "/api/auth/login", json={"email": other_email, "password": "other-pass-123"}
            )
            other_token = other_login.json()["access_token"]

            denied_edit = client.put(
                f"/api/posts/{post_id}", json={"title": "Hijacked"}, headers=self.auth(other_token)
            )
            self.assertEqual(denied_edit.status_code, 403)
            denied_delete = client.delete(f"/api/posts/{post_id}", headers=self.auth(other_token))
            self.assertEqual(denied_delete.status_code, 403)
            self.assertIsNotNone(other_refresh)
        finally:
            client.delete(f"/api/posts/{post_id}", headers=self.auth(token))
            database.delete_user(other_user_id)
            database.delete_profile(other_profile["id"])

    # ---------------- search & recommendations ----------------
    def test_08_search_and_recommendations(self):
        token, _ = self.login()
        marker = f"zqmarker{uuid.uuid4().hex[:8]}"
        post = self.create_post(
            token, title=f"Search Target {marker}", content=f"Full text body containing {marker}."
        )

        try:
            results = client.get("/api/posts", params={"q": marker}).json()
            # Exact keyword match ranks first (semantic matches may follow).
            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0]["id"], post["id"])

            related = client.get("/api/posts/1/related").json()
            self.assertGreaterEqual(len(related), 1)

            for_auth = client.get("/api/feed/recommended", headers=self.auth(token)).json()
            self.assertGreaterEqual(len(for_auth), 1)
            for_anon = client.get("/api/feed/recommended").json()
            self.assertGreaterEqual(len(for_anon), 1)
        finally:
            client.delete(f"/api/posts/{post['id']}", headers=self.auth(token))

    # ---------------- semantic search & embeddings ----------------
    def test_12_embeddings_are_populated(self):
        if not self.semantic:
            self.skipTest("embedding model unavailable in this environment")
        row = supabase.table("posts").select("id,embedding").eq("id", 1).limit(1).execute()
        self.assertTrue(row.data)
        self.assertIsNotNone(row.data[0].get("embedding"))

    def test_13_semantic_search_matches_meaning(self):
        """A query with no keyword overlap should still find the right post."""
        if not self.semantic:
            self.skipTest("embedding model unavailable in this environment")

        token, _ = self.login()
        post = self.create_post(
            token,
            title="Deep Sea Expedition Notes",
            content="Observations of whales, dolphins, seals and coral reefs during an eight-week Pacific voyage.",
        )
        try:
            # No shared words with the post: text search alone returns nothing.
            results = client.get("/api/posts", params={"q": "marine mammals in the ocean"}).json()
            top_ids = [item["id"] for item in results[:5]]
            self.assertIn(post["id"], top_ids, "semantic search did not surface the marine-life post")
        finally:
            client.delete(f"/api/posts/{post['id']}", headers=self.auth(token))

    # ---------------- profile & preferences ----------------
    def test_09_me_and_preferences(self):
        token, _ = self.login()

        me = client.get("/api/me", headers=self.auth(token))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["id"], self.user_id)

        profile_update = client.put(
            "/api/me", json={"tagline": "Testing tagline"}, headers=self.auth(token)
        )
        self.assertEqual(profile_update.status_code, 200, profile_update.text)
        self.assertEqual(profile_update.json()["tagline"], "Testing tagline")

        defaults = client.get("/api/me/preferences", headers=self.auth(token)).json()
        self.assertIn(defaults["theme"], ("light", "dark", "system"))

        updated = client.put(
            "/api/me/preferences",
            json={"theme": "dark", "favorite_categories": ["Engineering"], "default_sort": "likes"},
            headers=self.auth(token),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["theme"], "dark")
        self.assertEqual(updated.json()["favorite_categories"], ["Engineering"])

        invalid = client.put(
            "/api/me/preferences", json={"theme": "neon"}, headers=self.auth(token)
        )
        self.assertEqual(invalid.status_code, 422)

        # users cannot edit someone else's profile
        foreign = client.put(
            "/api/profiles/user_admin", json={"display_name": "Hacked"}, headers=self.auth(token)
        )
        self.assertEqual(foreign.status_code, 403)

    def test_10_profiles_are_public(self):
        profiles = client.get("/api/profiles")
        self.assertEqual(profiles.status_code, 200)
        self.assertGreaterEqual(len(profiles.json()), 1)

        admin = client.get("/api/profiles/user_admin")
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(admin.json()["username"], "faruk_dev")
        self.assertIn("posts_count", admin.json())

    # ---------------- uploads ----------------
    def test_11_upload_requires_auth_and_cleans_up(self):
        unauthenticated = client.post(
            "/api/upload", files={"file": ("pixel.png", PNG_BYTES, "image/png")}
        )
        self.assertEqual(unauthenticated.status_code, 401)

        token, _ = self.login()
        response = client.post(
            "/api/upload",
            files={"file": ("pixel.png", PNG_BYTES, "image/png")},
            headers=self.auth(token),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["url"].startswith("/uploads/"))

        uploaded = UPLOAD_DIR / payload["filename"]
        self.assertTrue(uploaded.exists())
        uploaded.unlink()

        rejected = client.post(
            "/api/upload",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
            headers=self.auth(token),
        )
        self.assertEqual(rejected.status_code, 400)


if __name__ == "__main__":
    unittest.main()

import unittest
from starlette.testclient import TestClient
from app import app

client = TestClient(app)

class TestBlogApp(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "OK")

    def test_get_items(self):
        response = client.get("/items")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_post_lifecycle(self):
        # 1. Create Post
        new_post = {
            "title": "Continuous Integration Test Post",
            "content": "Verifying that the FastAPI endpoints, likes, comments, and shares operate smoothly.",
            "category": "Engineering",
            "author_id": "user_admin"
        }
        create_resp = client.post("/items", json=new_post)
        self.assertEqual(create_resp.status_code, 201)
        post = create_resp.json()
        post_id = post["id"]
        self.assertEqual(post["title"], new_post["title"])

        # 2. Like Post
        like_resp = client.post(f"/api/posts/{post_id}/like", json={"user_id": "user_admin"})
        self.assertEqual(like_resp.status_code, 200)
        self.assertTrue(like_resp.json()["liked"])

        # 3. Add Comment
        comment_resp = client.post(f"/api/posts/{post_id}/comments", json={
            "content": "Testing comment functionality!",
            "author_id": "user_admin"
        })
        self.assertEqual(comment_resp.status_code, 201)
        self.assertEqual(comment_resp.json()["content"], "Testing comment functionality!")

        # 4. Share Post
        share_resp = client.post(f"/api/posts/{post_id}/share", json={
            "platform": "twitter",
            "user_id": "user_admin"
        })
        self.assertEqual(share_resp.status_code, 200)
        self.assertGreaterEqual(share_resp.json()["shares_count"], 1)

        # 5. Profile Retrieval
        profile_resp = client.get("/api/profiles/user_admin")
        self.assertEqual(profile_resp.status_code, 200)
        self.assertEqual(profile_resp.json()["username"], "faruk_dev")

if __name__ == "__main__":
    unittest.main()
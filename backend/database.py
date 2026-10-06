import math
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from backend.supabase_client import supabase, is_supabase_configured

# ---------------- Initial In-Memory / Local Seed Data ----------------
LOCAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "user_admin": {
        "id": "user_admin",
        "username": "faruk_dev",
        "display_name": "Faruk Developer",
        "email": "faruk@example.com",
        "bio": "DevOps engineer & full-stack architect passionate about clean code, high-throughput systems, and minimalist aesthetics.",
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200&auto=format&fit=crop&q=80",
        "website": "https://github.com/Faruk1350",
        "location": "San Francisco, CA",
        "created_at": "2026-01-15T10:00:00Z"
    },
    "user_sarah": {
        "id": "user_sarah",
        "username": "sarah_design",
        "display_name": "Sarah Chen",
        "email": "sarah@example.com",
        "bio": "Product designer & typography obsessive. Crafting intuitive design systems and modern web experiences.",
        "avatar_url": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1557683316-973673baf926?w=1200&auto=format&fit=crop&q=80",
        "website": "https://sarahchen.design",
        "location": "Toronto, ON",
        "created_at": "2026-02-01T12:00:00Z"
    },
    "user_alex": {
        "id": "user_alex",
        "username": "alex_ross",
        "display_name": "Alex Ross",
        "email": "alex@example.com",
        "bio": "Cloud architect & technical writer. Exploring serverless edge computing and asynchronous frameworks.",
        "avatar_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
        "cover_image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=1200&auto=format&fit=crop&q=80",
        "website": "https://alexross.tech",
        "location": "London, UK",
        "created_at": "2026-02-10T14:30:00Z"
    }
}

LOCAL_POSTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Minimalist Design in Digital Interfaces",
        "content": "Minimalism is not the lack of something; it is simply the perfect amount of everything. When crafting software interfaces, eliminating unnecessary visual noise and focusing on clear typographic hierarchy allows users to focus on what matters most.\n\nKey principles for modern minimalism:\n- Intentional whitespace provides breathing room.\n- Subtle, soft tonal contrasts replace harsh borders.\n- Micro-interactions acknowledge user action without distraction.\n- Harmonious color palettes evoke tranquility and trust.",
        "cover_image": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&auto=format&fit=crop&q=80",
        "category": "Design",
        "author_id": "user_sarah",
        "author_name": "Sarah Chen",
        "author_avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
        "read_time": "3 min read",
        "likes_count": 28,
        "comments_count": 3,
        "shares_count": 9,
        "created_at": "2026-10-04T09:15:00Z"
    },
    {
        "id": 2,
        "title": "Why FastAPI is the Future of Python Backends",
        "content": "Transitioning from traditional synchronous frameworks like Flask to FastAPI unlocks massive concurrency and developer ergonomics. With native async/await support, Pydantic type validation, and automatic OpenAPI schema generation, FastAPI delivers industry-leading performance out of the box.\n\nHighlights:\n- Asynchronous ASGI execution powered by Starlette and Uvicorn.\n- Zero boilerplate input parsing and validation.\n- Interactive documentation with Swagger UI and ReDoc.\n- Seamless pairing with modern database clients like Supabase.",
        "cover_image": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80",
        "category": "Engineering",
        "author_id": "user_admin",
        "author_name": "Faruk Developer",
        "author_avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
        "read_time": "4 min read",
        "likes_count": 42,
        "comments_count": 2,
        "shares_count": 14,
        "created_at": "2026-10-05T14:20:00Z"
    },
    {
        "id": 3,
        "title": "Architecting Cloud-Native Workflows with Supabase",
        "content": "PostgreSQL has stood the test of time as one of the most reliable and extensible database engines in computer science. Supabase brings PostgreSQL to the modern developer with instant REST APIs, WebSocket real-time updates, built-in row-level security (RLS), and unified storage.\n\nBy leveraging Supabase alongside modern lightweight web frontends, teams can build reactive, scalable applications in record time without managing complex database clusters.",
        "cover_image": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&auto=format&fit=crop&q=80",
        "category": "Database",
        "author_id": "user_alex",
        "author_name": "Alex Ross",
        "author_avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
        "read_time": "5 min read",
        "likes_count": 35,
        "comments_count": 2,
        "shares_count": 11,
        "created_at": "2026-10-06T06:30:00Z"
    }
]

LOCAL_COMMENTS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "post_id": 1,
        "author_id": "user_admin",
        "author_name": "Faruk Developer",
        "author_avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
        "content": "This emphasis on typography and calm palettes makes reading so effortless. Beautifully articulated!",
        "created_at": "2026-10-04T10:00:00Z"
    },
    {
        "id": 2,
        "post_id": 1,
        "author_id": "user_alex",
        "author_name": "Alex Ross",
        "author_avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
        "content": "Whitespace is truly the most underrated design tool. Excited to apply these guidelines in our next release.",
        "created_at": "2026-10-04T12:30:00Z"
    },
    {
        "id": 3,
        "post_id": 1,
        "author_id": "user_sarah",
        "author_name": "Sarah Chen",
        "author_avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
        "content": "Thank you both! Always happy to see teams adopting calmer digital experiences.",
        "created_at": "2026-10-04T13:45:00Z"
    },
    {
        "id": 4,
        "post_id": 2,
        "author_id": "user_sarah",
        "author_name": "Sarah Chen",
        "author_avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
        "content": "The automatic interactive OpenAPI docs make client integration an absolute breeze.",
        "created_at": "2026-10-05T15:10:00Z"
    },
    {
        "id": 5,
        "post_id": 2,
        "author_id": "user_alex",
        "author_name": "Alex Ross",
        "author_avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
        "content": "Pydantic v2 core speed improvements give FastAPI an incredible boost.",
        "created_at": "2026-10-05T16:20:00Z"
    },
    {
        "id": 6,
        "post_id": 3,
        "author_id": "user_admin",
        "author_name": "Faruk Developer",
        "author_avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
        "content": "PostgreSQL row-level security paired with Supabase Auth completely simplifies backend authorization rules.",
        "created_at": "2026-10-06T07:15:00Z"
    },
    {
        "id": 7,
        "post_id": 3,
        "author_id": "user_sarah",
        "author_name": "Sarah Chen",
        "author_avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
        "content": "Great architectural summary!",
        "created_at": "2026-10-06T08:00:00Z"
    }
]

# Track likes locally: set of (post_id, user_id)
LOCAL_LIKES = {
    (1, "user_admin"),
    (2, "user_admin"),
    (2, "user_sarah"),
    (3, "user_admin")
}

# Track shares count
LOCAL_SHARES = []

def calculate_read_time(content: str) -> str:
    words = len(content.split())
    minutes = max(1, math.ceil(words / 180))
    return f"{minutes} min read"

# ----------------- Database Service Layer -----------------

def get_posts(search: Optional[str] = None, category: Optional[str] = None, sort: str = "recent", current_user_id: str = "user_admin") -> List[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            query = supabase.table("posts").select("*")
            if category and category.lower() != "all":
                query = query.eq("category", category)
            if search:
                query = query.ilike("title", f"%{search}%")
            
            if sort == "likes":
                query = query.order("likes_count", desc=True)
            else:
                query = query.order("created_at", desc=True)

            res = query.execute()
            posts_data = res.data or []
            
            # Check user liked status
            liked_post_ids = set()
            try:
                likes_res = supabase.table("likes").select("post_id").eq("user_id", current_user_id).execute()
                liked_post_ids = {item["post_id"] for item in (likes_res.data or [])}
            except Exception:
                pass

            for post in posts_data:
                post["is_liked"] = post["id"] in liked_post_ids

            return posts_data
        except Exception as e:
            # Fallback to local store if Supabase request fails
            pass

    # Local fallback
    filtered = list(LOCAL_POSTS)
    if category and category.lower() != "all":
        filtered = [p for p in filtered if p.get("category", "").lower() == category.lower()]
    if search:
        s = search.lower()
        filtered = [p for p in filtered if s in p.get("title", "").lower() or s in p.get("content", "").lower() or s in p.get("author_name", "").lower()]
    
    if sort == "likes":
        filtered.sort(key=lambda p: p.get("likes_count", 0), reverse=True)
    else:
        filtered.sort(key=lambda p: p.get("created_at", ""), reverse=True)

    result = []
    for p in filtered:
        item = dict(p)
        item["is_liked"] = (p["id"], current_user_id) in LOCAL_LIKES
        result.append(item)
    return result

def get_post_by_id(post_id: int, current_user_id: str = "user_admin") -> Optional[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            res = supabase.table("posts").select("*").eq("id", post_id).single().execute()
            if res.data:
                post = res.data
                likes_res = supabase.table("likes").select("id").eq("post_id", post_id).eq("user_id", current_user_id).execute()
                post["is_liked"] = bool(likes_res.data)
                return post
        except Exception:
            pass

    for p in LOCAL_POSTS:
        if p["id"] == post_id:
            item = dict(p)
            item["is_liked"] = (post_id, current_user_id) in LOCAL_LIKES
            return item
    return None

def create_post(data: Dict[str, Any]) -> Dict[str, Any]:
    read_time = calculate_read_time(data.get("content", ""))
    now_iso = datetime.now(timezone.utc).isoformat()
    
    author_id = data.get("author_id", "user_admin")
    author_profile = get_profile(author_id)
    author_name = data.get("author_name") or (author_profile["display_name"] if author_profile else "Anonymous")
    author_avatar = data.get("author_avatar") or (author_profile.get("avatar_url") if author_profile else None)

    new_post_payload = {
        "title": data["title"],
        "content": data["content"],
        "cover_image": data.get("cover_image"),
        "category": data.get("category", "General"),
        "author_id": author_id,
        "author_name": author_name,
        "author_avatar": author_avatar,
        "read_time": read_time,
        "likes_count": 0,
        "comments_count": 0,
        "shares_count": 0,
        "created_at": now_iso
    }

    if is_supabase_configured():
        try:
            res = supabase.table("posts").insert(new_post_payload).execute()
            if res.data:
                created = res.data[0]
                created["is_liked"] = False
                return created
        except Exception:
            pass

    new_id = (max([p["id"] for p in LOCAL_POSTS], default=0)) + 1
    new_post_payload["id"] = new_id
    LOCAL_POSTS.insert(0, new_post_payload)
    item = dict(new_post_payload)
    item["is_liked"] = False
    return item

def delete_post(post_id: int) -> bool:
    if is_supabase_configured():
        try:
            supabase.table("posts").delete().eq("id", post_id).execute()
            return True
        except Exception:
            pass

    global LOCAL_POSTS
    orig_len = len(LOCAL_POSTS)
    LOCAL_POSTS = [p for p in LOCAL_POSTS if p["id"] != post_id]
    return len(LOCAL_POSTS) < orig_len

def toggle_like(post_id: int, user_id: str) -> Dict[str, Any]:
    if is_supabase_configured():
        try:
            # Check existing like
            check = supabase.table("likes").select("id").eq("post_id", post_id).eq("user_id", user_id).execute()
            if check.data and len(check.data) > 0:
                # Unlike
                supabase.table("likes").delete().eq("post_id", post_id).eq("user_id", user_id).execute()
                # Decrement like count
                post_res = supabase.table("posts").select("likes_count").eq("id", post_id).single().execute()
                curr_likes = max(0, (post_res.data.get("likes_count") or 1) - 1)
                supabase.table("posts").update({"likes_count": curr_likes}).eq("id", post_id).execute()
                return {"post_id": post_id, "liked": False, "likes_count": curr_likes}
            else:
                # Like
                supabase.table("likes").insert({"post_id": post_id, "user_id": user_id}).execute()
                post_res = supabase.table("posts").select("likes_count").eq("id", post_id).single().execute()
                curr_likes = (post_res.data.get("likes_count") or 0) + 1
                supabase.table("posts").update({"likes_count": curr_likes}).eq("id", post_id).execute()
                return {"post_id": post_id, "liked": True, "likes_count": curr_likes}
        except Exception:
            pass

    key = (post_id, user_id)
    post = next((p for p in LOCAL_POSTS if p["id"] == post_id), None)
    if not post:
        return {"post_id": post_id, "liked": False, "likes_count": 0}

    if key in LOCAL_LIKES:
        LOCAL_LIKES.remove(key)
        post["likes_count"] = max(0, post["likes_count"] - 1)
        liked = False
    else:
        LOCAL_LIKES.add(key)
        post["likes_count"] += 1
        liked = True

    return {"post_id": post_id, "liked": liked, "likes_count": post["likes_count"]}

def record_share(post_id: int, platform: str, user_id: str) -> Dict[str, Any]:
    if is_supabase_configured():
        try:
            supabase.table("shares").insert({
                "post_id": post_id,
                "platform": platform,
                "user_id": user_id
            }).execute()
            post_res = supabase.table("posts").select("shares_count").eq("id", post_id).single().execute()
            curr_shares = (post_res.data.get("shares_count") or 0) + 1
            supabase.table("posts").update({"shares_count": curr_shares}).eq("id", post_id).execute()
            return {"post_id": post_id, "platform": platform, "shares_count": curr_shares, "share_url": f"/post/{post_id}"}
        except Exception:
            pass

    post = next((p for p in LOCAL_POSTS if p["id"] == post_id), None)
    curr_shares = 1
    if post:
        post["shares_count"] = post.get("shares_count", 0) + 1
        curr_shares = post["shares_count"]

    LOCAL_SHARES.append({
        "post_id": post_id,
        "platform": platform,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return {"post_id": post_id, "platform": platform, "shares_count": curr_shares, "share_url": f"/post/{post_id}"}

def get_comments(post_id: int) -> List[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            res = supabase.table("comments").select("*").eq("post_id", post_id).order("created_at", desc=False).execute()
            return res.data or []
        except Exception:
            pass

    return [c for c in LOCAL_COMMENTS if c["post_id"] == post_id]

def add_comment(post_id: int, comment_data: Dict[str, Any]) -> Dict[str, Any]:
    author_id = comment_data.get("author_id", "user_admin")
    profile = get_profile(author_id)
    author_name = comment_data.get("author_name") or (profile["display_name"] if profile else "Reader")
    author_avatar = comment_data.get("author_avatar") or (profile.get("avatar_url") if profile else None)

    payload = {
        "post_id": post_id,
        "author_id": author_id,
        "author_name": author_name,
        "author_avatar": author_avatar,
        "content": comment_data["content"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    if is_supabase_configured():
        try:
            res = supabase.table("comments").insert(payload).execute()
            # update post comments count
            post_res = supabase.table("posts").select("comments_count").eq("id", post_id).single().execute()
            cnt = (post_res.data.get("comments_count") or 0) + 1
            supabase.table("posts").update({"comments_count": cnt}).eq("id", post_id).execute()
            return res.data[0]
        except Exception:
            pass

    new_id = (max([c["id"] for c in LOCAL_COMMENTS], default=0)) + 1
    payload["id"] = new_id
    LOCAL_COMMENTS.append(payload)

    post = next((p for p in LOCAL_POSTS if p["id"] == post_id), None)
    if post:
        post["comments_count"] = post.get("comments_count", 0) + 1

    return payload

def delete_comment(comment_id: int) -> bool:
    if is_supabase_configured():
        try:
            supabase.table("comments").delete().eq("id", comment_id).execute()
            return True
        except Exception:
            pass

    global LOCAL_COMMENTS
    comment = next((c for c in LOCAL_COMMENTS if c["id"] == comment_id), None)
    if comment:
        post = next((p for p in LOCAL_POSTS if p["id"] == comment["post_id"]), None)
        if post:
            post["comments_count"] = max(0, post.get("comments_count", 1) - 1)
        LOCAL_COMMENTS = [c for c in LOCAL_COMMENTS if c["id"] != comment_id]
        return True
    return False

def get_profile(identifier: str) -> Optional[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            res = supabase.table("profiles").select("*").or_(f"id.eq.{identifier},username.eq.{identifier}").execute()
            if res.data and len(res.data) > 0:
                profile = res.data[0]
                # calculate stats
                posts_res = supabase.table("posts").select("id,likes_count").eq("author_id", profile["id"]).execute()
                user_posts = posts_res.data or []
                profile["posts_count"] = len(user_posts)
                profile["likes_received"] = sum(p.get("likes_count", 0) for p in user_posts)
                return profile
        except Exception:
            pass

    # Search local
    for profile in LOCAL_PROFILES.values():
        if profile["id"] == identifier or profile["username"] == identifier:
            result = dict(profile)
            user_posts = [p for p in LOCAL_POSTS if p.get("author_id") == profile["id"]]
            result["posts_count"] = len(user_posts)
            result["likes_received"] = sum(p.get("likes_count", 0) for p in user_posts)
            return result
    return None

def update_profile(profile_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {k: v for k, v in updates.items() if v is not None}
    
    if is_supabase_configured():
        try:
            res = supabase.table("profiles").update(cleaned).eq("id", profile_id).execute()
            if res.data:
                return get_profile(profile_id)
        except Exception:
            pass

    if profile_id in LOCAL_PROFILES:
        LOCAL_PROFILES[profile_id].update(cleaned)
        # Also update author_name and author_avatar on existing posts/comments for consistency
        new_name = cleaned.get("display_name")
        new_avatar = cleaned.get("avatar_url")
        for p in LOCAL_POSTS:
            if p.get("author_id") == profile_id:
                if new_name:
                    p["author_name"] = new_name
                if new_avatar is not None:
                    p["author_avatar"] = new_avatar
        for c in LOCAL_COMMENTS:
            if c.get("author_id") == profile_id:
                if new_name:
                    c["author_name"] = new_name
                if new_avatar is not None:
                    c["author_avatar"] = new_avatar

        return get_profile(profile_id)
    return {}

def get_all_profiles() -> List[Dict[str, Any]]:
    if is_supabase_configured():
        try:
            res = supabase.table("profiles").select("*").execute()
            if res.data:
                return [get_profile(p["id"]) for p in res.data]
        except Exception:
            pass

    return [get_profile(pid) for pid in LOCAL_PROFILES.keys()]

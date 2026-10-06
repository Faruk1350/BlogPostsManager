"""Prometheus metrics shared across the application.

HTTP metrics (requests, latency, in-progress) are provided by
prometheus-fastapi-instrumentator. This module owns the business metrics so
that the service layer can be instrumented from a single place.
"""

from prometheus_client import Counter, Gauge, Info

app_info = Info("blog_app_info", "Blog Posts Manager application info")

# Current number of blog posts (refreshed on read/write paths).
posts_gauge = Gauge("blog_posts_count", "Current number of blog posts")

# Lifecycle events, labelled by action.
post_events = Counter("blog_post_events_total", "Post lifecycle events", ["action"])
like_events = Counter("blog_like_events_total", "Like and unlike events", ["action"])
comment_events = Counter("blog_comment_events_total", "Comment lifecycle events", ["action"])

# Single-action counters.
share_events = Counter("blog_share_events_total", "Recorded post shares")
profile_events = Counter("blog_profile_update_events_total", "Profile updates")
upload_events = Counter("blog_upload_events_total", "Uploaded files")
preference_events = Counter("blog_preference_update_events_total", "Preference updates")

# Authentication events by action (signup, login, login_failed, logout, refresh).
auth_events = Counter("blog_auth_events_total", "Authentication events", ["action"])

# Instantiate labelled series at zero so dashboards show 0 instead of "No data"
# before the first event arrives.
for _action in ("created", "updated", "deleted"):
    post_events.labels(action=_action).inc(0)
    comment_events.labels(action=_action).inc(0)
for _action in ("like", "unlike"):
    like_events.labels(action=_action).inc(0)
for _action in ("signup", "signup_failed", "login", "login_failed", "logout", "refresh", "password_change"):
    auth_events.labels(action=_action).inc(0)

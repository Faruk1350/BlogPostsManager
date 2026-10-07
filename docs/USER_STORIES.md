# User Stories — Chronicle (Blog Posts Manager)

All three stories below are **implemented, deployed and verified** on
`blog.tavesglobal.com` (see the evidence section of each story for the tests,
endpoints and metrics that prove it).

- Product: Chronicle — a blog platform with JWT accounts, drafts, semantic
  search and personalised recommendations.
- Stack: FastAPI + Supabase Postgres (+ pgvector), React 19 UI, local ONNX
  embeddings, Prometheus/Grafana/Loki observability.
- Test suite: `test_app.py` — 15 self-cleaning integration tests
  (`make test` or run inside the deploy pipeline).

---

## US-1 — Accounts, sessions and personal settings

> **As a** reader or author,
> **I want** to create an account, sign in/out securely and manage my profile
> and preferences,
> **So that** my content, reactions and feed are personal to me and protected.

**Status:** ✅ Implemented and live

### Acceptance criteria

1. **Sign up** — Given a valid email and a password of 8+ characters, when I
   submit the sign-up form, then an account, profile and default preferences
   are created and I am signed in immediately.
2. **Validation** — Given a duplicate email, then signup returns `409`; given a
   malformed email or a password under 8 characters, then the request is
   rejected (`400`/`422`) with a readable message.
3. **First account is admin** — Given the platform has no accounts yet, when
   the first person signs up, then they become the admin and inherit the
   original demo author profile and its posts. Later accounts are normal users.
4. **Sign in** — Given correct credentials, then I receive an access token
   (30 min) and a refresh token (30 days); given a wrong password, then the
   response is `401` and a failed-login event is counted for monitoring.
5. **Session survives reload** — Given I return to the site later, then my
   session is restored from the stored refresh token; a stale access token is
   transparently refreshed once and the original request retried.
6. **Refresh rotation** — Given a valid refresh token, when it is used, then a
   new one is issued and the old one is revoked; replaying the old token fails
   with `401`.
7. **Sign out** — Given I am signed in, when I sign out, then my refresh token
   is revoked server-side and the session is cleared locally.
8. **Password change** — Given I know my current password, when I change it,
   then the old password stops working and the new one signs me in; a wrong
   current password returns `400`.
9. **Protection** — Given no token, then every mutating endpoint
   (posts, likes, comments, shares, upload, settings) returns `401`.
10. **Profile & preferences** — Given I am signed in, then I can update my
    display name, tagline, bio, avatar, location and website, and set theme
    (light/dark/system), notification toggles, favourite categories, default
    feed sort and digest frequency; theme applies immediately and persists.
11. **Privacy** — Given any API response, then password hashes and refresh
    token values are never returned.

### Tasks

- [x] Database: `users` (bcrypt hash, `is_admin`), `refresh_tokens`
  (SHA-256 hashed, revocable, expiring), `preferences` (theme, notifications,
  favourite categories, sort, digest); `profiles.user_id` link; RLS on.
- [x] `backend/security.py`: bcrypt hashing, JWT issue/decode,
  `get_current_user` / `get_optional_user` / `require_admin` dependencies,
  ownership guard (`assert_can_modify`).
- [x] `backend/routes/auth.py`: `POST /api/auth/signup|login|refresh|logout`,
  `GET /api/auth/me`, `PUT /api/auth/password`.
- [x] `backend/routes/profiles.py`: `GET/PUT /api/me`,
  `GET/PUT /api/me/preferences`; profile edits restricted to owner/admin.
- [x] Frontend: `lib/api.js` (token storage + automatic 401 refresh/retry),
  `lib/auth.jsx` (session restore, theme application), `AuthPage` (login +
  signup), `SettingsPage` (profile, preferences, password), navbar account
  menu with admin badge and sign-out.
- [x] Metrics + alerting: `blog_auth_events_total{action}` counter, Grafana
  "Failed logins" panel, `AppLoginFailureSpike` alert (>5 failures / 15 min).
- [x] Tests: `test_02_signup_login_refresh_logout`,
  `test_03_password_change`, `test_04_protected_endpoints_require_auth`,
  `test_09_me_and_preferences`, `test_10_profiles_are_public`.

### Evidence

- Endpoints: `/api/auth/*`, `/api/me*` (see `/docs` for the full schema).
- Tests: 5 named tests above, all green in `test_app.py`.
- Live: `https://blog.tavesglobal.com/signup` · `/login` · `/settings`.

---

## US-2 — Authoring: write, edit, draft, publish, delete

> **As an** author,
> **I want** to write and manage stories with cover images, save drafts and
> control what is public,
> **So that** I can publish polished content and keep unfinished work private.

**Status:** ✅ Implemented and live

### Acceptance criteria

1. **Write** — Given I am signed in, when I publish a story with a title,
   content and optional cover image/category, then it is created (`201`) with a
   unique slug, computed read time and zeroed counters, and appears in the
   public feed.
2. **Validation** — Given a missing title or empty content on publish, then the
   request is rejected with `400`.
3. **Drafts are private** — Given I save a story as a draft, then it does not
   appear in the public feed, is not reachable by ID for anyone else (`404`),
   and is listed for me under "My drafts" (`?status=draft`, auth required).
4. **Publish a draft** — Given a draft of mine, when I switch it to published,
   then it becomes visible to everyone.
5. **Edit** — Given a story I own, when I edit title/content/cover/category/
   status, then the change is stored, the read time and slug are recalculated
   and `updated_at` is bumped; a non-author editing my story gets `403`, and an
   admin can edit any story.
6. **Delete** — Given a story I own (or admin), when I delete it, then it and
   its likes/comments/shares disappear (cascade); a non-author gets `403`.
7. **Cover images** — Given a PNG/JPG/WEBP/GIF file, when I upload it, then I
   get a URL I can attach to a story; unsupported file types are rejected
   (`400`) and uploading without a session returns `401`.
8. **View counter** — Given a published story, when a reader opens it, then its
   view counter increases and is shown on the card and reader.
9. **Ownership UI** — Given I am the author, then edit/delete controls appear on
   my cards and in the reader; other users never see them.

### Tasks

- [x] Database: `posts.status` (`draft|published`), `slug` (unique backfilled),
  `views_count`, `updated_at`; `increment_post_views` RPC.
- [x] `backend/routes/items.py`: `POST /items|/api/posts` (auth, draft support),
  `PUT /api/posts/{id}`, `DELETE /api/posts/{id}`, `GET /api/posts/{id}`;
  draft visibility rules; pagination (`limit`/`offset`).
- [x] `backend/database.py`: slug generation/uniqueness, read-time computation,
  ownership-aware updates, cascade deletes.
- [x] `backend/routes/upload.py`: image uploads restricted to allowed
  extensions and authenticated users.
- [x] Frontend: write modal with edit mode, "Save as draft" and publish,
  cover-photo upload/presets/URL, draft badges and "My drafts" feed tab,
  edit/delete actions on cards and in the reader.
- [x] Tests: `test_05_post_lifecycle`, `test_06_drafts`, `test_07_ownership`,
  `test_11_upload_requires_auth_and_cleans_up`.

### Evidence

- Endpoints: `POST/PUT/DELETE /api/posts*`, `POST /api/upload` (see `/docs`).
- Tests: the four tests above, all green and self-cleaning.
- Live: write button in the navbar → editor with draft/publish.

---

## US-3 — Discovery and engagement: semantic search, recommendations, reactions

> **As a** reader,
> **I want** to find stories by meaning (not just keywords), get related and
> personalised suggestions, and react with likes, comments and shares,
> **So that** I discover relevant content and authors can see engagement.

**Status:** ✅ Implemented and live

### Acceptance criteria

1. **Semantic search** — Given the embedding model is available, when I search
   a phrase with **no keyword overlap** with the content (e.g. *"marine
   mammals in the ocean"*), then stories about that topic are returned.
2. **Keyword precision** — Given a query containing a rare/exact term, then
   stories containing it rank **first**, with semantic matches filling the
   remaining slots (hybrid ranking).
3. **Search UX** — Given I type in the search box, then the query is debounced
   (~300 ms), results update without a reload, and the result count is shown.
4. **Graceful degradation** — Given the embedding model cannot load (no
   network on first run, restricted environment), then search still works
   using ranked full-text search and recommendations fall back to
   category/author affinity — no errors surface to readers.
5. **Related stories** — Given I open a story, then a "Related stories" rail
   shows similar published stories (vector similarity, excluding itself) and
   clicking one opens it in the reader.
6. **Recommended feed** — Given I am signed in with at least one like or
   comment, then "For you" ranks stories by similarity to my taste; with no
   history (or signed out), it shows trending stories; my own posts are
   excluded.
7. **Likes** — Given I am signed in, when I like/unlike a story, then the
   state persists per user (one like per user/story) and the visible count
   updates; unauthenticated users are asked to sign in.
8. **Comments** — Given I am signed in, when I comment, then it appears
   immediately for everyone (`201`) and the count updates; comments are
   paginated in order; I can delete my own comments (admins can delete any)
   and the count decreases.
9. **Shares** — Given I share a story to any channel, then the share is
   recorded with its platform and the share count increases.
10. **Counts are truthful** — Given any interaction, then `likes_count`,
    `comments_count` and `shares_count` are derived from the interaction rows,
    so they can never drift.

### Tasks

- [x] Database: `pgvector` extension, `posts.embedding vector(384)` + HNSW
  index; `semantic_search` RPC; vector-based `related_posts` and
  `recommended_feed` (taste centroid, affinity fallback); `likes`/`shares`
  tables with unique user/post constraint; counters derived from rows.
- [x] `backend/embeddings.py`: local ONNX model (`fastembed`,
  bge-small, 384-d) with lazy loading, query/document embedding, cache-dir
  fallback and graceful degradation.
- [x] `backend/database.py`: hybrid search (keyword-first + semantic fill),
  related/recommended wrappers, embedding on create/update, startup warmup and
  backfill of missing vectors.
- [x] `backend/routes/items.py`: `GET /api/feed/recommended`,
  `GET /api/posts/{id}/related`, like/share/comment endpoints (auth),
  comment pagination.
- [x] Frontend: debounced search with "Semantic matches" summary, "For you"
  feed tab, related-stories rail in the reader, sign-in prompts for reactions,
  live count updates.
- [x] Metrics: `blog_embedding_status`, `blog_embedding_events_total`;
  search/recommendation endpoints instrumented automatically.
- [x] Tests: `test_08_search_and_recommendations`,
  `test_12_embeddings_are_populated`,
  `test_13_semantic_search_matches_meaning`, plus like/comment/share coverage
  inside `test_05_post_lifecycle`.

### Evidence

- Live check: search *"how do I make my API faster"* returns the FastAPI,
  Postgres-index and Supabase posts (no keyword overlap); searching
  *"postgres indexes"* ranks that story first.
- Related rail for the Supabase story returns the index/FastAPI/ops stories.
- 7/7 posts embedded in production (`select count(embedding) from posts`).
- Tests: three named tests above + interaction coverage, all green.

---

## Cross-story requirements (apply to all three)

- **Security:** every mutating action is authenticated and ownership-checked;
  admins can moderate any content.
- **Observability:** request rate/latency/errors per endpoint, business
  counters (posts, likes, comments, shares, uploads, auth, embeddings) and
  structured logs flow to Grafana/Loki; alerts cover downtime, error rate,
  latency, memory, host resources, containers, tunnel and failed logins.
- **Deployment:** `./deploy.sh` (or `make deploy`) builds, runs all 15 tests,
  deploys, health-checks and rolls back automatically on failure; commit hooks
  auto-deploy via launchd.
- **Quality gate:** no story is "done" unless its tests pass in the pipeline
  and the feature is verifiable on the live URL.

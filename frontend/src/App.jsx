import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpDown, BookOpen, Compass, FileText, PenSquare, Sparkles } from "lucide-react";

import Navbar from "./components/Navbar";
import PostCard from "./components/PostCard";
import PostModal from "./components/PostModal";
import CreatePostModal from "./components/CreatePostModal";
import ShareModal from "./components/ShareModal";
import ProfileModal from "./components/ProfileModal";
import AuthPage from "./components/AuthPage";
import SettingsPage from "./components/SettingsPage";
import Toast from "./components/Toast";
import { api } from "./lib/api";
import { useAuth } from "./lib/auth";
import "./App.css";

const CATEGORIES = ["All", "Technology", "Design", "Engineering", "Database", "Lifestyle"];
const VALID_VIEWS = ["home", "login", "signup", "settings"];

function viewFromPath(pathname) {
  const clean = pathname.replace(/^\/+|\/+$/g, "");
  return VALID_VIEWS.includes(clean) ? clean : "home";
}

export default function App() {
  const { ready, profile, preferences, isAuthenticated, logout } = useAuth();

  const [view, setView] = useState(() => viewFromPath(window.location.pathname));
  const [tab, setTab] = useState("latest"); // 'latest' | 'foryou' | 'drafts'
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [sortOption, setSortOption] = useState("recent");
  const [dbStatus, setDbStatus] = useState({ connected: false, database: "local" });

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingPost, setEditingPost] = useState(null);
  const [readerPost, setReaderPost] = useState(null);
  const [sharePost, setSharePost] = useState(null);
  const [profileModalId, setProfileModalId] = useState(null);

  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((toast) => toast.id !== id)), 3200);
  }, []);

  // ---------------- navigation ----------------
  const navigate = useCallback((next) => {
    setView(next);
    window.history.pushState({}, "", next === "home" ? "/" : `/${next}`);
    window.scrollTo({ top: 0 });
  }, []);

  useEffect(() => {
    const onPop = () => setView(viewFromPath(window.location.pathname));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const requireAuth = useCallback(() => {
    showToast("Please sign in to continue.");
    navigate("login");
  }, [navigate, showToast]);

  const handleError = useCallback(
    (err) => {
      if (err?.status === 401) {
        requireAuth();
      } else {
        showToast(err?.detail || "Something went wrong.");
      }
    },
    [requireAuth, showToast]
  );

  // ---------------- initial data ----------------
  useEffect(() => {
    api("/api/health")
      .then((data) => setDbStatus({ connected: data.supabase_connected, database: data.database }))
      .catch(() => {});
  }, []);

  // Apply the user's preferred default sort once preferences load.
  useEffect(() => {
    if (preferences?.default_sort) setSortOption(preferences.default_sort);
  }, [preferences?.default_sort]);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // ---------------- posts ----------------
  const fetchPosts = useCallback(async () => {
    setLoading(true);
    try {
      let data;
      if (tab === "foryou") {
        data = await api("/api/feed/recommended?limit=24");
      } else if (tab === "drafts") {
        data = await api("/api/posts?status=draft&limit=50");
      } else {
        const params = new URLSearchParams();
        if (debouncedSearch.trim()) params.append("q", debouncedSearch.trim());
        if (selectedCategory !== "All") params.append("category", selectedCategory);
        params.append("sort", sortOption);
        params.append("limit", "24");
        data = await api(`/api/posts?${params.toString()}`);
      }
      setPosts(data || []);
    } catch (err) {
      if (err?.status === 401 && tab === "drafts") {
        setTab("latest");
      } else {
        handleError(err);
      }
    } finally {
      setLoading(false);
    }
  }, [tab, debouncedSearch, selectedCategory, sortOption, handleError]);

  useEffect(() => {
    if (!ready) return;
    fetchPosts();
  }, [ready, fetchPosts]);

  // Deep link: ?post=ID opens the reader once posts are loaded.
  useEffect(() => {
    const urlPostId = new URLSearchParams(window.location.search).get("post");
    if (!urlPostId || posts.length === 0) return;
    const found = posts.find((post) => String(post.id) === String(urlPostId));
    if (found) setReaderPost(found);
  }, [posts]);

  // ---------------- actions ----------------
  const handleToggleLike = async (postId) => {
    if (!isAuthenticated) return requireAuth();
    try {
      const data = await api(`/api/posts/${postId}/like`, { method: "POST", body: {} });
      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId ? { ...post, is_liked: data.liked, likes_count: data.likes_count } : post
        )
      );
      setReaderPost((prev) =>
        prev && prev.id === postId ? { ...prev, is_liked: data.liked, likes_count: data.likes_count } : prev
      );
      if (data.liked) showToast("Liked story!");
    } catch (err) {
      handleError(err);
    }
  };

  const handleDeletePost = async (postId) => {
    if (!isAuthenticated) return requireAuth();
    if (!window.confirm("Delete this story? This cannot be undone.")) return;

    try {
      await api(`/api/posts/${postId}`, { method: "DELETE" });
      setPosts((prev) => prev.filter((post) => post.id !== postId));
      setReaderPost((prev) => (prev && prev.id === postId ? null : prev));
      showToast("Story deleted.");
    } catch (err) {
      handleError(err);
    }
  };

  const handleOpenCreate = () => {
    if (!isAuthenticated) return requireAuth();
    setEditingPost(null);
    setCreateModalOpen(true);
  };

  const handleOpenEdit = (post) => {
    setReaderPost(null);
    setEditingPost(post);
    setCreateModalOpen(true);
  };

  const handlePostSaved = () => {
    setEditingPost(null);
    fetchPosts();
  };

  const handleSignOut = async () => {
    await logout();
    setPosts([]);
    showToast("Signed out.");
    navigate("home");
  };

  const handleAuthSuccess = () => {
    showToast("Welcome to Chronicle!");
    navigate("home");
  };

  const readerForId = useCallback(
    (id) => {
      const found = posts.find((post) => post.id === id);
      if (found) setReaderPost(found);
    },
    [posts]
  );

  const tabs = useMemo(
    () => [
      { id: "latest", label: "Latest", icon: BookOpen },
      { id: "foryou", label: "For you", icon: Sparkles },
      ...(isAuthenticated ? [{ id: "drafts", label: "My drafts", icon: FileText }] : []),
    ],
    [isAuthenticated]
  );

  // ---------------- views ----------------
  if (view === "login" || view === "signup") {
    return (
      <AuthPage
        mode={view}
        onModeChange={(next) => navigate(next)}
        onSuccess={handleAuthSuccess}
        onBack={() => navigate("home")}
      />
    );
  }

  if (view === "settings") {
    if (!isAuthenticated) {
      return (
        <AuthPage mode="login" onModeChange={(next) => navigate(next)} onSuccess={handleAuthSuccess} onBack={() => navigate("home")} />
      );
    }
    return <SettingsPage onBack={() => navigate("home")} showToast={showToast} />;
  }

  return (
    <div className="app-container">
      <Navbar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        onOpenCreate={handleOpenCreate}
        onOpenProfile={(id) => setProfileModalId(id || profile?.id)}
        onOpenSettings={() => navigate("settings")}
        onSignIn={() => navigate("login")}
        onLogout={handleSignOut}
        dbStatus={dbStatus}
      />

      <main className="main-content">
        <section className="hero-section">
          <h1 className="hero-title">Words that shape the future.</h1>
          <p className="hero-subtitle">
            Explore insightful engineering stories, design philosophies, modern architectures, and ideas
            from passionate creators.
          </p>
        </section>

        {/* Feed tabs */}
        <div className="feed-tabs">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`feed-tab ${tab === id ? "active" : ""}`}
              onClick={() => setTab(id)}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>

        {tab !== "foryou" && (
          <div className="filters-bar">
            <div className="category-pills">
              {CATEGORIES.map((category) => (
                <button
                  key={category}
                  className={`cat-pill ${selectedCategory === category ? "active" : ""}`}
                  onClick={() => setSelectedCategory(category)}
                >
                  {category === "All" ? "All stories" : category}
                </button>
              ))}
            </div>

            <div className="sort-container">
              <ArrowUpDown size={14} />
              <span>Sort:</span>
              <select
                className="sort-select"
                value={sortOption}
                onChange={(event) => setSortOption(event.target.value)}
              >
                <option value="recent">Latest first</option>
                <option value="likes">Most popular</option>
              </select>
            </div>
          </div>
        )}

        {debouncedSearch && tab === "latest" && (
          <div className="search-summary">
            <Compass size={15} /> Semantic matches for “{debouncedSearch}” — {posts.length} found
          </div>
        )}

        {loading ? (
          <div className="empty-state">
            <div className="empty-title">Loading stories...</div>
            <div className="empty-text">Fetching publications from the database.</div>
          </div>
        ) : posts.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <BookOpen size={24} />
            </div>
            <div className="empty-title">
              {tab === "drafts" ? "No drafts yet" : "No stories found"}
            </div>
            <div className="empty-text">
              {tab === "drafts"
                ? "Stories you save as drafts will appear here."
                : debouncedSearch
                ? `No stories matched “${debouncedSearch}”. Try another keyword or category.`
                : "No stories have been published in this category yet."}
            </div>
            {isAuthenticated && (
              <button className="btn-primary" style={{ marginTop: "0.5rem" }} onClick={handleOpenCreate}>
                <PenSquare size={16} />
                <span>Write a story</span>
              </button>
            )}
          </div>
        ) : (
          <div className="blog-grid">
            {posts.map((post) => (
              <PostCard
                key={post.id}
                post={post}
                onLike={handleToggleLike}
                onOpenReader={(p) => setReaderPost(p)}
                onOpenShare={(p) => (isAuthenticated ? setSharePost(p) : requireAuth())}
                onOpenProfile={(id) => setProfileModalId(id)}
                onDeletePost={handleDeletePost}
                onEditPost={handleOpenEdit}
                currentUser={profile}
              />
            ))}
          </div>
        )}
      </main>

      <PostModal
        post={readerPost}
        isOpen={Boolean(readerPost)}
        onClose={() => setReaderPost(null)}
        onLike={handleToggleLike}
        onOpenShare={(p) => (isAuthenticated ? setSharePost(p) : requireAuth())}
        onOpenProfile={(id) => {
          setReaderPost(null);
          setProfileModalId(id);
        }}
        onEditPost={handleOpenEdit}
        onDeletePost={handleDeletePost}
        onOpenReader={(p) => setReaderPost(p)}
        onRequireAuth={requireAuth}
        showToast={showToast}
      />

      <CreatePostModal
        isOpen={createModalOpen}
        onClose={() => {
          setCreateModalOpen(false);
          setEditingPost(null);
        }}
        onPostCreated={handlePostSaved}
        onPostSaved={handlePostSaved}
        editingPost={editingPost}
        showToast={showToast}
      />

      <ShareModal
        post={sharePost}
        isOpen={Boolean(sharePost)}
        onClose={() => setSharePost(null)}
        showToast={showToast}
      />

      <ProfileModal
        profileId={profileModalId}
        isOpen={Boolean(profileModalId)}
        onClose={() => setProfileModalId(null)}
        onOpenReader={(post) => {
          setProfileModalId(null);
          setReaderPost(post);
        }}
        showToast={showToast}
      />

      <Toast toasts={toasts} />
    </div>
  );
}

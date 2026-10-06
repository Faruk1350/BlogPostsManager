import React, { useState, useEffect, useCallback } from "react";
import Navbar from "./components/Navbar";
import PostCard from "./components/PostCard";
import PostModal from "./components/PostModal";
import CreatePostModal from "./components/CreatePostModal";
import ShareModal from "./components/ShareModal";
import ProfileModal from "./components/ProfileModal";
import Toast from "./components/Toast";
import { Sparkles, ArrowUpDown, BookOpen, PenSquare } from "lucide-react";
import "./App.css";

const CATEGORIES = [
  "All",
  "Technology",
  "Design",
  "Engineering",
  "Database",
  "Lifestyle"
];

export default function App() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");
  const [sortOption, setSortOption] = useState("recent"); // 'recent' | 'likes'

  // Profiles & Database status
  const [currentUser, setCurrentUser] = useState(null);
  const [allProfiles, setAllProfiles] = useState([]);
  const [dbStatus, setDbStatus] = useState({ connected: false, database: "local" });

  // Modals & Overlays
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [readerPost, setReaderPost] = useState(null);
  const [sharePost, setSharePost] = useState(null);
  const [profileModalId, setProfileModalId] = useState(null);

  // Toasts
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  // 1. Initial Load: Check DB status & profiles
  useEffect(() => {
    const initApp = async () => {
      try {
        // Health check
        const healthRes = await fetch("/api/health");
        if (healthRes.ok) {
          const healthData = await healthRes.json();
          setDbStatus({
            connected: healthData.supabase_connected || false,
            database: healthData.database || "local"
          });
        }

        // Fetch profiles
        const profilesRes = await fetch("/api/profiles");
        if (profilesRes.ok) {
          const profilesData = await profilesRes.json();
          setAllProfiles(profilesData);
          if (profilesData.length > 0) {
            setCurrentUser(profilesData[0]); // default to first profile (Faruk)
          }
        }
      } catch (err) {
        console.error("Initialization error:", err);
      }
    };

    initApp();
  }, []);

  // 2. Fetch posts whenever filter/sort/search/current user changes
  const fetchPosts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm.trim()) params.append("search", searchTerm.trim());
      if (selectedCategory !== "All") params.append("category", selectedCategory);
      params.append("sort", sortOption);
      if (currentUser?.id) params.append("current_user_id", currentUser.id);

      const res = await fetch(`/api/posts?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setPosts(data);

        // Check if query param ?post=ID exists to auto-open reader
        const urlParams = new URLSearchParams(window.location.search);
        const urlPostId = urlParams.get("post");
        if (urlPostId) {
          const found = data.find((p) => String(p.id) === String(urlPostId));
          if (found) setReaderPost(found);
        }
      }
    } catch (err) {
      console.error("Failed to fetch posts:", err);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, selectedCategory, sortOption, currentUser]);

  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  // 3. Actions
  const handleToggleLike = async (postId) => {
    if (!currentUser) return;

    try {
      const res = await fetch(`/api/posts/${postId}/like`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentUser.id })
      });

      if (res.ok) {
        const data = await res.json();
        setPosts((prev) =>
          prev.map((p) =>
            p.id === postId
              ? { ...p, is_liked: data.liked, likes_count: data.likes_count }
              : p
          )
        );

        if (readerPost && readerPost.id === postId) {
          setReaderPost((prev) => ({
            ...prev,
            is_liked: data.liked,
            likes_count: data.likes_count
          }));
        }

        if (data.liked) {
          showToast("Liked story!");
        }
      }
    } catch (err) {
      console.error("Failed to like post", err);
    }
  };

  const handleDeletePost = async (postId) => {
    if (!window.confirm("Are you sure you want to delete this story?")) return;

    try {
      const res = await fetch(`/api/posts/${postId}`, { method: "DELETE" });
      if (res.ok) {
        setPosts((prev) => prev.filter((p) => p.id !== postId));
        if (readerPost && readerPost.id === postId) {
          setReaderPost(null);
        }
        showToast("Story deleted successfully.");
      }
    } catch (err) {
      console.error("Failed to delete post", err);
    }
  };

  const handlePostCreated = (newPost) => {
    setPosts((prev) => [newPost, ...prev]);
  };

  const handleSwitchProfile = (profileId) => {
    const found = allProfiles.find((p) => p.id === profileId);
    if (found) {
      setCurrentUser(found);
      showToast(`Switched active profile to ${found.display_name}`);
    }
  };

  const handleProfileUpdated = (updated) => {
    setCurrentUser(updated);
    setAllProfiles((prev) =>
      prev.map((p) => (p.id === updated.id ? updated : p))
    );
    fetchPosts();
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <Navbar
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        onOpenCreate={() => setCreateModalOpen(true)}
        onOpenProfile={() => setProfileModalId(currentUser?.id || "user_admin")}
        currentUser={currentUser}
        dbStatus={dbStatus}
      />

      {/* Main Content Area */}
      <main className="main-content">
        {/* Hero Section */}
        <section className="hero-section">
          <h1 className="hero-title">Words that shape the future.</h1>
          <p className="hero-subtitle">
            Explore insightful engineering stories, design philosophies, modern architectures, and ideas from passionate creators.
          </p>
        </section>

        {/* Filters and Sorting Bar */}
        <div className="filters-bar">
          {/* Category Pills */}
          <div className="category-pills">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                className={`cat-pill ${selectedCategory === cat ? "active" : ""}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat === "All" ? "All Stories" : cat}
              </button>
            ))}
          </div>

          {/* Sort Selector */}
          <div className="sort-container">
            <ArrowUpDown size={14} />
            <span>Sort:</span>
            <select
              className="sort-select"
              value={sortOption}
              onChange={(e) => setSortOption(e.target.value)}
            >
              <option value="recent">Latest First</option>
              <option value="likes">Most Popular</option>
            </select>
          </div>
        </div>

        {/* Blog Post Grid */}
        {loading ? (
          <div className="empty-state">
            <div className="empty-title">Loading stories...</div>
            <div className="empty-text">Fetching latest publications from the database.</div>
          </div>
        ) : posts.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <BookOpen size={24} />
            </div>
            <div className="empty-title">No stories found</div>
            <div className="empty-text">
              {searchTerm
                ? `No stories matched your search "${searchTerm}". Try another keyword or category.`
                : "No stories have been published in this category yet. Be the first to share your thoughts!"}
            </div>
            <button
              className="btn-primary"
              style={{ marginTop: "0.5rem" }}
              onClick={() => setCreateModalOpen(true)}
            >
              <PenSquare size={16} />
              <span>Write First Story</span>
            </button>
          </div>
        ) : (
          <div className="blog-grid">
            {posts.map((post) => (
              <PostCard
                key={post.id}
                post={post}
                onLike={handleToggleLike}
                onOpenReader={(p) => setReaderPost(p)}
                onOpenShare={(p) => setSharePost(p)}
                onOpenProfile={(id) => setProfileModalId(id)}
                onDeletePost={handleDeletePost}
                currentUser={currentUser}
              />
            ))}
          </div>
        )}
      </main>

      {/* Reader Modal (Comments + Photos + Full Text) */}
      <PostModal
        post={readerPost}
        isOpen={Boolean(readerPost)}
        onClose={() => setReaderPost(null)}
        onLike={handleToggleLike}
        onOpenShare={(p) => setSharePost(p)}
        onOpenProfile={(id) => setProfileModalId(id)}
        currentUser={currentUser}
        showToast={showToast}
      />

      {/* Write Story Modal (Photo Upload / URL / Presets) */}
      <CreatePostModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onPostCreated={handlePostCreated}
        currentUser={currentUser}
        showToast={showToast}
      />

      {/* Share Modal (Copy link + Social) */}
      <ShareModal
        post={sharePost}
        isOpen={Boolean(sharePost)}
        onClose={() => setSharePost(null)}
        showToast={showToast}
        currentUser={currentUser}
      />

      {/* Profile Modal (View, Switch, Edit Bio/Avatar) */}
      <ProfileModal
        profileId={profileModalId}
        isOpen={Boolean(profileModalId)}
        onClose={() => setProfileModalId(null)}
        allProfiles={allProfiles}
        onSwitchProfile={handleSwitchProfile}
        onOpenReader={(p) => setReaderPost(p)}
        currentUser={currentUser}
        showToast={showToast}
        onProfileUpdated={handleProfileUpdated}
      />

      {/* Toast Notifications */}
      <Toast toasts={toasts} />
    </div>
  );
}
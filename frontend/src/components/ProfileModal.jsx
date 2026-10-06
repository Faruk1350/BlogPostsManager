import React, { useState, useEffect } from "react";
import {
  X,
  MapPin,
  Globe,
  Calendar,
  Edit3,
  Heart,
  BookOpen,
  Check,
  UserCheck
} from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

const AVATAR_PRESETS = [
  "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
  "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=200&auto=format&fit=crop&q=80",
  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&auto=format&fit=crop&q=80"
];

export default function ProfileModal({
  profileId,
  isOpen,
  onClose,
  onOpenReader,
  showToast,
}) {
  const { profile: myProfile, reload } = useAuth();
  const [profile, setProfile] = useState(null);
  const [activeTab, setActiveTab] = useState("posts"); // 'posts' | 'likes'
  const [userPosts, setUserPosts] = useState([]);
  const [likedPosts, setLikedPosts] = useState([]);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  // Edit fields
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [website, setWebsite] = useState("");
  const [location, setLocation] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen && profileId) {
      loadProfileData(profileId);
    }
  }, [isOpen, profileId]);

  if (!isOpen) return null;

  const canEdit = Boolean(myProfile && profile && myProfile.id === profile.id);

  const loadProfileData = async (id) => {
    setLoading(true);
    setIsEditing(false);
    try {
      const [pData, postsData, likesData] = await Promise.all([
        api(`/api/profiles/${id}`),
        api(`/api/profiles/${id}/posts`).catch(() => []),
        api(`/api/profiles/${id}/likes`).catch(() => []),
      ]);

      setProfile(pData);
      setDisplayName(pData.display_name || "");
      setBio(pData.bio || "");
      setAvatarUrl(pData.avatar_url || "");
      setWebsite(pData.website || "");
      setLocation(pData.location || "");
      setUserPosts(postsData || []);
      setLikedPosts(likesData || []);
    } catch (err) {
      console.error("Failed to load profile", err);
      showToast?.(err.detail || "Could not load profile.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async (event) => {
    event.preventDefault();
    if (!profile) return;

    setSaving(true);
    try {
      const updated = await api(`/api/profiles/${profile.id}`, {
        method: "PUT",
        body: {
          display_name: displayName.trim(),
          bio: bio.trim(),
          avatar_url: avatarUrl.trim(),
          website: website.trim(),
          location: location.trim(),
        },
      });
      setProfile(updated);
      setIsEditing(false);
      showToast?.("Profile updated.");
      if (myProfile?.id === updated.id) await reload();
    } catch (err) {
      showToast?.(err.detail || "Could not update profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content large"
        onClick={(e) => e.stopPropagation()}
        style={{ padding: 0 }}
      >
        {/* Close Button Floating */}
        <div
          style={{
            position: "absolute",
            top: "1rem",
            right: "1rem",
            zIndex: 10
          }}
        >
          <button
            className="close-btn"
            style={{ backgroundColor: "rgba(255, 255, 255, 0.9)" }}
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        {/* Cover Photo */}
        <img
          src={
            profile?.cover_image_url ||
            "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1200&auto=format&fit=crop&q=80"
          }
          alt="Cover"
          className="profile-cover"
        />

        {/* Profile Content */}
        <div className="profile-header-content">
          <div className="profile-names-row">
            <img
              src={
                profile?.avatar_url ||
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200"
              }
              alt={profile?.display_name || "User"}
              className="profile-avatar-big"
            />

            {/* Actions: Edit (owners only) */}
            {canEdit && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button
                  className="btn-secondary"
                  style={{ padding: "0.4rem 0.85rem", fontSize: "0.8rem" }}
                  onClick={() => setIsEditing(!isEditing)}
                >
                  <Edit3 size={13} style={{ marginRight: "4px" }} />
                  <span>{isEditing ? "Cancel" : "Edit Profile"}</span>
                </button>
              </div>
            )}
          </div>

          {/* Edit Form OR View Header */}
          {isEditing ? (
            <form onSubmit={handleSaveProfile} style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "1rem" }}>
              <div className="form-group">
                <label className="form-label">Display Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Bio</label>
                <textarea
                  className="form-textarea"
                  style={{ minHeight: "80px" }}
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                <div className="form-group">
                  <label className="form-label">Location</label>
                  <input
                    type="text"
                    className="form-input"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. San Francisco, CA"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Website</label>
                  <input
                    type="url"
                    className="form-input"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
                    placeholder="https://..."
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Avatar Photo URL</label>
                <input
                  type="url"
                  className="form-input"
                  value={avatarUrl}
                  onChange={(e) => setAvatarUrl(e.target.value)}
                />
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                  {AVATAR_PRESETS.map((url, i) => (
                    <img
                      key={i}
                      src={url}
                      alt="Preset"
                      style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "50%",
                        cursor: "pointer",
                        border: avatarUrl === url ? "2px solid var(--accent-primary)" : "1px solid var(--border-subtle)"
                      }}
                      onClick={() => setAvatarUrl(url)}
                    />
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem", marginTop: "0.5rem" }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsEditing(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          ) : (
            <>
              <div>
                <h2 className="profile-fullname">{profile?.display_name}</h2>
                <div className="profile-handle">@{profile?.username}</div>
              </div>

              {profile?.bio && <p className="profile-bio">{profile.bio}</p>}

              {/* Meta details */}
              <div className="profile-meta-list">
                {profile?.location && (
                  <span className="profile-meta-item">
                    <MapPin size={14} />
                    <span>{profile.location}</span>
                  </span>
                )}
                {profile?.website && (
                  <a
                    href={profile.website}
                    target="_blank"
                    rel="noreferrer"
                    className="profile-meta-item"
                    style={{ color: "var(--accent-primary)" }}
                  >
                    <Globe size={14} />
                    <span>{profile.website.replace(/^https?:\/\//, "")}</span>
                  </a>
                )}
                <span className="profile-meta-item">
                  <Calendar size={14} />
                  <span>Joined 2026</span>
                </span>
              </div>

              {/* Stats Grid */}
              <div className="profile-stats-grid">
                <div>
                  <div className="stat-number">{profile?.posts_count ?? userPosts.length}</div>
                  <div className="stat-label">Stories</div>
                </div>
                <div>
                  <div className="stat-number">{profile?.likes_received ?? 0}</div>
                  <div className="stat-label">Likes Received</div>
                </div>
                <div>
                  <div className="stat-number">{likedPosts.length}</div>
                  <div className="stat-label">Liked Stories</div>
                </div>
              </div>
            </>
          )}

          {/* Tabs */}
          {!isEditing && (
            <div>
              <div style={{ display: "flex", gap: "0.75rem", borderBottom: "1px solid var(--border-subtle)", margin: "0.5rem 0 1rem" }}>
                <button
                  className={`cat-pill ${activeTab === "posts" ? "active" : ""}`}
                  onClick={() => setActiveTab("posts")}
                >
                  <BookOpen size={14} style={{ display: "inline", marginRight: "4px" }} />
                  Stories ({userPosts.length})
                </button>
                <button
                  className={`cat-pill ${activeTab === "likes" ? "active" : ""}`}
                  onClick={() => setActiveTab("likes")}
                >
                  <Heart size={14} style={{ display: "inline", marginRight: "4px" }} />
                  Liked ({likedPosts.length})
                </button>
              </div>

              {/* Tab Content */}
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {activeTab === "posts" ? (
                  userPosts.length === 0 ? (
                    <div style={{ color: "var(--text-muted)", padding: "1.5rem 0", textAlign: "center" }}>
                      No stories published yet.
                    </div>
                  ) : (
                    userPosts.map((p) => (
                      <div
                        key={p.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "0.85rem 1rem",
                          backgroundColor: "#ffffff",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "var(--radius-md)",
                          cursor: "pointer"
                        }}
                        onClick={() => {
                          onClose();
                          onOpenReader(p);
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{p.title}</div>
                          <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                            {p.category} · {p.read_time} · {p.likes_count} likes
                          </div>
                        </div>
                      </div>
                    ))
                  )
                ) : likedPosts.length === 0 ? (
                  <div style={{ color: "var(--text-muted)", padding: "1.5rem 0", textAlign: "center" }}>
                    No liked stories yet.
                  </div>
                ) : (
                  likedPosts.map((p) => (
                    <div
                      key={p.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "0.85rem 1rem",
                        backgroundColor: "#ffffff",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-md)",
                        cursor: "pointer"
                      }}
                      onClick={() => {
                        onClose();
                        onOpenReader(p);
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>{p.title}</div>
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                          By {p.author_name} · {p.category} · {p.likes_count} likes
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

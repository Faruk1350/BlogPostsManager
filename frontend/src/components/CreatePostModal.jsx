import React, { useState, useRef } from "react";
import { X, Image as ImageIcon, Upload, Sparkles, AlertCircle } from "lucide-react";

const PHOTO_PRESETS = [
  {
    name: "Minimalist Workspace",
    url: "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&auto=format&fit=crop&q=80"
  },
  {
    name: "Modern Engineering",
    url: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80"
  },
  {
    name: "Cloud Architecture",
    url: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&auto=format&fit=crop&q=80"
  },
  {
    name: "Creative Aesthetics",
    url: "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?w=1200&auto=format&fit=crop&q=80"
  }
];

const CATEGORIES = [
  "Technology",
  "Design",
  "Engineering",
  "Database",
  "Lifestyle",
  "General"
];

export default function CreatePostModal({
  isOpen,
  onClose,
  onPostCreated,
  currentUser,
  showToast
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("Engineering");
  const [coverImage, setCoverImage] = useState("");
  const [imageUrlInput, setImageUrlInput] = useState("");
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData
      });

      if (!res.ok) {
        throw new Error("Failed to upload image.");
      }

      const data = await res.json();
      setCoverImage(data.url);
      showToast("Cover photo uploaded successfully!");
    } catch (err) {
      console.error(err);
      setError("Failed to upload photo. You can paste an image URL instead.");
    } finally {
      setUploading(false);
    }
  };

  const handleApplyUrl = () => {
    if (imageUrlInput.trim()) {
      setCoverImage(imageUrlInput.trim());
      setImageUrlInput("");
      showToast("Image applied!");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !content.trim()) {
      setError("Please provide both a title and story content.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        cover_image: coverImage || PHOTO_PRESETS[0].url,
        category: category,
        author_id: currentUser?.id || "user_admin",
        author_name: currentUser?.display_name || "Faruk Developer",
        author_avatar: currentUser?.avatar_url || ""
      };

      const res = await fetch("/api/posts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error("Failed to publish story.");
      }

      const created = await res.json();
      onPostCreated(created);
      showToast("Story published successfully!");
      onClose();
      // Reset form
      setTitle("");
      setContent("");
      setCoverImage("");
    } catch (err) {
      console.error(err);
      setError("Failed to publish post. Please check backend connection.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2 className="modal-title">Write a New Story</h2>
          <button className="close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  color: "#e11d48",
                  backgroundColor: "#fff1f2",
                  padding: "0.75rem 1rem",
                  borderRadius: "var(--radius-md)",
                  fontSize: "0.875rem"
                }}
              >
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {/* Title */}
            <div className="form-group">
              <label className="form-label">Story Title</label>
              <input
                type="text"
                className="form-input"
                placeholder="Give your story a clear, compelling title..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                autoFocus
                required
              />
            </div>

            {/* Category */}
            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            {/* Cover Photo */}
            <div className="form-group">
              <label className="form-label">Cover Photo</label>

              {coverImage ? (
                <div className="preview-image-wrap">
                  <img
                    src={coverImage}
                    alt="Preview"
                    className="preview-image"
                  />
                  <button
                    type="button"
                    className="remove-photo-btn"
                    onClick={() => setCoverImage("")}
                    title="Remove photo"
                  >
                    <X size={16} />
                  </button>
                </div>
              ) : (
                <div>
                  <div
                    className="photo-upload-box"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload
                      size={28}
                      color="var(--accent-primary)"
                      style={{ margin: "0 auto 0.5rem" }}
                    />
                    <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                      {uploading ? "Uploading image..." : "Upload cover photo"}
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      PNG, JPG, WEBP or GIF
                    </div>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileUpload}
                      accept="image/*"
                      style={{ display: "none" }}
                    />
                  </div>

                  {/* Or Enter URL */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.5rem",
                      marginTop: "0.75rem"
                    }}
                  >
                    <input
                      type="url"
                      className="form-input"
                      placeholder="Or paste an image URL..."
                      value={imageUrlInput}
                      onChange={(e) => setImageUrlInput(e.target.value)}
                    />
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={handleApplyUrl}
                    >
                      Use URL
                    </button>
                  </div>

                  {/* Presets */}
                  <div style={{ marginTop: "0.75rem" }}>
                    <div
                      style={{
                        fontSize: "0.78rem",
                        color: "var(--text-muted)",
                        marginBottom: "0.4rem"
                      }}
                    >
                      Quick Presets:
                    </div>
                    <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                      {PHOTO_PRESETS.map((p) => (
                        <button
                          key={p.name}
                          type="button"
                          className="cat-pill"
                          style={{
                            fontSize: "0.75rem",
                            padding: "0.25rem 0.65rem",
                            backgroundColor: "var(--bg-subtle)"
                          }}
                          onClick={() => setCoverImage(p.url)}
                        >
                          <Sparkles size={11} style={{ marginRight: "3px" }} />
                          {p.name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Story Content */}
            <div className="form-group">
              <label className="form-label">
                Content{" "}
                <span style={{ fontWeight: 400, color: "var(--text-muted)" }}>
                  ({content.split(/\s+/).filter(Boolean).length} words)
                </span>
              </label>
              <textarea
                className="form-textarea"
                placeholder="Write your story here... Share insights, stories, technical tutorials, or ideas."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={8}
                required
              />
            </div>
          </div>

          {/* Footer */}
          <div className="modal-footer">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={submitting || !title.trim() || !content.trim()}
            >
              {submitting ? "Publishing..." : "Publish Story"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

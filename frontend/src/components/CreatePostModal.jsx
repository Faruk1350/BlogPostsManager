import React, { useEffect, useRef, useState } from "react";
import { X, Upload, Sparkles, AlertCircle, FileText } from "lucide-react";

import { api } from "../lib/api";

const PHOTO_PRESETS = [
  {
    name: "Minimalist Workspace",
    url: "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&auto=format&fit=crop&q=80",
  },
  {
    name: "Modern Engineering",
    url: "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&auto=format&fit=crop&q=80",
  },
  {
    name: "Cloud Architecture",
    url: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1200&auto=format&fit=crop&q=80",
  },
  {
    name: "Creative Aesthetics",
    url: "https://images.unsplash.com/photo-1507238691740-187a5b1d37b8?w=1200&auto=format&fit=crop&q=80",
  },
];

const CATEGORIES = ["Technology", "Design", "Engineering", "Database", "Lifestyle", "General"];

export default function CreatePostModal({
  isOpen,
  onClose,
  onPostCreated,
  onPostSaved,
  editingPost,
  showToast,
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
  const isEditing = Boolean(editingPost);

  useEffect(() => {
    if (!isOpen) return;
    if (editingPost) {
      setTitle(editingPost.title || "");
      setContent(editingPost.content || "");
      setCategory(editingPost.category || "General");
      setCoverImage(editingPost.cover_image || "");
    } else {
      setTitle("");
      setContent("");
      setCategory("Engineering");
      setCoverImage("");
    }
    setImageUrlInput("");
    setError("");
  }, [isOpen, editingPost]);

  if (!isOpen) return null;

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await api("/api/upload", { method: "POST", formData });
      setCoverImage(data.url);
      showToast?.("Cover photo uploaded.");
    } catch (err) {
      setError(err.detail || "Failed to upload photo — you can paste an image URL instead.");
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (status) => {
    if (!title.trim() || (!content.trim() && status === "published")) {
      setError("A title and story content are required to publish. Drafts need at least a title.");
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        cover_image: coverImage || null,
        category,
        status,
      };

      if (isEditing) {
        const updated = await api(`/api/posts/${editingPost.id}`, { method: "PUT", body: payload });
        onPostSaved?.(updated);
        showToast?.(status === "draft" ? "Draft saved." : "Story updated.");
      } else {
        const created = await api("/api/posts", { method: "POST", body: payload });
        onPostCreated?.(created);
        showToast?.(status === "draft" ? "Draft saved." : "Story published!");
      }
      onClose();
    } catch (err) {
      setError(err.detail || "Could not save the story. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const wordCount = content.split(/\s+/).filter(Boolean).length;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{isEditing ? "Edit story" : "Write a new story"}</h2>
          <button className="close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div className="form-error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Story title</label>
            <input
              type="text"
              className="form-input"
              placeholder="Give your story a clear, compelling title..."
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label">Category</label>
            <select className="form-select" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Cover photo</label>
            {coverImage ? (
              <div className="preview-image-wrap">
                <img src={coverImage} alt="Preview" className="preview-image" />
                <button type="button" className="remove-photo-btn" onClick={() => setCoverImage("")} title="Remove photo">
                  <X size={16} />
                </button>
              </div>
            ) : (
              <div>
                <div className="photo-upload-box" onClick={() => fileInputRef.current?.click()}>
                  <Upload size={28} color="var(--accent-primary)" style={{ margin: "0 auto 0.5rem" }} />
                  <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                    {uploading ? "Uploading image..." : "Upload cover photo"}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>PNG, JPG, WEBP or GIF</div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept="image/*"
                    style={{ display: "none" }}
                  />
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.75rem" }}>
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
                    onClick={() => {
                      if (imageUrlInput.trim()) {
                        setCoverImage(imageUrlInput.trim());
                        setImageUrlInput("");
                      }
                    }}
                  >
                    Use URL
                  </button>
                </div>

                <div style={{ marginTop: "0.75rem" }}>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginBottom: "0.4rem" }}>
                    Quick presets:
                  </div>
                  <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                    {PHOTO_PRESETS.map((preset) => (
                      <button
                        key={preset.name}
                        type="button"
                        className="cat-pill"
                        style={{ fontSize: "0.75rem", padding: "0.25rem 0.65rem", backgroundColor: "var(--bg-subtle)" }}
                        onClick={() => setCoverImage(preset.url)}
                      >
                        <Sparkles size={11} style={{ marginRight: "3px" }} />
                        {preset.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">
              Content <span style={{ fontWeight: 400, color: "var(--text-muted)" }}>({wordCount} words)</span>
            </label>
            <textarea
              className="form-textarea"
              placeholder="Write your story here... Share insights, tutorials, or ideas."
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={8}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose} disabled={submitting}>
            Cancel
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => handleSubmit("draft")}
            disabled={submitting || !title.trim()}
          >
            <FileText size={15} /> Save as draft
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => handleSubmit("published")}
            disabled={submitting || !title.trim() || !content.trim()}
          >
            {submitting ? "Saving…" : isEditing ? "Update story" : "Publish story"}
          </button>
        </div>
      </div>
    </div>
  );
}

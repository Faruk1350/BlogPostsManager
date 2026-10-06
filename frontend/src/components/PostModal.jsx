import React, { useState, useEffect } from "react";
import { X, Heart, Share2, MessageSquare, Clock, Send, Trash2 } from "lucide-react";

export default function PostModal({
  post,
  isOpen,
  onClose,
  onLike,
  onOpenShare,
  onOpenProfile,
  currentUser,
  showToast
}) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [loadingComments, setLoadingComments] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);

  useEffect(() => {
    if (isOpen && post) {
      fetchComments();
    }
  }, [isOpen, post]);

  if (!isOpen || !post) return null;

  const fetchComments = async () => {
    setLoadingComments(true);
    try {
      const res = await fetch(`/api/posts/${post.id}/comments`);
      if (res.ok) {
        const data = await res.json();
        setComments(data);
      }
    } catch (err) {
      console.error("Failed to fetch comments", err);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!newComment.trim() || submittingComment) return;

    setSubmittingComment(true);
    try {
      const res = await fetch(`/api/posts/${post.id}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: newComment.trim(),
          author_id: currentUser?.id || "user_admin",
          author_name: currentUser?.display_name || "Faruk Developer",
          author_avatar: currentUser?.avatar_url || ""
        })
      });

      if (res.ok) {
        const created = await res.json();
        setComments((prev) => [...prev, created]);
        setNewComment("");
        post.comments_count = (post.comments_count || 0) + 1;
        showToast("Comment posted successfully!");
      }
    } catch (err) {
      console.error("Failed to post comment", err);
      showToast("Error posting comment");
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      const res = await fetch(`/api/comments/${commentId}`, { method: "DELETE" });
      if (res.ok) {
        setComments((prev) => prev.filter((c) => c.id !== commentId));
        post.comments_count = Math.max(0, (post.comments_count || 1) - 1);
        showToast("Comment deleted.");
      }
    } catch (err) {
      console.error("Failed to delete comment", err);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "Recently";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric"
      });
    } catch {
      return "Recently";
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
        {post.cover_image && (
          <img
            src={post.cover_image}
            alt={post.title}
            className="reader-cover"
            onError={(e) => {
              e.target.src =
                "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=1200&auto=format&fit=crop&q=80";
            }}
          />
        )}

        {/* Reader Content Body */}
        <div className="reader-content">
          {/* Category & Read Time */}
          <div className="reader-meta-row">
            {post.category && (
              <span className="category-tag" style={{ position: "static" }}>
                {post.category}
              </span>
            )}
            <div className="read-time-pill">
              <Clock size={13} />
              <span>{post.read_time || "3 min read"}</span>
            </div>
          </div>

          {/* Title */}
          <h1 className="reader-title">{post.title}</h1>

          {/* Author Details */}
          <div className="card-author-row" style={{ margin: "0.5rem 0 1rem" }}>
            <div
              className="card-author-info"
              onClick={() => {
                onClose();
                onOpenProfile(post.author_id || "user_admin");
              }}
            >
              <img
                src={
                  post.author_avatar ||
                  "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"
                }
                alt={post.author_name}
                className="card-author-avatar"
                style={{ width: "36px", height: "36px" }}
              />
              <div>
                <div className="card-author-name">{post.author_name}</div>
                <div className="card-date">{formatDate(post.created_at)}</div>
              </div>
            </div>

            {/* Like & Share Action Buttons */}
            <div className="card-actions">
              <button
                className={`action-btn ${post.is_liked ? "liked" : ""}`}
                onClick={() => onLike(post.id)}
              >
                <Heart
                  size={18}
                  fill={post.is_liked ? "currentColor" : "none"}
                  strokeWidth={post.is_liked ? 0 : 2}
                />
                <span>{post.likes_count || 0}</span>
              </button>

              <button
                className="action-btn"
                onClick={() => onOpenShare(post)}
              >
                <Share2 size={18} strokeWidth={2} />
                <span>{post.shares_count || 0}</span>
              </button>
            </div>
          </div>

          {/* Full Text Body */}
          <div className="reader-body">{post.content}</div>
        </div>

        {/* Comments Section */}
        <div className="comments-section">
          <div className="comments-header">
            <MessageSquare size={18} />
            <span>Comments ({comments.length})</span>
          </div>

          {/* Comment Form */}
          <form className="comment-input-row" onSubmit={handleAddComment}>
            <img
              src={
                currentUser?.avatar_url ||
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"
              }
              alt={currentUser?.display_name || "User"}
              className="comment-avatar"
            />
            <div className="comment-field-wrap">
              <textarea
                className="comment-input"
                placeholder="Join the discussion... Share your thoughts."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                rows={2}
              />
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submittingComment || !newComment.trim()}
                  style={{
                    padding: "0.45rem 1rem",
                    fontSize: "0.825rem",
                    opacity: !newComment.trim() ? 0.6 : 1
                  }}
                >
                  <Send size={14} />
                  <span>{submittingComment ? "Posting..." : "Post Comment"}</span>
                </button>
              </div>
            </div>
          </form>

          {/* Comments List */}
          <div className="comment-list">
            {loadingComments ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Loading conversation...
              </div>
            ) : comments.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                No comments yet. Be the first to share your perspective!
              </div>
            ) : (
              comments.map((c) => (
                <div key={c.id} className="comment-item">
                  <img
                    src={
                      c.author_avatar ||
                      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"
                    }
                    alt={c.author_name}
                    className="comment-avatar"
                  />
                  <div className="comment-item-body">
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center"
                      }}
                    >
                      <span className="comment-author-name">{c.author_name}</span>
                      <span className="comment-timestamp">
                        {formatDate(c.created_at)}
                      </span>
                    </div>
                    <p className="comment-text">{c.content}</p>
                    {currentUser &&
                      (currentUser.id === c.author_id ||
                        currentUser.display_name === c.author_name) && (
                        <button
                          className="comment-delete-btn"
                          onClick={() => handleDeleteComment(c.id)}
                        >
                          <Trash2 size={12} style={{ display: "inline", marginRight: "3px" }} />
                          Delete
                        </button>
                      )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

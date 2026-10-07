import React, { useState, useEffect } from "react";
import { X, Heart, Share2, MessageSquare, Clock, Send, Trash2, Pencil, Eye, Sparkles } from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function PostModal({
  post,
  isOpen,
  onClose,
  onLike,
  onOpenShare,
  onOpenProfile,
  onEditPost,
  onDeletePost,
  onOpenReader,
  onRequireAuth,
  showToast
}) {
  const { profile, isAuthenticated, isAdmin } = useAuth();
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [loadingComments, setLoadingComments] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [related, setRelated] = useState([]);

  useEffect(() => {
    if (!isOpen || !post) return;
    let cancelled = false;

    (async () => {
      setLoadingComments(true);
      try {
        const [commentsData, relatedData] = await Promise.all([
          api(`/api/posts/${post.id}/comments`),
          api(`/api/posts/${post.id}/related`).catch(() => []),
        ]);
        if (!cancelled) {
          setComments(commentsData || []);
          setRelated(relatedData || []);
        }
      } catch (err) {
        if (!cancelled) console.error("Failed to load reader data", err);
      } finally {
        if (!cancelled) setLoadingComments(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOpen, post?.id]);

  if (!isOpen || !post) return null;

  const isAuthor = Boolean(profile && profile.id === post.author_id) || isAdmin;

  const handleAddComment = async (event) => {
    event.preventDefault();
    if (!isAuthenticated) {
      onRequireAuth?.();
      return;
    }
    if (!newComment.trim() || submittingComment) return;

    setSubmittingComment(true);
    try {
      const created = await api(`/api/posts/${post.id}/comments`, {
        method: "POST",
        body: { content: newComment.trim() },
      });
      setComments((prev) => [...prev, created]);
      setNewComment("");
      post.comments_count = (post.comments_count || 0) + 1;
      showToast?.("Comment posted!");
    } catch (err) {
      showToast?.(err.detail || "Could not post comment.");
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await api(`/api/comments/${commentId}`, { method: "DELETE" });
      setComments((prev) => prev.filter((comment) => comment.id !== commentId));
      post.comments_count = Math.max(0, (post.comments_count || 1) - 1);
      showToast?.("Comment deleted.");
    } catch (err) {
      showToast?.(err.detail || "Could not delete comment.");
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "Recently";
    try {
      return new Date(isoString).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "Recently";
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()} style={{ padding: 0 }}>
        {/* Floating actions */}
        <div className="reader-float-actions">
          {isAuthor && onEditPost && (
            <button
              className="close-btn"
              title="Edit story"
              style={{ backgroundColor: "var(--bg-elevated-strong)" }}
              onClick={() => onEditPost(post)}
            >
              <Pencil size={16} />
            </button>
          )}
          {isAuthor && onDeletePost && (
            <button
              className="close-btn"
              title="Delete story"
              style={{ backgroundColor: "var(--bg-elevated-strong)" }}
              onClick={() => onDeletePost(post.id)}
            >
              <Trash2 size={16} />
            </button>
          )}
          <button
            className="close-btn"
            style={{ backgroundColor: "var(--bg-elevated-strong)" }}
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
          <div className="reader-meta-row">
            {post.category && (
              <span className="category-tag" style={{ position: "static" }}>
                {post.category}
              </span>
            )}
            {post.status === "draft" && (
              <span className="draft-badge">Draft — only visible to you</span>
            )}
            <div className="read-time-pill">
              <Clock size={13} />
              <span>{post.read_time || "3 min read"}</span>
            </div>
            <div className="read-time-pill" title="Views">
              <Eye size={13} />
              <span>{post.views_count || 0}</span>
            </div>
          </div>

          <h1 className="reader-title">{post.title}</h1>

          <div className="card-author-row" style={{ margin: "0.5rem 0 1rem" }}>
            <div
              className="card-author-info"
              onClick={() => {
                onClose();
                onOpenProfile(post.author_id || "user_admin");
              }}
            >
              <img
                src={post.author_avatar || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"}
                alt={post.author_name}
                className="card-author-avatar"
                style={{ width: "36px", height: "36px" }}
              />
              <div>
                <div className="card-author-name">{post.author_name}</div>
                <div className="card-date">{formatDate(post.created_at)}</div>
              </div>
            </div>

            <div className="card-actions">
              <button
                className={`action-btn ${post.is_liked ? "liked" : ""}`}
                onClick={() => (isAuthenticated ? onLike(post.id) : onRequireAuth?.())}
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
                onClick={() => (isAuthenticated ? onOpenShare(post) : onRequireAuth?.())}
              >
                <Share2 size={18} strokeWidth={2} />
                <span>{post.shares_count || 0}</span>
              </button>
            </div>
          </div>

          <div className="reader-body">{post.content}</div>
        </div>

        {/* Related stories */}
        {related.length > 0 && (
          <div className="related-section">
            <div className="comments-header">
              <Sparkles size={17} />
              <span>Related stories</span>
            </div>
            <div className="related-grid">
              {related.map((item) => (
                <button key={item.id} className="related-card" onClick={() => onOpenReader(item)}>
                  {item.cover_image && <img src={item.cover_image} alt={item.title} loading="lazy" />}
                  <div className="related-body">
                    <span className="related-category">{item.category}</span>
                    <span className="related-title">{item.title}</span>
                    <span className="related-meta">
                      {item.author_name} · {item.read_time}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Comments Section */}
        <div className="comments-section">
          <div className="comments-header">
            <MessageSquare size={18} />
            <span>Comments ({comments.length})</span>
          </div>

          {isAuthenticated ? (
            <form className="comment-input-row" onSubmit={handleAddComment}>
              <img
                src={profile?.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"}
                alt={profile?.display_name || "User"}
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
                    style={{ padding: "0.45rem 1rem", fontSize: "0.825rem" }}
                  >
                    <Send size={14} />
                    <span>{submittingComment ? "Posting..." : "Post Comment"}</span>
                  </button>
                </div>
              </div>
            </form>
          ) : (
            <div className="comment-signin">
              <span>Join the discussion</span>
              <button className="btn-primary" onClick={() => onRequireAuth?.()}>
                Sign in to comment
              </button>
            </div>
          )}

          <div className="comment-list">
            {loadingComments ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>Loading conversation...</div>
            ) : comments.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
                No comments yet. Be the first to share your perspective!
              </div>
            ) : (
              comments.map((comment) => (
                <div key={comment.id} className="comment-item">
                  <img
                    src={comment.author_avatar || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"}
                    alt={comment.author_name}
                    className="comment-avatar"
                  />
                  <div className="comment-item-body">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className="comment-author-name">{comment.author_name}</span>
                      <span className="comment-timestamp">{formatDate(comment.created_at)}</span>
                    </div>
                    <p className="comment-text">{comment.content}</p>
                    {(isAdmin || (profile && profile.id === comment.author_id)) && (
                      <button className="comment-delete-btn" onClick={() => handleDeleteComment(comment.id)}>
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

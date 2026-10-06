import React from "react";
import { Heart, MessageSquare, Share2, Clock, Trash2 } from "lucide-react";

export default function PostCard({
  post,
  onLike,
  onOpenReader,
  onOpenShare,
  onOpenProfile,
  onDeletePost,
  currentUser
}) {
  const isAuthor = currentUser && currentUser.id === post.author_id;

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
    <article className="blog-card">
      {/* Cover Image */}
      {post.cover_image && (
        <div className="card-image-wrap" onClick={() => onOpenReader(post)}>
          <img
            src={post.cover_image}
            alt={post.title}
            className="card-image"
            loading="lazy"
            onError={(e) => {
              e.target.src = "https://images.unsplash.com/photo-1499750310107-5fef28a66643?w=800&auto=format&fit=crop&q=80";
            }}
          />
          {post.category && (
            <span className="category-tag">{post.category}</span>
          )}
        </div>
      )}

      {/* Card Content */}
      <div className="card-body">
        {/* Author & Date */}
        <div className="card-author-row">
          <div
            className="card-author-info"
            onClick={() => onOpenProfile(post.author_id || "user_admin")}
          >
            <img
              src={
                post.author_avatar ||
                "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"
              }
              alt={post.author_name}
              className="card-author-avatar"
            />
            <span className="card-author-name">{post.author_name}</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span className="card-date">{formatDate(post.created_at)}</span>
            {isAuthor && onDeletePost && (
              <button
                className="action-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeletePost(post.id);
                }}
                title="Delete story"
                style={{ padding: "0.2rem" }}
              >
                <Trash2 size={14} color="#94a3b8" />
              </button>
            )}
          </div>
        </div>

        {/* Post Title */}
        <h2 className="card-title" onClick={() => onOpenReader(post)}>
          {post.title}
        </h2>

        {/* Excerpt */}
        <p className="card-excerpt" onClick={() => onOpenReader(post)}>
          {post.content}
        </p>

        {/* Footer Actions */}
        <div className="card-footer">
          <div className="card-actions">
            {/* Like */}
            <button
              className={`action-btn ${post.is_liked ? "liked" : ""}`}
              onClick={(e) => {
                e.stopPropagation();
                onLike(post.id);
              }}
              title={post.is_liked ? "Unlike" : "Like story"}
            >
              <Heart
                size={16}
                fill={post.is_liked ? "currentColor" : "none"}
                strokeWidth={post.is_liked ? 0 : 2}
              />
              <span>{post.likes_count || 0}</span>
            </button>

            {/* Comment */}
            <button
              className="action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpenReader(post, true);
              }}
              title="View comments"
            >
              <MessageSquare size={16} strokeWidth={2} />
              <span>{post.comments_count || 0}</span>
            </button>

            {/* Share */}
            <button
              className="action-btn"
              onClick={(e) => {
                e.stopPropagation();
                onOpenShare(post);
              }}
              title="Share story"
            >
              <Share2 size={16} strokeWidth={2} />
              <span>{post.shares_count || 0}</span>
            </button>
          </div>

          {/* Reading Time */}
          <div className="read-time-pill">
            <Clock size={13} />
            <span>{post.read_time || "3 min read"}</span>
          </div>
        </div>
      </div>
    </article>
  );
}

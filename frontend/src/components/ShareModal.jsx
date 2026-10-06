import React, { useState } from "react";
import { X, Copy, Check, MessageCircle, Mail, Share2 } from "lucide-react";

import { api } from "../lib/api";

export default function ShareModal({
  post,
  isOpen,
  onClose,
  showToast
}) {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !post) return null;

  const currentUrl = typeof window !== "undefined"
    ? `${window.location.origin}?post=${post.id}`
    : `http://localhost:5173?post=${post.id}`;

  const trackShare = async (platform) => {
    try {
      await api(`/api/posts/${post.id}/share`, {
        method: "POST",
        body: { platform },
      });
      post.shares_count = (post.shares_count || 0) + 1;
    } catch (err) {
      console.error("Failed to track share", err);
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(currentUrl);
    setCopied(true);
    trackShare("link");
    showToast("Link copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  const shareTwitter = () => {
    trackShare("twitter");
    const text = encodeURIComponent(`Reading "${post.title}" on Chronicle:`);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(currentUrl)}`, "_blank");
  };

  const shareLinkedIn = () => {
    trackShare("linkedin");
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(currentUrl)}`, "_blank");
  };

  const shareWhatsApp = () => {
    trackShare("whatsapp");
    const text = encodeURIComponent(`Check out "${post.title}": ${currentUrl}`);
    window.open(`https://api.whatsapp.com/send?text=${text}`, "_blank");
  };

  const shareEmail = () => {
    trackShare("email");
    const subject = encodeURIComponent(post.title);
    const body = encodeURIComponent(`Hi,\n\nI thought you might enjoy reading this story:\n"${post.title}"\n\n${currentUrl}`);
    window.open(`mailto:?subject=${subject}&body=${body}`);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "460px" }}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Share2 size={18} />
            <h2 className="modal-title" style={{ fontSize: "1.15rem" }}>Share Story</h2>
          </div>
          <button className="close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body" style={{ gap: "1.25rem" }}>
          <div>
            <div style={{ fontSize: "0.95rem", fontWeight: 700, marginBottom: "0.25rem" }}>
              {post.title}
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              By {post.author_name} · {post.read_time}
            </div>
          </div>

          {/* Copy Link Input */}
          <div className="form-group">
            <label className="form-label">Story Link</label>
            <div className="copy-input-row">
              <input
                type="text"
                readOnly
                value={currentUrl}
                className="copy-input"
              />
              <button
                type="button"
                className="btn-primary"
                onClick={handleCopyLink}
                style={{ padding: "0.55rem 0.95rem", fontSize: "0.825rem" }}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
          </div>

          {/* Share Channels */}
          <div className="form-group">
            <label className="form-label">Share to Social</label>
            <div className="share-links-grid">
              <button className="share-link-btn" onClick={shareTwitter}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                </svg>
                <span>X / Twitter</span>
              </button>
              <button className="share-link-btn" onClick={shareLinkedIn}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#0a66c2">
                  <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76a1.64 1.64 0 1 0 0-3.28 1.64 1.64 0 0 0 0 3.28m1.37 9.74v-8.37H5.09v8.37h2.74z"/>
                </svg>
                <span>LinkedIn</span>
              </button>
              <button className="share-link-btn" onClick={shareWhatsApp}>
                <MessageCircle size={16} color="#16a34a" />
                <span>WhatsApp</span>
              </button>
              <button className="share-link-btn" onClick={shareEmail}>
                <Mail size={16} color="#ea580c" />
                <span>Email</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

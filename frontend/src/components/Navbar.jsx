import React from "react";
import { Feather, Search, Plus, Database, Settings, LogOut, LogIn } from "lucide-react";

import { useAuth } from "../lib/auth";

export default function Navbar({
  searchTerm,
  setSearchTerm,
  onOpenCreate,
  onOpenProfile,
  onOpenSettings,
  onSignIn,
  onLogout,
  dbStatus,
}) {
  const { profile, isAuthenticated, isAdmin } = useAuth();

  return (
    <header className="navbar">
      <div className="nav-content">
        {/* Brand */}
        <div className="nav-brand" onClick={() => setSearchTerm("")}>
          <div className="brand-icon">
            <Feather size={19} strokeWidth={2.5} />
          </div>
          <span>Chronicle</span>
        </div>

        {/* Search */}
        <div className="nav-search">
          <Search size={16} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search stories, topics, authors..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Actions */}
        <div className="nav-actions">
          <div
            className={`status-badge ${dbStatus.connected ? "supabase" : "local"}`}
            title={dbStatus.connected ? "Connected to Supabase PostgreSQL" : "Local database"}
          >
            <span className="status-dot" />
            <span>{dbStatus.connected ? "Supabase" : "Local DB"}</span>
          </div>

          {isAuthenticated && (
            <button className="btn-primary" onClick={onOpenCreate}>
              <Plus size={16} strokeWidth={2.5} />
              <span>Write</span>
            </button>
          )}

          {isAuthenticated ? (
            <>
              <button
                className="profile-pill"
                onClick={() => onOpenProfile(profile.id)}
                title={`${profile.display_name}${isAdmin ? " (admin)" : ""}`}
              >
                <img
                  src={profile.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"}
                  alt={profile.display_name}
                  className="profile-avatar-sm"
                />
                <span className="profile-name-sm">{profile.display_name.split(" ")[0]}</span>
                {isAdmin && <span className="admin-dot" title="Administrator" />}
              </button>

              <button className="icon-btn" onClick={onOpenSettings} title="Settings">
                <Settings size={17} />
              </button>
              <button className="icon-btn" onClick={onLogout} title="Sign out">
                <LogOut size={17} />
              </button>
            </>
          ) : (
            <button className="btn-primary" onClick={onSignIn}>
              <LogIn size={16} strokeWidth={2.5} />
              <span>Sign in</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

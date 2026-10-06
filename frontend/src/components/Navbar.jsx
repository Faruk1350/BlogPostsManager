import React from "react";
import { Feather, Search, Plus, Database, Sparkles } from "lucide-react";

export default function Navbar({
  searchTerm,
  setSearchTerm,
  onOpenCreate,
  onOpenProfile,
  currentUser,
  dbStatus
}) {
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
          {/* Database indicator */}
          <div
            className={`status-badge ${dbStatus.connected ? "supabase" : "local"}`}
            title={
              dbStatus.connected
                ? "Connected directly to Supabase cloud PostgreSQL"
                : "Operating in Local Demo DB. Configure SUPABASE_URL and SUPABASE_KEY in backend/.env to connect."
            }
          >
            <span className="status-dot" />
            <span>{dbStatus.connected ? "Supabase" : "Local DB"}</span>
          </div>

          {/* Write Button */}
          <button className="btn-primary" onClick={onOpenCreate}>
            <Plus size={16} strokeWidth={2.5} />
            <span>Write</span>
          </button>

          {/* Profile Pill */}
          {currentUser && (
            <div
              className="profile-pill"
              onClick={onOpenProfile}
              title={`Logged in as ${currentUser.display_name}`}
            >
              <img
                src={currentUser.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100"}
                alt={currentUser.display_name}
                className="profile-avatar-sm"
              />
              <span className="profile-name-sm">{currentUser.display_name.split(" ")[0]}</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

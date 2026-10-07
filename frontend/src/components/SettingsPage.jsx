import React, { useEffect, useState } from "react";
import { ArrowLeft, Bell, Check, Lock, Palette, Save, Upload } from "lucide-react";

import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

const CATEGORIES = ["Technology", "Design", "Engineering", "Database", "Lifestyle", "General"];
const THEMES = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];
const DIGESTS = [
  { value: "off", label: "Off" },
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
];

export default function SettingsPage({ onBack, showToast }) {
  const { profile, preferences, updateProfile, updatePreferences, changePassword } = useAuth();

  const [form, setForm] = useState({ display_name: "", tagline: "", bio: "", location: "", website: "", avatar_url: "" });
  const [prefs, setPrefs] = useState({ theme: "system", notify_likes: true, notify_comments: true, notify_shares: true, favorite_categories: [], default_sort: "recent", digest_frequency: "off" });
  const [passwordForm, setPasswordForm] = useState({ current: "", next: "" });
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (profile) {
      setForm({
        display_name: profile.display_name || "",
        tagline: profile.tagline || "",
        bio: profile.bio || "",
        location: profile.location || "",
        website: profile.website || "",
        avatar_url: profile.avatar_url || "",
      });
    }
    if (preferences) {
      setPrefs({
        theme: preferences.theme || "system",
        notify_likes: preferences.notify_likes ?? true,
        notify_comments: preferences.notify_comments ?? true,
        notify_shares: preferences.notify_shares ?? true,
        favorite_categories: preferences.favorite_categories || [],
        default_sort: preferences.default_sort || "recent",
        digest_frequency: preferences.digest_frequency || "off",
      });
    }
  }, [profile, preferences]);

  const setField = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const saveProfile = async (event) => {
    event.preventDefault();
    setSavingProfile(true);
    try {
      await updateProfile(form);
      showToast("Profile saved.");
    } catch (err) {
      showToast(err.detail || "Could not save profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      await updatePreferences(prefs);
      showToast("Preferences saved.");
    } catch (err) {
      showToast(err.detail || "Could not save preferences.");
    } finally {
      setSavingPrefs(false);
    }
  };

  const toggleCategory = (category) => {
    setPrefs((prev) => ({
      ...prev,
      favorite_categories: prev.favorite_categories.includes(category)
        ? prev.favorite_categories.filter((c) => c !== category)
        : [...prev.favorite_categories, category],
    }));
  };

  const uploadAvatar = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await api("/api/upload", { method: "POST", formData });
      setForm((prev) => ({ ...prev, avatar_url: data.url }));
      showToast("Avatar uploaded — remember to save.");
    } catch (err) {
      showToast(err.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const submitPassword = async (event) => {
    event.preventDefault();
    setSavingPassword(true);
    try {
      await changePassword(passwordForm.current, passwordForm.next);
      setPasswordForm({ current: "", next: "" });
      showToast("Password updated.");
    } catch (err) {
      showToast(err.detail || "Could not change password.");
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <div className="settings-page">
      <button className="auth-back" onClick={onBack} type="button">
        <ArrowLeft size={16} /> Back to stories
      </button>

      <h1 className="settings-title">Settings</h1>
      <p className="settings-subtitle">Manage your profile, preferences and account security.</p>

      <div className="settings-grid">
        {/* Profile */}
        <section className="settings-card">
          <h2><Palette size={16} /> Profile</h2>
          <form onSubmit={saveProfile} className="settings-form">
            <div className="settings-avatar-row">
              <img
                src={form.avatar_url || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"}
                alt="Avatar"
                className="settings-avatar"
              />
              <label className="btn-secondary settings-upload">
                <Upload size={14} /> {uploading ? "Uploading…" : "Change avatar"}
                <input type="file" accept="image/*" onChange={uploadAvatar} hidden />
              </label>
            </div>

            <label className="settings-field">
              <span>Display name</span>
              <input value={form.display_name} onChange={setField("display_name")} maxLength={80} required />
            </label>
            <label className="settings-field">
              <span>Tagline</span>
              <input value={form.tagline} onChange={setField("tagline")} placeholder="One line about you" maxLength={120} />
            </label>
            <label className="settings-field">
              <span>Bio</span>
              <textarea value={form.bio} onChange={setField("bio")} rows={4} maxLength={500} />
            </label>
            <div className="settings-row">
              <label className="settings-field">
                <span>Location</span>
                <input value={form.location} onChange={setField("location")} maxLength={80} />
              </label>
              <label className="settings-field">
                <span>Website</span>
                <input value={form.website} onChange={setField("website")} maxLength={200} />
              </label>
            </div>

            <button className="btn-primary" type="submit" disabled={savingProfile}>
              <Save size={15} /> {savingProfile ? "Saving…" : "Save profile"}
            </button>
          </form>
        </section>

        {/* Preferences */}
        <section className="settings-card">
          <h2><Bell size={16} /> Preferences</h2>

          <div className="settings-field">
            <span>Theme</span>
            <div className="settings-pills">
              {THEMES.map((theme) => (
                <button
                  key={theme.value}
                  type="button"
                  className={`cat-pill ${prefs.theme === theme.value ? "active" : ""}`}
                  onClick={() => setPrefs((prev) => ({ ...prev, theme: theme.value }))}
                >
                  {theme.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-field">
            <span>Default feed sort</span>
            <select
              className="form-select"
              value={prefs.default_sort}
              onChange={(e) => setPrefs((prev) => ({ ...prev, default_sort: e.target.value }))}
            >
              <option value="recent">Latest first</option>
              <option value="likes">Most popular</option>
            </select>
          </div>

          <div className="settings-field">
            <span>Email notifications</span>
            {[
              ["notify_likes", "Likes on my stories"],
              ["notify_comments", "Comments on my stories"],
              ["notify_shares", "Shares of my stories"],
            ].map(([key, label]) => (
              <label key={key} className="settings-toggle">
                <input
                  type="checkbox"
                  checked={Boolean(prefs[key])}
                  onChange={(e) => setPrefs((prev) => ({ ...prev, [key]: e.target.checked }))}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>

          <div className="settings-field">
            <span>Digest frequency</span>
            <div className="settings-pills">
              {DIGESTS.map((digest) => (
                <button
                  key={digest.value}
                  type="button"
                  className={`cat-pill ${prefs.digest_frequency === digest.value ? "active" : ""}`}
                  onClick={() => setPrefs((prev) => ({ ...prev, digest_frequency: digest.value }))}
                >
                  {digest.label}
                </button>
              ))}
            </div>
          </div>

          <div className="settings-field">
            <span>Favourite categories</span>
            <div className="settings-pills">
              {CATEGORIES.map((category) => (
                <button
                  key={category}
                  type="button"
                  className={`cat-pill ${prefs.favorite_categories.includes(category) ? "active" : ""}`}
                  onClick={() => toggleCategory(category)}
                >
                  {prefs.favorite_categories.includes(category) && <Check size={12} />} {category}
                </button>
              ))}
            </div>
          </div>

          <button className="btn-primary" type="button" onClick={savePreferences} disabled={savingPrefs}>
            <Save size={15} /> {savingPrefs ? "Saving…" : "Save preferences"}
          </button>
        </section>

        {/* Security */}
        <section className="settings-card">
          <h2><Lock size={16} /> Security</h2>
          <form onSubmit={submitPassword} className="settings-form">
            <label className="settings-field">
              <span>Current password</span>
              <input
                type="password"
                value={passwordForm.current}
                onChange={(e) => setPasswordForm((prev) => ({ ...prev, current: e.target.value }))}
                required
              />
            </label>
            <label className="settings-field">
              <span>New password</span>
              <input
                type="password"
                value={passwordForm.next}
                onChange={(e) => setPasswordForm((prev) => ({ ...prev, next: e.target.value }))}
                minLength={8}
                required
              />
            </label>
            <button className="btn-primary" type="submit" disabled={savingPassword}>
              <Lock size={15} /> {savingPassword ? "Updating…" : "Update password"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}

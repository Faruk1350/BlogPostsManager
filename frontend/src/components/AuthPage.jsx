import React, { useState } from "react";
import { ArrowLeft, Feather, Lock, Mail, User } from "lucide-react";

import { useAuth } from "../lib/auth";

export default function AuthPage({ mode = "login", onModeChange, onSuccess, onBack }) {
  const { login, signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isSignup = mode === "signup";

  const handleSubmit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (isSignup) {
        await signup(email.trim(), password, displayName.trim());
      } else {
        await login(email.trim(), password);
      }
      onSuccess?.();
    } catch (err) {
      setError(err.detail || err.message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <button className="auth-back" onClick={onBack} type="button">
          <ArrowLeft size={16} /> Back to stories
        </button>

        <div className="auth-brand">
          <div className="brand-icon">
            <Feather size={19} strokeWidth={2.5} />
          </div>
          <span>Chronicle</span>
        </div>

        <h1 className="auth-title">{isSignup ? "Create your account" : "Welcome back"}</h1>
        <p className="auth-subtitle">
          {isSignup
            ? "Sign up to publish stories, react, comment and personalise your feed."
            : "Sign in to continue writing and interacting."}
        </p>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          {isSignup && (
            <label className="auth-field">
              <User size={15} />
              <input
                type="text"
                placeholder="Display name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={80}
                required
              />
            </label>
          )}

          <label className="auth-field">
            <Mail size={15} />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>

          <label className="auth-field">
            <Lock size={15} />
            <input
              type="password"
              placeholder={isSignup ? "Password (min. 8 characters)" : "Password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>

          <button className="btn-primary auth-submit" type="submit" disabled={busy}>
            {busy ? "Please wait…" : isSignup ? "Create account" : "Sign in"}
          </button>
        </form>

        <div className="auth-switch">
          {isSignup ? "Already have an account?" : "New to Chronicle?"}{" "}
          <button type="button" onClick={() => onModeChange(isSignup ? "login" : "signup")}>
            {isSignup ? "Sign in" : "Create one"}
          </button>
        </div>

        {isSignup && (
          <p className="auth-hint">
            The first account created becomes the admin and inherits the original demo posts.
          </p>
        )}
      </div>
    </div>
  );
}

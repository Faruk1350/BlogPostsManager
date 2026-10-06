import React from "react";
import { CheckCircle2 } from "lucide-react";

export default function Toast({ toasts }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className="toast">
          <CheckCircle2 size={16} color="#38bdf8" />
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}

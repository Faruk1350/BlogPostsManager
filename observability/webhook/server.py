"""Local Alertmanager webhook receiver.

Receives alert payloads from Alertmanager, appends them as JSON lines to a log
file (shipped to Loki by Promtail) and keeps the last N alerts in memory so the
  GET /alerts endpoint can be used for a quick look.
"""

import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG_FILE = os.getenv("ALERT_LOG", "/var/log/blog/alerts.log")
PORT = int(os.getenv("PORT", "9099"))
MAX_KEEP = int(os.getenv("MAX_KEEP", "200"))

_recent = []
_lock = threading.Lock()


def _record(entry):
    with _lock:
        _recent.append(entry)
        del _recent[:-MAX_KEEP]

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")

    level = "ALERT" if entry.get("status") == "firing" else "RESOLVED"
    print(f"{level} {entry.get('severity', '-')} {entry.get('alertname', '-')} :: {entry.get('summary', '')}", flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "alert-webhook/1.0"

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/alerts":
            self._send(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": f"invalid payload: {exc}"})
            return

        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            _record(
                {
                    "received_at": datetime.now(timezone.utc).isoformat(),
                    "status": alert.get("status"),
                    "alertname": labels.get("alertname"),
                    "severity": labels.get("severity"),
                    "service": labels.get("service"),
                    "instance": labels.get("instance"),
                    "summary": annotations.get("summary"),
                    "description": annotations.get("description"),
                    "startsAt": alert.get("startsAt"),
                    "endsAt": alert.get("endsAt"),
                }
            )

        self._send(200, {"received": len(payload.get("alerts", []))})

    def do_GET(self):  # noqa: N802
        path = self.path.rstrip("/")
        if path in ("", "/alerts"):
            with _lock:
                self._send(200, {"count": len(_recent), "recent": list(_recent)})
        elif path == "/healthz":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args):  # silence default access logging
        return


if __name__ == "__main__":
    print(f"alert-webhook listening on :{PORT}, writing to {LOG_FILE}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

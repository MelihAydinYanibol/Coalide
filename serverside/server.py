#!/usr/bin/env python3
"""
Coalide — parental stats server (server side, for the parent).

A tiny, zero-dependency HTTP server (stdlib only) that:

  * receives learning-stats snapshots pushed by the child's Coalide app
    (POST /api/stats), one stored record per user, and
  * serves a web dashboard (GET /) that shows all of those stats — the same
    information as the in-app "İstatistikler" screen, in the browser.

The child's app pushes a fresh snapshot every time its menu opens (see
stats_reporter.py in the main project), so the dashboard stays current without
the parent needing any access to the child's machine.

Run it on the parent's machine / a always-on box:

    python server.py                 # listens on 0.0.0.0:5055
    COALIDE_STATS_PORT=8000 python server.py

Then point the child's config.json "STATS_SERVER_URL" at this host, e.g.
    "STATS_SERVER_URL": "http://192.168.1.50:5055"

Data is stored as plain JSON under ./data/<user>.json. Nothing here ships in a
Coalide release — the whole `serverside/` folder is wiped by `-release-ready`.
"""

import json
import os
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import report      # daily Telegram report (stdlib-only, sits next to this file)
import admin_api    # admin auth + config/words sync backend

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.html")
ADMIN_FILE_HTML = os.path.join(BASE_DIR, "admin.html")

HOST = os.environ.get("COALIDE_STATS_HOST", "0.0.0.0")
PORT = int(os.environ.get("COALIDE_STATS_PORT", "5055"))

MAX_BODY_BYTES = 12 * 1024 * 1024  # 12 MB — words.json sync can be a few hundred KB

# Usernames end up in a filename; keep only safe characters (Unicode word
# chars + hyphen), matching utils._sanitize_username in the main project.
_UNSAFE_RE = re.compile(r"[^\w\-]", re.UNICODE)

_lock = threading.Lock()  # serialize reads/writes of the JSON store


# --------------------------------------------------------------------------
# Storage
# --------------------------------------------------------------------------

def _safe_user(name: str) -> str:
    return _UNSAFE_RE.sub("", (name or "").strip()) or "default"


def _user_path(user: str) -> str:
    return os.path.join(DATA_DIR, f"{_safe_user(user)}.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save_record(user: str, record: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    path = _user_path(user)
    tmp = path + ".tmp"
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # atomic on the same filesystem


def _load_record(user: str):
    path = _user_path(user)
    with _lock:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


def _list_users() -> list:
    if not os.path.isdir(DATA_DIR):
        return []
    users = []
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith(".json"):
            continue
        rec = _load_record(fname[:-5])
        if not isinstance(rec, dict):
            continue
        users.append({
            "username": rec.get("username", fname[:-5]),
            "updated_at": rec.get("updated_at"),
            "client_time": rec.get("client_time"),
        })
    users.sort(key=lambda u: u.get("updated_at") or "", reverse=True)
    return users


def all_records() -> list:
    """Every stored per-user record (used by the daily report)."""
    if not os.path.isdir(DATA_DIR):
        return []
    out = []
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json"):
            continue
        rec = _load_record(fname[:-5])
        if isinstance(rec, dict):
            out.append(rec)
    return out


# --------------------------------------------------------------------------
# HTTP handler
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    server_version = "CoalideStats/1.0"

    # ---- helpers ----
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, content_type: str, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_html_file(self, path, missing):
        try:
            with open(path, "rb") as f:
                self._send_bytes(f.read(), "text/html; charset=utf-8")
        except FileNotFoundError:
            self._send_bytes(missing, "text/plain; charset=utf-8", status=500)

    def _read_json(self):
        """Read and parse a JSON request body. Returns (obj, error_response_sent)."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            self._send_json({"error": "empty body"}, status=400)
            return None
        if length > MAX_BODY_BYTES:
            self._send_json({"error": "payload too large"}, status=413)
            return None
        try:
            obj = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self._send_json({"error": "invalid JSON"}, status=400)
            return None
        if not isinstance(obj, dict):
            self._send_json({"error": "expected a JSON object"}, status=400)
            return None
        return obj

    def _admin_token(self):
        return (self.headers.get("X-Admin-Token")
                or parse_qs(urlparse(self.path).query).get("token", [None])[0])

    def _require_admin(self) -> bool:
        """Return True if the request carries a valid admin token, else 401."""
        if admin_api.valid_token(self._admin_token()):
            return True
        self._send_json({"error": "unauthorized"}, status=401)
        return False

    # ---- routing ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path in ("/", "/index.html", "/dashboard.html"):
            return self._send_html_file(DASHBOARD_FILE,
                                        b"dashboard.html not found next to server.py")

        if path in ("/admin", "/admin.html"):
            return self._send_html_file(ADMIN_FILE_HTML,
                                        b"admin.html not found next to server.py")

        if path == "/health":
            return self._send_json({"status": "ok", "time": _now_iso()})

        if path == "/api/users":
            return self._send_json({"users": _list_users()})

        # ---- admin (auth required) ----
        if path == "/api/admin/coalide-config":
            if not self._require_admin():
                return
            return self._send_json(admin_api.get_config_state())

        if path == "/api/admin/words":
            if not self._require_admin():
                return
            return self._send_json(admin_api.get_words_state())

        if path == "/api/admin/server-env":
            if not self._require_admin():
                return
            return self._send_json(admin_api.get_server_env())

        if path == "/api/report/preview":
            settings = report.load_settings(HOST, PORT)
            text = report.build_report_text(all_records(), settings["url"])
            return self._send_json({"enabled": settings["enabled"],
                                    "report_time": settings["report_time"],
                                    "text": text})

        if path == "/api/stats":
            user = (qs.get("user") or [None])[0]
            if not user:
                users = _list_users()
                if not users:
                    return self._send_json({"error": "no data yet"}, status=404)
                user = users[0]["username"]  # most recently updated
            record = _load_record(user)
            if record is None:
                return self._send_json({"error": f"no data for '{user}'"}, status=404)
            return self._send_json(record)

        return self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/api/stats":
            return self._post_stats()
        if path == "/api/sync":
            return self._post_sync()
        if path == "/api/admin/login":
            return self._post_login()
        if path == "/api/admin/logout":
            admin_api.logout(self._admin_token())
            return self._send_json({"status": "ok"})
        if path == "/api/admin/coalide-config":
            return self._post_config()
        if path == "/api/admin/words":
            return self._post_words()
        if path == "/api/admin/server-env":
            return self._post_server_env()
        if path == "/api/report/send":
            return self._post_send_report()

        return self._send_json({"error": "not found"}, status=404)

    # ---- POST handlers ----
    def _post_stats(self):
        payload = self._read_json()
        if payload is None:
            return
        user = _safe_user(payload.get("username", "default"))
        record = {
            "username": user,
            "client_time": payload.get("client_time"),
            "updated_at": _now_iso(),
            "stats": payload.get("stats", {}),
        }
        try:
            _save_record(user, record)
        except Exception as e:
            return self._send_json({"error": f"could not store: {e}"}, status=500)
        return self._send_json({"status": "ok", "username": user,
                                "updated_at": record["updated_at"]}, status=201)

    def _post_sync(self):
        payload = self._read_json()
        if payload is None:
            return
        try:
            return self._send_json(admin_api.sync(payload))
        except Exception as e:
            return self._send_json({"error": f"sync failed: {e}"}, status=500)

    def _post_login(self):
        payload = self._read_json()
        if payload is None:
            return
        token, err = admin_api.login(payload.get("hash", ""))
        if token:
            return self._send_json({"token": token})
        status = 503 if err == "not_synced" else 401
        return self._send_json({"error": err}, status=status)

    def _post_config(self):
        if not self._require_admin():
            return
        payload = self._read_json()
        if payload is None:
            return
        try:
            rev = admin_api.save_config(payload.get("config"))
        except Exception as e:
            return self._send_json({"error": str(e)}, status=400)
        return self._send_json({"status": "ok", "rev": rev})

    def _post_words(self):
        if not self._require_admin():
            return
        payload = self._read_json()
        if payload is None:
            return
        action = payload.get("action")
        try:
            if action == "add":
                result = admin_api.add_word(payload.get("word") or {})
            elif action == "edit":
                result = admin_api.edit_word(int(payload.get("index", -1)),
                                             payload.get("word") or {})
            elif action == "delete":
                result = admin_api.delete_word(int(payload.get("index", -1)))
            else:
                return self._send_json({"error": "unknown action"}, status=400)
        except Exception as e:
            return self._send_json({"error": str(e)}, status=400)
        return self._send_json({"status": "ok", **result})

    def _post_server_env(self):
        if not self._require_admin():
            return
        payload = self._read_json()
        if payload is None:
            return
        try:
            admin_api.save_server_env(payload.get("env") or {})
        except Exception as e:
            return self._send_json({"error": str(e)}, status=400)
        return self._send_json({"status": "ok"})

    def _post_send_report(self):
        if not self._require_admin():
            return
        settings = report.load_settings(HOST, PORT)
        if not settings.get("enabled"):
            return self._send_json(
                {"error": "no_channel",
                 "detail": "Telegram/ntfy ayarlı değil."}, status=400)

        lines = []
        def log(msg):
            print(msg)
            lines.append(str(msg))

        channels = []
        if settings.get("telegram_enabled"):
            channels.append("Telegram")
        if settings.get("ntfy_enabled"):
            channels.append("ntfy")

        try:
            ok = report.run_report(all_records, settings, log=log)
        except Exception as e:
            return self._send_json({"error": "send_failed", "detail": str(e)},
                                   status=500)
        return self._send_json({"status": "ok" if ok else "partial",
                                "sent": ok, "channels": channels,
                                "log": lines})

    # Quieter, single-line access log.
    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} "
              f"{fmt % args}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    shown_host = HOST if HOST != "0.0.0.0" else "localhost"
    print("Coalide parental stats server")
    print(f"  Dashboard : http://{shown_host}:{PORT}/")
    print(f"  Admin     : http://{shown_host}:{PORT}/admin")
    print(f"  API       : http://{shown_host}:{PORT}/api/stats")
    print(f"  Data dir  : {DATA_DIR}")
    # Daily Telegram report scheduler — reloads settings each cycle, so .env
    # edits via the web admin take effect without a restart (no-op if unset).
    report.start_scheduler(all_records, lambda: report.load_settings(HOST, PORT))
    print("  Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    # Manual helpers for setup/testing:
    #   python server.py --report-preview   print the report text, don't send
    #   python server.py --send-report      send the report now via Telegram
    if "--report-preview" in sys.argv[1:]:
        st = report.load_settings(HOST, PORT)
        print(report.build_report_text(all_records(), st["url"]))
        sys.exit(0)
    if "--send-report" in sys.argv[1:]:
        st = report.load_settings(HOST, PORT)
        ok = report.run_report(all_records, st)
        sys.exit(0 if ok else 1)
    main()

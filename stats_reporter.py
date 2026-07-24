"""
Coalide — parental stats reporter (client side).

Pushes a snapshot of the local learning statistics to the parent-side web
dashboard / API (see the `serverside/` folder) so a parent can watch progress
remotely. The main program calls report_stats_async() when the menu opens, so
the dashboard always reflects the latest state.

Design goals (mirrors stats_menu.record_answer's "never break the app" rule):
  - Fully non-blocking: the push runs in a daemon thread with a short timeout.
  - Silent on failure: no server, offline, bad URL -> nothing happens, no crash.
  - Opt-in by configuration: does nothing until STATS_SERVER_URL is set to a
    real address (the placeholder default is ignored).

The payload is whatever stats_menu.build_stats() produces, run through a small
recursive JSON serializer so dates / Counters / tuples survive the trip. This
keeps the statistics logic in exactly one place (stats_menu) — the server and
dashboard just render what they are given.
"""

import json
import os
import threading
from collections import Counter
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_USER_FILE = os.path.join(BASE_DIR, "current_user.json")

# If STATS_SERVER_URL still contains one of these, treat it as "not configured"
# and skip reporting entirely (so the shipped placeholder never hits the wire).
_PLACEHOLDER_MARKERS = ("IP-TO-YOUR", "YOUR-PARENT-SERVER", "example.com")

_REQUEST_TIMEOUT = 4  # seconds — a parent server should answer fast or not at all


def _jsonable(obj):
    """Recursively convert build_stats() output into JSON-serializable data."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Counter):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)  # last-resort: never let an odd type break the push


def _current_username() -> str:
    """Read the logged-in username directly (no prompt, no heavy imports)."""
    try:
        with open(CURRENT_USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("username"):
            return str(data["username"])
    except Exception:
        pass
    return "default"


def _build_payload() -> dict:
    from stats_menu import build_stats  # local import: pulls textual, keep lazy
    stats = build_stats()
    return {
        "username": _current_username(),
        "client_time": datetime.now().isoformat(timespec="seconds"),
        "stats": _jsonable(stats),
    }


def _push() -> None:
    """Build and POST the stats snapshot. Swallows every error by design."""
    try:
        from utils import get_config, lg
    except Exception:
        return

    try:
        cfg = get_config()
        if not cfg.get("STATS_REPORTING_ENABLED", True):
            return

        url = str(cfg.get("STATS_SERVER_URL", "")).strip()
        if not url or any(marker in url for marker in _PLACEHOLDER_MARKERS):
            lg("stats_reporter: STATS_SERVER_URL not configured, skipping push.")
            return

        endpoint = url.rstrip("/") + "/api/stats"
        payload = _build_payload()

        import requests
        resp = requests.post(endpoint, json=payload, timeout=_REQUEST_TIMEOUT,
                             headers={"Content-Type": "application/json"})
        if resp.status_code in (200, 201):
            lg(f"stats_reporter: pushed stats for '{payload['username']}'.")
        else:
            lg(f"stats_reporter: server returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        # Never surface reporting failures to the learner — it's a background
        # convenience for the parent, not part of the quiz flow.
        try:
            lg(f"stats_reporter: push failed: {e}")
        except Exception:
            pass


def report_stats_async() -> threading.Thread:
    """Fire-and-forget the stats push on a daemon thread; returns the thread."""
    t = threading.Thread(target=_push, name="coalide-stats-reporter", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    # Manual test: build the payload and either print it or push it.
    import sys
    if "--push" in sys.argv[1:]:
        _push()
        print("Push attempted (see debug log with -debug for details).")
    else:
        print(json.dumps(_build_payload(), indent=2, ensure_ascii=False))

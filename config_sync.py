"""
Coalide — config & words sync (client side).

The parental stats server (see serverside/) runs on a DIFFERENT device, so it
cannot touch this machine's files directly. This module keeps them in sync over
HTTP: when the menu opens it pushes the current config.json / words.json and a
hash of ADMIN_PASSWORD to the server, then pulls back anything the parent has
changed through the web admin and applies it locally.

Mirrors stats_reporter.py's rules:
  - Runs on a daemon thread; never blocks the menu.
  - Silent on failure (offline, no server, placeholder URL -> nothing happens).
  - Opt-in: does nothing until STATS_SERVER_URL points at a real server.

Revision tracking: the server hands out an integer `rev` for config and words
that increases every time the parent edits them. We remember the last rev we
applied in .config_sync.json and only re-write local files when the server has
something newer — so a parent edit lands on the next menu open, and nothing is
overwritten needlessly.
"""

import hashlib
import json
import os
import threading
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
WORDS_FILE = os.path.join(BASE_DIR, "words.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")
SYNC_STATE_FILE = os.path.join(BASE_DIR, ".config_sync.json")

_PLACEHOLDER_MARKERS = ("IP-TO-YOUR", "YOUR-PARENT-SERVER", "example.com")
_REQUEST_TIMEOUT = 5


def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _save_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    os.replace(tmp, path)


def _admin_hash() -> str | None:
    """SHA-256 hex of ADMIN_PASSWORD (env first, then .env). None if unset."""
    pw = os.environ.get("ADMIN_PASSWORD")
    if not pw:
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ADMIN_PASSWORD=") and "=" in line:
                        pw = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except OSError:
            pass
    if not pw:
        return None
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


def _sync_state() -> dict:
    st = _load_json(SYNC_STATE_FILE, {})
    return st if isinstance(st, dict) else {}


def _reconcile_progress(words: list) -> None:
    """Drop progress entries for words the parent removed, so progress.json
    doesn't accumulate orphans after a server-side word deletion."""
    prog = _load_json(PROGRESS_FILE, None)
    if not isinstance(prog, dict):
        return
    targets = {w.get("target") for w in words if isinstance(w, dict)}
    pruned = {k: v for k, v in prog.items() if k in targets}
    if len(pruned) != len(prog):
        _save_json(PROGRESS_FILE, pruned)


def _backup_progress():
    """Copy progress.json to a timestamped .bak before a parent-queued bulk
    reset, so it stays recoverable. Best-effort; never raises."""
    if not os.path.exists(PROGRESS_FILE):
        return None
    try:
        import shutil
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = f"{PROGRESS_FILE}.{stamp}.bak"
        shutil.copy2(PROGRESS_FILE, backup)
        return backup
    except Exception:
        return None


def _apply_progress_resets(jobs: list) -> int:
    """Apply parent-queued reset jobs: remove every progress entry whose SM-2
    interval falls in a job's [lo, hi] range, sending those words back to 'not
    started'. Backs progress.json up first. Returns the number of entries removed."""
    prog = _load_json(PROGRESS_FILE, None)
    if not isinstance(prog, dict) or not prog:
        return 0
    remove = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        try:
            lo = float(job.get("lo", 0))
            hi = float(job.get("hi", 0))
        except (TypeError, ValueError):
            continue
        for target, entry in prog.items():
            if not isinstance(entry, dict):
                continue
            interval = entry.get("interval", 0)
            if not isinstance(interval, (int, float)):
                interval = 0
            if lo <= interval <= hi:
                remove.add(target)
    if not remove:
        return 0
    _backup_progress()
    pruned = {k: v for k, v in prog.items() if k not in remove}
    _save_json(PROGRESS_FILE, pruned)
    return len(remove)


def _push():
    try:
        from utils import get_config, lg
    except Exception:
        return
    try:
        cfg = get_config()
        if not cfg.get("CONFIG_SYNC_ENABLED", True):
            return
        url = str(cfg.get("STATS_SERVER_URL", "")).strip()
        if not url or any(m in url for m in _PLACEHOLDER_MARKERS):
            lg("config_sync: STATS_SERVER_URL not configured, skipping.")
            return

        state = _sync_state()
        payload = {
            "config": cfg,
            "words": _load_json(WORDS_FILE, []),
            "admin_hash": _admin_hash(),
            "applied_config_rev": state.get("config_rev", 0),
            "applied_words_rev": state.get("words_rev", 0),
            "applied_reset_rev": state.get("reset_rev", 0),
            "client_time": datetime.now().isoformat(timespec="seconds"),
        }

        import requests
        resp = requests.post(url.rstrip("/") + "/api/sync", json=payload,
                             timeout=_REQUEST_TIMEOUT,
                             headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            lg(f"config_sync: server returned {resp.status_code}: {resp.text[:200]}")
            return

        data = resp.json()
        new_state = dict(state)
        applied = []

        cfg_part = data.get("config") or {}
        if isinstance(cfg_part.get("data"), dict):
            # Overlay the parent's values onto the current local config rather
            # than replacing it, so a config key a newer Coalide added locally
            # (via repair_config) survives and isn't reset on every sync.
            merged = {**cfg, **cfg_part["data"]}
            _save_json(CONFIG_FILE, merged)
            new_state["config_rev"] = cfg_part.get("rev", state.get("config_rev", 0))
            applied.append("config")
        elif cfg_part.get("rev"):
            new_state["config_rev"] = cfg_part["rev"]

        words_part = data.get("words") or {}
        if isinstance(words_part.get("data"), list):
            _save_json(WORDS_FILE, words_part["data"])
            _reconcile_progress(words_part["data"])
            new_state["words_rev"] = words_part.get("rev", state.get("words_rev", 0))
            applied.append("words")
            try:
                from sm2 import reload_words
                reload_words()
            except Exception:
                pass
        elif words_part.get("rev"):
            new_state["words_rev"] = words_part["rev"]

        # Progress resets queued by the parent from the web admin. Apply any job
        # newer than what we've applied, then remember the server's rev so each
        # reset runs exactly once.
        reset_part = data.get("reset") or {}
        reset_jobs = reset_part.get("jobs") or []
        if isinstance(reset_jobs, list) and reset_jobs:
            removed = _apply_progress_resets(reset_jobs)
            new_state["reset_rev"] = reset_part.get("rev", state.get("reset_rev", 0))
            applied.append(f"reset({removed})")
            if removed:
                try:
                    from sm2 import reload_words
                    reload_words()
                except Exception:
                    pass
        elif reset_part.get("rev"):
            new_state["reset_rev"] = reset_part["rev"]

        if new_state != state:
            _save_json(SYNC_STATE_FILE, new_state)
        if applied:
            lg(f"config_sync: applied server changes -> {', '.join(applied)}.")
    except Exception as e:
        try:
            from utils import lg
            lg(f"config_sync: sync failed: {e}")
        except Exception:
            pass


def sync_config_async() -> threading.Thread:
    """Fire-and-forget config/words sync on a daemon thread."""
    t = threading.Thread(target=_push, name="coalide-config-sync", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    _push()
    print("Sync attempted (run with -debug in the app to see the log).")

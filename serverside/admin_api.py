"""
Coalide — admin & sync backend (server side).

The stats server runs on a DIFFERENT device than Coalide, so it has no direct
access to the child's config.json / words.json / .env. Instead everything flows
over HTTP:

  * The child app, when its menu opens, calls POST /api/sync — it pushes its
    current config + words + a hash of ADMIN_PASSWORD, and pulls back any
    changes the parent has made (by comparing revision numbers).
  * The parent edits the server-held authoritative copy through the web admin
    (/admin), gated behind the same admin password (verified against the hash
    the child synced — the plaintext password never reaches the server).

Authoritative state lives in DATA_DIR:
    coalide_config.json   {"rev", "updated_at", "data": {...}}
    coalide_words.json    {"rev", "updated_at", "data": [...]}
    admin.json            {"hash", "updated_at"}

The serverside's OWN .env (Telegram/report settings) is a real local file on
this device and is edited directly.

Stdlib only.
"""

import hmac
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone

from report import _parse_env_file  # reuse the tiny .env parser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "coalide_config.json")
WORDS_FILE = os.path.join(DATA_DIR, "coalide_words.json")
ADMIN_FILE = os.path.join(DATA_DIR, "admin.json")
SERVER_ENV = os.path.join(BASE_DIR, ".env")

SESSION_TTL = 2 * 3600  # seconds
_sessions = {}          # token -> expiry timestamp
_lock = threading.RLock()

WORD_TYPES = ["noun", "verb", "adjective", "adverb", "pronoun", "preposition", "other"]

# Parent-friendly descriptions for config.json keys (mirrors admin.py).
CONFIG_DESCRIPTIONS = {
    "Daily_New_Word_Cap": "Bir günde en fazla kaç yeni kelime tanıtılır.",
    "No_Repeat_Window": "Aynı kelime tekrar sorulmadan önce kaç soru geçmeli.",
    "Repo_Owner": "Güncellemelerin indirildiği GitHub kullanıcısı.",
    "Repo_Name": "Güncellemelerin indirildiği GitHub deposu.",
    "Update_Prereleases": "Ön sürüm (beta) güncellemeleri de yüklensin mi.",
    "Source_Language": "Kaynak dil (çocuğun bildiği dil).",
    "Target_Language": "Hedef dil (öğrenilen dil).",
    "BASE_RATE_PER_MINUTE": "1 dakika ekran süresinin taban kredi fiyatı.",
    "ESCALATION_PER_HOUR": "Aynı gün alınan her ek saatte fiyat artış oranı (0.5 = %50).",
    "SPAM_PROTECTION": "Art arda rastgele cevap yazmayı engelle.",
    "INPUT_TIMEOUT": "Cevap için süre sınırı, saniye (0 = kapalı).",
    "Credit_Reset_Weekly": "Krediler her Pazartesi sıfırlansın mı.",
    "BACKUP_PRONUNCIATIONS": "Telaffuz ses dosyalarını yedekle.",
    "KIOSK_MODE": "Kiosk modu: uygulama kapanınca otomatik yeniden açılır.",
    "BYPASS_SHORTCUTS": "Alt+Tab / Windows tuşu gibi kaçış kısayollarını engelle.",
    "Credit_Window_Start": "Kredi kazanmanın başladığı saat (SS:DD, örn. 07:00).",
    "Credit_Window_End": "Kredi kazanmanın bittiği saat (SS:DD, örn. 22:00).",
    "REQUIRE_INTERNET": "İnternet yoksa quiz başlatılmasın.",
    "STATS_REPORTING_ENABLED": "İstatistikleri veli sunucusuna gönder.",
    "STATS_SERVER_URL": "Veli sunucusunun adresi (istatistik ve senkronizasyon).",
    "CONFIG_SYNC_ENABLED": "Ayar/kelime değişikliklerini sunucudan çek ve uygula.",
}

# Keys the serverside .env editor surfaces with friendly labels (extras allowed).
SERVER_ENV_KEYS = [
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "NTFY_TOPIC", "NTFY_SERVER", "NTFY_TOKEN",
    "COALIDE_REPORT_TIME",
    "COALIDE_REPORT_ENABLED", "COALIDE_DASHBOARD_URL",
    "COALIDE_STATS_HOST", "COALIDE_STATS_PORT",
]
_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# --------------------------------------------------------------------------
# JSON store helpers
# --------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _save(path, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Sync (child <-> server)
# --------------------------------------------------------------------------

def sync(payload: dict) -> dict:
    """Handle a child's push/pull. Seeds authoritative state on first contact,
    stores the admin hash, and returns whatever the parent has since changed."""
    with _lock:
        resp = {}

        # Admin password hash — always refresh from the child (source of truth).
        h = payload.get("admin_hash")
        if isinstance(h, str) and h:
            _save(ADMIN_FILE, {"hash": h.lower(), "updated_at": _now()})

        # Config
        cfg = _load(CONFIG_FILE, None)
        if cfg is None and isinstance(payload.get("config"), dict):
            cfg = {"rev": 1, "updated_at": _now(), "data": payload["config"]}
            _save(CONFIG_FILE, cfg)
        if cfg is None:
            resp["config"] = {"rev": 0, "data": None}
        else:
            applied = _int(payload.get("applied_config_rev"))
            resp["config"] = {"rev": cfg["rev"],
                              "data": cfg["data"] if cfg["rev"] > applied else None}

        # Words
        w = _load(WORDS_FILE, None)
        if w is None and isinstance(payload.get("words"), list):
            w = {"rev": 1, "updated_at": _now(), "data": payload["words"]}
            _save(WORDS_FILE, w)
        if w is None:
            resp["words"] = {"rev": 0, "data": None}
        else:
            applied = _int(payload.get("applied_words_rev"))
            resp["words"] = {"rev": w["rev"],
                            "data": w["data"] if w["rev"] > applied else None}

        return resp


def _int(v) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------

def stored_admin_hash():
    a = _load(ADMIN_FILE, {})
    return a.get("hash") if isinstance(a, dict) else None


def login(received_hash: str):
    """Verify a hex SHA-256 of the admin password against the synced hash.
    Returns (token, None) on success or (None, reason)."""
    with _lock:
        stored = stored_admin_hash()
        if not stored:
            return None, "not_synced"
        if not received_hash or not hmac.compare_digest(
                str(received_hash).strip().lower(), str(stored).strip().lower()):
            return None, "bad_password"
        token = secrets.token_urlsafe(32)
        _sessions[token] = time.time() + SESSION_TTL
        return token, None


def valid_token(token: str) -> bool:
    if not token:
        return False
    with _lock:
        exp = _sessions.get(token)
        if not exp:
            return False
        if exp < time.time():
            _sessions.pop(token, None)
            return False
        _sessions[token] = time.time() + SESSION_TTL  # sliding expiry
        return True


def logout(token: str) -> None:
    with _lock:
        _sessions.pop(token, None)


# --------------------------------------------------------------------------
# Coalide config (authoritative, parent-editable)
# --------------------------------------------------------------------------

def get_config_state() -> dict:
    cfg = _load(CONFIG_FILE, None)
    return {
        "synced": cfg is not None,
        "rev": cfg["rev"] if cfg else 0,
        "updated_at": cfg["updated_at"] if cfg else None,
        "config": cfg["data"] if cfg else {},
        "descriptions": CONFIG_DESCRIPTIONS,
    }


def save_config(data: dict) -> int:
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    with _lock:
        cur = _load(CONFIG_FILE, None)
        rev = (cur["rev"] + 1) if cur else 1
        _save(CONFIG_FILE, {"rev": rev, "updated_at": _now(), "data": data})
        return rev


# --------------------------------------------------------------------------
# Coalide words (authoritative, parent-editable)
# --------------------------------------------------------------------------

def get_words_state() -> dict:
    w = _load(WORDS_FILE, None)
    return {"synced": w is not None, "rev": w["rev"] if w else 0,
            "words": w["data"] if w else []}


def _words_data():
    w = _load(WORDS_FILE, None)
    if w is None:
        raise ValueError("Kelime listesi henüz eşitlenmedi.")
    return w, list(w["data"] if isinstance(w.get("data"), list) else [])


def _bump_words(data: list) -> int:
    cur = _load(WORDS_FILE, None)
    rev = (cur["rev"] + 1) if cur else 1
    _save(WORDS_FILE, {"rev": rev, "updated_at": _now(), "data": data})
    return rev


def _norm_word(raw: dict, existing: dict | None = None) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("Geçersiz kelime verisi.")
    target = str(raw.get("target", "")).strip()
    if not target:
        raise ValueError("Hedef kelime boş olamaz.")
    source = raw.get("source")
    if isinstance(source, str):
        source = [p.strip() for p in source.split(",") if p.strip()]
    source = [str(x).strip() for x in (source or []) if str(x).strip()]
    if not source:
        raise ValueError("En az bir anlam girmelisiniz.")
    sentence = raw.get("sentence") or ["", ""]
    if not isinstance(sentence, (list, tuple)):
        sentence = ["", ""]
    s1 = str(sentence[0]) if len(sentence) > 0 else ""
    s2 = str(sentence[1]) if len(sentence) > 1 else ""
    return {
        "language": str(raw.get("language") or "en").strip() or "en",
        "word_type": str(raw.get("word_type") or "noun").strip().lower(),
        "sentence": [s1, s2],
        "target": target,
        "past": str(raw.get("past") or "").strip(),
        "v3": str(raw.get("v3") or "").strip(),
        "source": source,
        "next_review_date": (existing or {}).get("next_review_date"),
    }


def _is_dup(words: list, word: dict, skip: int | None = None) -> bool:
    for i, w in enumerate(words):
        if i == skip:
            continue
        if (str(w.get("target", "")).strip().lower() == word["target"].strip().lower()
                and w.get("language") == word["language"]):
            return True
    return False


def add_word(raw: dict) -> dict:
    with _lock:
        _, words = _words_data()
        word = _norm_word(raw)
        if _is_dup(words, word):
            raise ValueError(f"'{word['target']}' zaten kayıtlı.")
        words.append(word)
        rev = _bump_words(words)
        return {"rev": rev, "count": len(words), "target": word["target"]}


def edit_word(index: int, raw: dict) -> dict:
    with _lock:
        _, words = _words_data()
        if not (0 <= index < len(words)):
            raise ValueError("Geçersiz kelime seçimi.")
        word = _norm_word(raw, existing=words[index])
        if _is_dup(words, word, skip=index):
            raise ValueError(f"'{word['target']}' zaten kayıtlı.")
        words[index] = word
        rev = _bump_words(words)
        return {"rev": rev, "count": len(words), "target": word["target"]}


def delete_word(index: int) -> dict:
    with _lock:
        _, words = _words_data()
        if not (0 <= index < len(words)):
            raise ValueError("Geçersiz kelime seçimi.")
        target = words[index].get("target", "?")
        del words[index]
        rev = _bump_words(words)
        return {"rev": rev, "count": len(words), "target": target}


# --------------------------------------------------------------------------
# Serverside .env (this device's own report/Telegram settings)
# --------------------------------------------------------------------------

def get_server_env() -> dict:
    env = _parse_env_file(SERVER_ENV)
    return {"env": env, "known": SERVER_ENV_KEYS}


def save_server_env(mapping: dict) -> None:
    if not isinstance(mapping, dict):
        raise ValueError("env must be a JSON object")
    clean = {}
    for k, v in mapping.items():
        key = str(k).strip()
        if not _ENV_KEY_RE.match(key):
            raise ValueError(f"Geçersiz anahtar adı: {k!r}")
        clean[key] = str("" if v is None else v).replace("\n", " ").replace("\r", "")
    lines = ["# Coalide parental stats server configuration",
             "# Edited via the web admin. Restart the server to apply report changes.",
             ""]
    # Keep known keys first, in order, then any extras.
    for key in SERVER_ENV_KEYS:
        if key in clean:
            lines.append(f"{key}={clean.pop(key)}")
    for key, val in clean.items():
        lines.append(f"{key}={val}")
    tmp = SERVER_ENV + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, SERVER_ENV)

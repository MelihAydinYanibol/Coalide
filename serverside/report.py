"""
Coalide — daily Telegram report (server side).

Builds a text summary of every learner's stored stats and sends it to the
parent over Telegram, once a day at a configured time (midnight by default).
The dashboard URL is appended at the end so the parent can open the full view.

Zero dependencies — uses only the standard library (urllib for the Telegram
Bot API), so it ships inside `serverside/` without touching the main app's
requirements.

Configuration (environment variables, or a `.env` file next to server.py /
in its parent folder). Both the Telegram-style and Coalide-style names work:

    TELEGRAM_BOT_TOKEN / BOT_TOKEN     Telegram bot token
    TELEGRAM_CHAT_ID   / CHAT_ID       Chat/channel id to send to
    COALIDE_DASHBOARD_URL              Public dashboard URL (for the footer link)
    COALIDE_REPORT_TIME               "HH:MM" 24h local time, default "00:00"
    COALIDE_REPORT_ENABLED            "true"/"false"; defaults to on when a token
                                      and chat id are both present

The daily report is skipped silently when no token/chat is configured.
"""

import json
import os
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GUARD_FILE = os.path.join(BASE_DIR, "data", ".last_report")

TELEGRAM_MAX = 4096  # hard API limit on message length


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

def _parse_env_file(path: str) -> dict:
    env = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def _looks_like_placeholder(v: str) -> bool:
    if not v:
        return True
    bad = ("ENTER_YOUR_TOKEN", "YOUR_CHAT_ID", "YOUR_BOT_TOKEN", "YOUR-BOT-TOKEN",
           "IP-TO-YOUR", "YOUR-PARENT-SERVER")
    return v.startswith("[") or any(b in v for b in bad)


def load_settings(host: str, port: int) -> dict:
    """Resolve report settings from env vars, then a nearby .env, then defaults."""
    file_env = {}
    for p in (os.path.join(BASE_DIR, ".env"),
              os.path.join(os.path.dirname(BASE_DIR), ".env")):
        for k, v in _parse_env_file(p).items():
            file_env.setdefault(k, v)

    def get(*keys, default=None):
        for k in keys:
            if os.environ.get(k):
                return os.environ[k]
        for k in keys:
            if file_env.get(k):
                return file_env[k]
        return default

    token = get("TELEGRAM_BOT_TOKEN", "BOT_TOKEN")
    chat = get("TELEGRAM_CHAT_ID", "CHAT_ID")
    if _looks_like_placeholder(token):
        token = None
    if _looks_like_placeholder(chat):
        chat = None

    shown_host = host if host not in ("0.0.0.0", "") else "localhost"
    url = get("COALIDE_DASHBOARD_URL", default=f"http://{shown_host}:{port}/")
    report_time = get("COALIDE_REPORT_TIME", default="00:00").strip()
    try:
        hh, mm = report_time.split(":")
        report_time = f"{int(hh):02d}:{int(mm):02d}"
    except (ValueError, AttributeError):
        report_time = "00:00"

    enabled_raw = get("COALIDE_REPORT_ENABLED")
    if enabled_raw is None:
        enabled = bool(token and chat)
    else:
        enabled = enabled_raw.strip().lower() in ("1", "true", "yes", "on")

    return {
        "token": token,
        "chat": chat,
        "url": url,
        "report_time": report_time,
        "enabled": enabled and bool(token and chat),
    }


# --------------------------------------------------------------------------
# Report text
# --------------------------------------------------------------------------

def _esc(v) -> str:
    """Escape for Telegram HTML parse mode."""
    return (str("" if v is None else v)
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else round(f, 1)
    except (TypeError, ValueError):
        return 0


def _today_answers(stats: dict):
    """(correct, wrong, blank) from the last day of daily_answers."""
    da = stats.get("daily_answers") or []
    if not da:
        return 0, 0, 0
    parts = da[-1][1] if isinstance(da[-1], (list, tuple)) and len(da[-1]) > 1 else []
    def part(i):
        try:
            return _num(parts[i][0])
        except (IndexError, TypeError):
            return 0
    return part(0), part(1), part(2)


def build_report_text(records: list, dashboard_url: str) -> str:
    """Compose the full daily-report message from stored per-user records."""
    lines = ["📊 <b>Coalide Günlük Rapor</b>",
             f"🗓 {date.today().isoformat()}", ""]

    active = [r for r in records if isinstance(r, dict) and r.get("stats")]
    if not active:
        lines.append("Henüz hiçbir öğrenci için veri yok.")
    for rec in active:
        st = rec.get("stats") or {}
        name = rec.get("username", "?")
        tc, tw, tb = _today_answers(st)
        block = [
            f"👤 <b>{_esc(name)}</b>",
            f"🎯 Başarı: {_num(st.get('overall_rate'))}%  ·  💬 {_num(st.get('log_total'))} cevap",
            f"🔥 Seri: {_num(st.get('streak'))} gün  ·  "
            f"📚 {_num(st.get('started_count'))}/{_num(st.get('total_words'))} kelime "
            f"(🏆 {_num(st.get('mastered'))} öğrenilen)",
            f"✨ Bugün: +{_num(st.get('new_today'))} yeni kelime · "
            f"{tc + tw + tb} cevap ({tc}✓ {tw}✗ {tb}∅)",
            f"⏰ Tekrar bekleyen: {_num(st.get('due_now'))}",
            f"💵 Kredi: {_num(st.get('balance'))}  ·  "
            f"📺 Bugün ekran süresi: {_num(st.get('redeemed_today'))} dk",
            f"🪙 Bu hafta: +{_num(st.get('earned_week'))} kazanıldı / "
            f"−{_num(st.get('spent_week'))} harcandı",
        ]
        hardest = st.get("hardest") or []
        if hardest:
            hw = ", ".join(f"{_esc(h.get('word'))} (%{_num(h.get('rate'))})"
                           for h in hardest[:3])
            block.append(f"🧗 Zorlandığı kelimeler: {hw}")
        last = rec.get("client_time") or rec.get("updated_at")
        if last:
            block.append(f"<i>Son güncelleme: {_esc(last)}</i>")
        lines.append("\n".join(block))
        lines.append("")

    lines.append(f"🔗 Daha fazla bilgi: {dashboard_url}")
    text = "\n".join(lines)
    if len(text) > TELEGRAM_MAX - 40:
        text = text[:TELEGRAM_MAX - 60].rstrip() + "\n…\n🔗 " + dashboard_url
    return text


# --------------------------------------------------------------------------
# Sending
# --------------------------------------------------------------------------

def send_telegram(text: str, token: str, chat_id: str) -> tuple:
    """Send `text` to Telegram. Returns (ok: bool, detail: str)."""
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    try:
        req = urllib.request.Request(api, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "replace")
            ok = resp.status == 200 and '"ok":true' in body.replace(" ", "")
            return ok, body[:300]
    except Exception as e:
        return False, str(e)


def run_report(records_provider, settings: dict, log=print) -> bool:
    """Build and send the report now. Returns True on success."""
    if not settings.get("enabled"):
        log("Report skipped: Telegram not configured.")
        return False
    records = records_provider() or []
    text = build_report_text(records, settings["url"])
    ok, detail = send_telegram(text, settings["token"], settings["chat"])
    if ok:
        log(f"Daily report sent to Telegram chat {settings['chat']}.")
    else:
        log(f"Daily report FAILED to send: {detail}")
    return ok


# --------------------------------------------------------------------------
# Scheduler
# --------------------------------------------------------------------------

def _read_guard() -> str:
    try:
        with open(GUARD_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _write_guard(day: str) -> None:
    try:
        os.makedirs(os.path.dirname(GUARD_FILE), exist_ok=True)
        with open(GUARD_FILE, "w", encoding="utf-8") as f:
            f.write(day)
    except OSError:
        pass


def start_scheduler(records_provider, settings_loader, log=print) -> None:
    """Start a daemon thread that sends the report once per day.

    `settings_loader` is a no-arg callable returning fresh settings, so changes
    made through the web admin's .env editor take effect without a restart.

    Fires at the first check that is at or after `report_time` on a day the
    report hasn't been sent yet — so a report still goes out even if the
    machine was asleep at the exact minute (e.g. midnight)."""

    def loop():
        while True:
            try:
                settings = settings_loader()
                if settings.get("enabled"):
                    now = datetime.now()
                    today = now.date().isoformat()
                    if _read_guard() != today and now.strftime("%H:%M") >= settings["report_time"]:
                        run_report(records_provider, settings, log)
                        _write_guard(today)  # once per day, success or not
            except Exception as e:
                log(f"Report scheduler error: {e}")
            time.sleep(30)

    threading.Thread(target=loop, name="coalide-daily-report", daemon=True).start()
    log("Daily Telegram report scheduler started (checks every 30s).")

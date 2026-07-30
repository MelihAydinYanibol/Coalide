"""
Per-user credit tracking for the web app.

A web-safe port of the terminal app's credit/reward loop
(``objects/balance_obj.py``). Correct answers earn credits; credits can be
"redeemed" for minutes of screen time with the same escalating pricing and
weekly-reset rules. The one deliberate difference from the terminal app: there
is no PCV2 parental-control server call here — a web deployment can't reach a
device on the family LAN — so redemption records the grant locally and returns
success. The pricing, caps and weekly-reset behaviour are otherwise identical.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time, timedelta

from engine import DATA_DIR, get_config, _safe_username

MINUTES_PER_DAY = 24 * 60


# --------------------------------------------------------------------------- #
# Credit-earning window                                                        #
# --------------------------------------------------------------------------- #

def _parse_time(value: str, fallback: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return datetime.strptime(fallback, "%H:%M").time()


def is_within_credit_window(now: time | None = None) -> bool:
    cfg = get_config()
    start = _parse_time(cfg.get("Credit_Window_Start", "07:00"), "07:00")
    end = _parse_time(cfg.get("Credit_Window_End", "22:00"), "22:00")
    current = now if now is not None else datetime.now().time()
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


# --------------------------------------------------------------------------- #
# Persistence                                                                  #
# --------------------------------------------------------------------------- #

def _data_path(username: str) -> str:
    return os.path.join(DATA_DIR, f"{_safe_username(username)}_data.json")


def load_user(username: str) -> dict:
    path = _data_path(username)
    if not os.path.exists(path):
        data = {"username": username, "balance": 0, "redeemed_minutes_by_date": {}, "last_reset_date": None}
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {"username": username, "balance": 0, "redeemed_minutes_by_date": {}, "last_reset_date": None}
    data.setdefault("balance", 0)
    data.setdefault("redeemed_minutes_by_date", {})
    data.setdefault("last_reset_date", None)
    return data


def save_user(data: dict) -> None:
    with open(_data_path(data["username"]), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --------------------------------------------------------------------------- #
# Weekly reset                                                                 #
# --------------------------------------------------------------------------- #

def check_weekly_reset(data: dict) -> bool:
    """Reset balance to 0 if a new week (Monday 00:00) has started since last reset."""
    if not get_config().get("Credit_Reset_Weekly", True):
        return False
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    last_reset = date.fromisoformat(data["last_reset_date"]) if data.get("last_reset_date") else date.min
    if last_reset < week_start:
        data["balance"] = 0
        data["last_reset_date"] = week_start.isoformat()
        save_user(data)
        return True
    return False


# --------------------------------------------------------------------------- #
# Earning / pricing / redemption                                              #
# --------------------------------------------------------------------------- #

def award_credits(username: str) -> dict:
    """
    Award credits for a correct answer if we're inside the earning window.
    Returns ``{"awarded": int, "balance": int, "in_window": bool}``.
    """
    cfg = get_config()
    amount = cfg.get("CREDITS_PER_CORRECT", 7)
    data = load_user(username)
    check_weekly_reset(data)
    in_window = is_within_credit_window()
    if in_window:
        data["balance"] += amount
        save_user(data)
    return {"awarded": amount if in_window else 0, "balance": data["balance"], "in_window": in_window}


def cost_for_minutes(data: dict, requested_minutes: int, target_date: str) -> int:
    """Escalating cost: each hour already redeemed for ``target_date`` makes the next hour pricier."""
    cfg = get_config()
    base = cfg.get("BASE_RATE_PER_MINUTE", 5)
    escalation = cfg.get("ESCALATION_PER_HOUR", 0.5)
    already = data["redeemed_minutes_by_date"].get(target_date, 0)
    total = 0.0
    for m in range(requested_minutes):
        hour_bracket = (already + m) // 60
        total += base * (1 + escalation * hour_bracket)
    return round(total)


def redeem(username: str, requested_minutes: int, target_date: str) -> dict:
    """
    Redeem credits for screen-time minutes. Enforces the same rules as the
    terminal app: no past dates, no banking past the weekly reset, and a hard
    24h/day cap. Records the redemption locally (no PCV2 call in the web app).
    """
    data = load_user(username)
    check_weekly_reset(data)

    try:
        tgt = date.fromisoformat(target_date)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Geçersiz tarih."}

    if tgt < date.today():
        return {"ok": False, "error": "Geçmiş bir tarih için süre alınamaz."}

    if requested_minutes <= 0:
        return {"ok": False, "error": "Lütfen pozitif bir dakika sayısı girin."}

    if get_config().get("Credit_Reset_Weekly", True):
        week_end = date.today() + timedelta(days=6 - date.today().weekday())
        if tgt > week_end:
            return {"ok": False, "error": f"Krediler her pazartesi sıfırlanır; en geç {week_end.isoformat()} için süre alabilirsiniz."}

    already = data["redeemed_minutes_by_date"].get(target_date, 0)
    if already + requested_minutes > MINUTES_PER_DAY:
        remaining = MINUTES_PER_DAY - already
        return {"ok": False, "error": f"Bir gün en fazla {MINUTES_PER_DAY} dakikadır; bu tarih için en fazla {remaining} dakika daha alabilirsiniz."}

    cost = cost_for_minutes(data, requested_minutes, target_date)
    if data["balance"] < cost:
        return {"ok": False, "error": f"Yeterli krediniz yok. Gereken: {cost}, mevcut: {data['balance']}."}

    data["balance"] -= cost
    data["redeemed_minutes_by_date"][target_date] = already + requested_minutes
    save_user(data)
    return {"ok": True, "cost": cost, "minutes": requested_minutes, "date": target_date, "balance": data["balance"]}

"""
Per-user statistics for the web app — a web-safe port of the terminal app's
``stats_menu.build_stats()`` (and its ``record_answer`` answer log).

The terminal app logs every answer to a single global ``statistics.csv`` and
derives its rich İstatistikler screen from that log plus ``progress.json`` and
``<user>_data.json``. This module does the same thing per-user:

    answer log   ->  webapp/data/<user>_stats.csv   (datetime,word,result)
    progress     ->  webapp/data/<user>_progress.json
    credits      ->  webapp/data/<user>_data.json

``build_stats(username)`` returns the same set of figures the terminal screen
shows, JSON-serialised (dates as ISO strings, colours as semantic tokens the
front end maps to CSS), so the web dashboard can render all five terminal tabs.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta

import engine

STATS_SUFFIX = "_stats.csv"

MATURE_INTERVAL = 21  # days; an SM-2 interval this long counts as "learned/mastered"
MINUTES_PER_DAY = 24 * 60

# Colour tokens (the front end maps these to CSS variables).
M, R, Y, P, G = "muted", "red", "yellow", "purple", "green"

TR_MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


# --------------------------------------------------------------------------- #
# Answer log (<user>_stats.csv)                                                #
# --------------------------------------------------------------------------- #

def _log_path(username: str) -> str:
    return os.path.join(engine.DATA_DIR, f"{engine._safe_username(username)}{STATS_SUFFIX}")


def record_answer(username: str, word: str, result) -> None:
    """
    Append one answered question to the user's stats log. ``result`` is
    True (correct) / False (wrong) / None (blank). Never raises — a logging
    failure must not break the quiz.
    """
    try:
        res = "correct" if result is True else "wrong" if result is False else "blank"
        path = _log_path(username)
        is_new = not os.path.exists(path)
        with open(path, "a", encoding="utf-8") as f:
            if is_new:
                f.write("datetime,word,result\n")
            f.write(f"{datetime.now().isoformat(timespec='seconds')},{word},{res}\n")
    except Exception:
        pass


def load_log(username: str) -> list:
    """Read <user>_stats.csv -> list of (date, word, result) tuples."""
    rows = []
    path = _log_path(username)
    if not os.path.exists(path):
        return rows
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3 or parts[0].startswith("datetime"):
                    continue
                d = _parse_date(parts[0][:10])
                if d is None:
                    continue
                rows.append((d, parts[1], parts[2]))
    except Exception:
        pass
    return rows


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _parse_date(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _day_label(d: date) -> str:
    return f"{d.day} {TR_MONTHS[d.month - 1]}"


def _iso(d):
    return d.isoformat() if d else None


def _cost_for_minutes(minutes: int, base: float, esc: float, already: int = 0) -> int:
    total = 0.0
    for m in range(minutes):
        total += base * (1 + esc * ((already + m) // 60))
    return round(total)


def _max_redeemable(balance: int, base: float, esc: float, already: int = 0) -> int:
    minutes = 0
    total = 0.0
    while already + minutes < MINUTES_PER_DAY:
        rate = base * (1 + esc * ((already + minutes) // 60))
        if round(total + rate) > balance:
            break
        total += rate
        minutes += 1
    return minutes


# --------------------------------------------------------------------------- #
# build_stats                                                                  #
# --------------------------------------------------------------------------- #

def build_stats(username: str) -> dict:
    today = date.today()
    progress = engine.load_progress(username)
    words = engine._read_json_list(engine.WORDS_FILE)
    log = load_log(username)
    cfg = engine.get_config(username)
    from credits import load_user
    user = load_user(username)

    credits_per_correct = cfg.get("CREDITS_PER_CORRECT", 7)
    base_rate = cfg.get("BASE_RATE_PER_MINUTE", 5)
    escalation = cfg.get("ESCALATION_PER_HOUR", 0.5)
    weekly_reset = cfg.get("Credit_Reset_Weekly", True)

    # ---- per-word state ----
    started = []
    for target, p in progress.items():
        if not isinstance(p, dict):
            continue
        attempts = p.get("last_ten_attempts") or []
        total = len(attempts) or p.get("total_attempts", 0)
        correct = p.get("correct_attempts", 0)
        wrong = p.get("wrong_attempts", 0)
        blank = p.get("blank_attempts", 0)
        started.append({
            "word": target,
            "rate": (correct / total * 100) if total else 0.0,
            "total": total, "correct": correct, "wrong": wrong, "blank": blank,
            "repetitions": p.get("repetitions", 0),
            "ease": p.get("ease_factor", 2.5),
            "interval": p.get("interval", 0),
            "first": _parse_date(p.get("first_review_date")),
            "last": _parse_date(p.get("last_review_date")),
            "next": _parse_date(p.get("next_review_date")),
        })

    total_words = len(words)
    started_count = len(started)
    not_started = max(0, total_words - started_count)
    mastered = sum(1 for e in started if e["interval"] >= MATURE_INTERVAL)

    # ---- maturity buckets ----
    buckets = [
        {"label": "Başlanmadı", "value": not_started, "color": M},
        {"label": "Yeni (≤1 gün)", "value": sum(1 for e in started if e["interval"] <= 1), "color": R},
        {"label": "Öğreniliyor (2-6g)", "value": sum(1 for e in started if 2 <= e["interval"] <= 6), "color": Y},
        {"label": "Genç (1-3 hafta)", "value": sum(1 for e in started if 7 <= e["interval"] < MATURE_INTERVAL), "color": P},
        {"label": "Olgun (3h-2 ay)", "value": sum(1 for e in started if MATURE_INTERVAL <= e["interval"] < 60), "color": G},
        {"label": "Usta (2 ay+)", "value": sum(1 for e in started if e["interval"] >= 60), "color": G},
    ]

    # ---- new words per day / week ----
    new_dates = [e["first"] for e in started if e["first"]]
    new_by_day = Counter(new_dates)
    new_today = new_by_day.get(today, 0)
    ws0 = _week_start(today)

    weekly_new = []
    for i in range(7, -1, -1):
        ws = ws0 - timedelta(weeks=i)
        cnt = sum(1 for d in new_dates if ws <= d < ws + timedelta(days=7))
        label = f"{_day_label(ws)} +" if ws != ws0 else "Bu hafta"
        weekly_new.append({"label": label, "value": cnt, "color": G if cnt else M})

    daily_new = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        cnt = new_by_day.get(d, 0)
        daily_new.append({"label": _day_label(d), "value": cnt, "color": P if cnt else M})

    # ---- answers from the log ----
    answers_by_day = {}
    for d, _w, res in log:
        answers_by_day.setdefault(d, Counter())[res] += 1
    log_totals = Counter(res for _d, _w, res in log)

    daily_answers = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = answers_by_day.get(d, Counter())
        daily_answers.append({"label": _day_label(d), "parts": [
            {"value": c.get("correct", 0), "color": G},
            {"value": c.get("wrong", 0), "color": R},
            {"value": c.get("blank", 0), "color": Y},
        ]})

    spark_30 = [sum(answers_by_day.get(today - timedelta(days=i), Counter()).values())
                for i in range(29, -1, -1)]
    spark_new_30 = [new_by_day.get(today - timedelta(days=i), 0) for i in range(29, -1, -1)]

    # ---- streak ----
    active_days = set(answers_by_day)
    for e in started:
        for k in ("first", "last"):
            if e[k]:
                active_days.add(e[k])
    streak = 0
    d = today if today in active_days else today - timedelta(days=1)
    while d in active_days:
        streak += 1
        d -= timedelta(days=1)

    # ---- all-time ----
    log_total = sum(log_totals.values())
    son10 = Counter()
    for e in started:
        son10["correct"] += e["correct"]
        son10["wrong"] += e["wrong"]
        son10["blank"] += e["blank"]
    son10_total = sum(son10.values())

    if log_total:
        overall_rate = log_totals.get("correct", 0) / log_total * 100
    elif son10_total:
        overall_rate = son10["correct"] / son10_total * 100
    else:
        overall_rate = 0.0

    best_day = max(answers_by_day.items(), key=lambda kv: sum(kv[1].values()), default=None)
    first_log = min((d for d, _w, _r in log), default=None)

    # ---- review forecast ----
    overdue = sum(1 for e in started if e["next"] and e["next"] < today)
    forecast = [{"label": "Gecikmiş", "value": overdue, "color": R}]
    for i in range(14):
        d = today + timedelta(days=i)
        cnt = sum(1 for e in started if e["next"] == d)
        label = "Bugün" if i == 0 else "Yarın" if i == 1 else _day_label(d)
        forecast.append({"label": label, "value": cnt, "color": Y if i == 0 else (P if cnt else M)})

    # ---- SM-2 health ----
    eases = [e["ease"] for e in started]
    intervals = [e["interval"] for e in started]
    longest = max(started, key=lambda e: e["interval"], default=None)
    sm2 = None
    if eases:
        sm2 = {
            "ef_avg": round(sum(eases) / len(eases), 2),
            "ef_min": round(min(eases), 2),
            "ef_max": round(max(eases), 2),
            "interval_avg": round(sum(intervals) / len(intervals)),
            "longest_word": longest["word"] if longest else None,
            "longest_interval": longest["interval"] if longest else 0,
        }

    # ---- hardest words / table ----
    attempted = [e for e in started if e["total"] > 0]
    hardest = sorted(attempted, key=lambda e: (e["rate"], -e["wrong"]))[:5]
    table_rows = sorted(started, key=lambda e: (e["rate"], -e["wrong"]))

    def _word_row(e):
        return {
            "word": e["word"], "rate": round(e["rate"], 1), "total": e["total"],
            "correct": e["correct"], "wrong": e["wrong"], "blank": e["blank"],
            "repetitions": e["repetitions"], "interval": e["interval"],
            "next": _iso(e["next"]),
            "delta": (e["next"] - today).days if e["next"] else None,
        }

    # ---- word types ----
    word_types_ctr = Counter((w.get("word_type") or "?").strip().lower() or "?"
                             for w in words if isinstance(w, dict))
    word_types = [{"label": t, "value": c, "color": P} for t, c in word_types_ctr.most_common()]

    # ---- screen time / credits ----
    balance = user.get("balance") if isinstance(user.get("balance"), (int, float)) else 0
    redeemed = {}
    for k, v in (user.get("redeemed_minutes_by_date") or {}).items():
        pd = _parse_date(k)
        if pd and isinstance(v, (int, float)):
            redeemed[pd] = v

    redeemed_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        m = redeemed.get(d, 0)
        redeemed_14.append({"label": _day_label(d), "value": m, "color": Y if m else M})

    redeemed_weekly = []
    for i in range(7, -1, -1):
        ws = ws0 - timedelta(weeks=i)
        m = sum(v for d, v in redeemed.items() if ws <= d < ws + timedelta(days=7))
        label = f"{_day_label(ws)} +" if ws != ws0 else "Bu hafta"
        redeemed_weekly.append({"label": label, "value": m, "color": G if m else M})

    spent_by_day = {d: _cost_for_minutes(int(m), base_rate, escalation) for d, m in redeemed.items()}
    spent_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = spent_by_day.get(d, 0)
        spent_14.append({"label": _day_label(d), "value": c, "color": R if c else M})

    earned_by_day = {d: c.get("correct", 0) * credits_per_correct for d, c in answers_by_day.items()}
    earned_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = earned_by_day.get(d, 0)
        earned_14.append({"label": _day_label(d), "value": c, "color": G if c else M})

    earned_week = sum(v for d, v in earned_by_day.items() if d >= ws0)
    spent_week = sum(v for d, v in spent_by_day.items() if d >= ws0)
    minutes_week = sum(v for d, v in redeemed.items() if d >= ws0)

    redeemed_today = int(redeemed.get(today, 0))
    redeemed_tomorrow = int(redeemed.get(today + timedelta(days=1), 0))
    max_today = _max_redeemable(balance, base_rate, escalation, redeemed_today)
    max_tomorrow = _max_redeemable(balance, base_rate, escalation, redeemed_tomorrow)
    current_rate = base_rate * (1 + escalation * (redeemed_today // 60))
    price_brackets = [{"hour": h + 1, "rate": base_rate * (1 + escalation * h),
                       "current": h == redeemed_today // 60} for h in range(4)]
    days_to_reset = (7 - today.weekday()) if weekly_reset else None
    spark_minutes_30 = [redeemed.get(today - timedelta(days=i), 0) for i in range(29, -1, -1)]

    return {
        "today": _iso(today),
        "total_words": total_words,
        "started_count": started_count,
        "mastered": mastered,
        "new_today": new_today,
        "due_now": overdue + sum(1 for e in started if e["next"] == today),
        "streak": streak,
        "buckets": buckets,
        "weekly_new": weekly_new,
        "daily_new": daily_new,
        "daily_answers": daily_answers,
        "spark_30": spark_30,
        "spark_new_30": spark_new_30,
        "log_totals": dict(log_totals),
        "log_total": log_total,
        "son10": dict(son10),
        "son10_total": son10_total,
        "overall_rate": round(overall_rate, 1),
        "best_day": {"label": _day_label(best_day[0]), "count": sum(best_day[1].values())} if best_day else None,
        "first_log": _iso(first_log),
        "active_day_count": len(answers_by_day),
        "avg_per_active_day": round(log_total / len(answers_by_day), 1) if answers_by_day else 0,
        "forecast": forecast,
        "sm2": sm2,
        "hardest": [_word_row(e) for e in hardest],
        "table_rows": [_word_row(e) for e in table_rows],
        "word_types": word_types,
        "credits_per_correct": credits_per_correct,
        "balance": balance,
        "redeemed_14": redeemed_14,
        "redeemed_total": sum(redeemed.values()),
        "redeemed_weekly": redeemed_weekly,
        "spent_14": spent_14,
        "spent_total": sum(spent_by_day.values()),
        "earned_14": earned_14,
        "earned_total": sum(earned_by_day.values()),
        "earned_week": earned_week,
        "spent_week": spent_week,
        "minutes_week": minutes_week,
        "redeemed_today": redeemed_today,
        "redeemed_tomorrow": redeemed_tomorrow,
        "max_today": max_today,
        "max_tomorrow": max_tomorrow,
        "current_rate": current_rate,
        "price_brackets": price_brackets,
        "base_rate": base_rate,
        "escalation": escalation,
        "days_to_reset": days_to_reset,
        "spark_minutes_30": spark_minutes_30,
    }

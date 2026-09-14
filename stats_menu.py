"""
Coalide — İstatistik Ekranı

A Textual TUI showing detailed learning statistics:
  - Overview tiles (words started/mastered, streak, credits, success rate...)
  - Weekly/daily "new words learned" bar charts (from progress.json
    first_review_date)
  - Daily answers (correct/wrong/blank) charts + all-time totals, read from
    statistics.csv — a per-answer log this module also writes via
    record_answer(), which new_master.py calls after every evaluated answer.
  - Per-word table (hardest first), upcoming review forecast, SM-2 health.
  - Time & speed: daily study time against DAILY_COALIDE_TIME_LIMIT, answer-speed
    histogram, time per result, slowest/fastest words, time-of-day activity and
    a per-direction breakdown — all read from the statistics.csv time_spent /
    direction columns.

Run standalone:  python stats_menu.py
From the menu:   the "İstatistikler" button launches it as a subprocess.
"""

import csv
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
WORDS_FILE = os.path.join(BASE_DIR, "words.json")
STATS_LOG = os.path.join(BASE_DIR, "statistics.csv")
CURRENT_USER_FILE = os.path.join(BASE_DIR, "current_user.json")

TR_MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

# Palette — matches menu.py
BG = "#0f0f1a"
PANEL_BG = "#16162a"
PURPLE = "#7c5cff"
GREEN = "#42d6a4"
YELLOW = "#f5c542"
RED = "#ff6b81"
MUTED = "#9a9ac0"

MATURE_INTERVAL = 21  # days; a word with an SM-2 interval this long counts as "learned"
CREDITS_PER_CORRECT = 7  # mirrors user.add_credits(7) in new_master.py
MINUTES_PER_DAY = 24 * 60

# Answer-speed histogram: [lower, upper) bounds in seconds; the last bin is open.
SPEED_BINS = [(0, 3, "0-3 sn"), (3, 6, "3-6 sn"), (6, 10, "6-10 sn"),
              (10, 20, "10-20 sn"), (20, 30, "20-30 sn"), (30, None, "30+ sn")]
HOUR_BLOCK = 3  # hours per bar in the time-of-day chart (24 bars is too tall here)
# A word needs this many timed answers before its average is worth ranking; with
# fewer timed answers than that anywhere, the ranking falls back to every word.
MIN_TIMED_ANSWERS = 2


# --------------------------------------------------------------------------
# Answer log (statistics.csv) — stdlib only, safe to import from new_master
# --------------------------------------------------------------------------

LOG_HEADER = ["datetime", "word", "result", "given", "expected", "prompt", "direction", "time_spent"]
ANSWER_LOG_DAYS = 30  # how far back the per-answer detail is kept in build_stats()


def _flat(v) -> str:
    """A list of accepted meanings -> one displayable string."""
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v)


def record_answer(word: str, result, given=None, expected=None,
                  prompt=None, direction=None, time_spent=None) -> None:
    """
    Append one answered question to statistics.csv.

    :param word: the target word that was asked.
    :param result: True (correct), False (wrong) or None (left blank).
    :param given: what the child actually typed.
    :param expected: the accepted answer(s) for the question.
    :param prompt: the text the child was shown.
    :param direction: "target" if the target word was wanted, else "source".
    :param time_spent: seconds spent on the question, as a float.

    The four detail columns were added after the first release, and time_spent
    after that, so rows written by an older build only have the first three
    (or first seven); readers must tolerate all three shapes.
    Written through csv so a comma inside a word or an answer cannot shift the
    columns. Never raises — a stats logging failure must not break the quiz.
    """
    try:
        res = "correct" if result is True else "wrong" if result is False else "blank"
        is_new = not os.path.exists(STATS_LOG)
        with open(STATS_LOG, "a", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(LOG_HEADER)
            w.writerow([datetime.now().isoformat(timespec="seconds"), word, res,
                        _flat(given), _flat(expected), _flat(prompt),
                        _flat(direction),
                        f"{time_spent:.2f}" if isinstance(time_spent, (int, float)) else ""])
    except Exception:
        pass


# --------------------------------------------------------------------------
# Data loading & aggregation
# --------------------------------------------------------------------------

def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _parse_date(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def read_log_rows() -> list:
    """
    Read statistics.csv -> list of dicts, one per answered question.

    Rows written before the detail columns existed simply come back with empty
    given/expected/prompt/direction.
    """
    rows = []
    if not os.path.exists(STATS_LOG):
        return rows
    try:
        with open(STATS_LOG, "r", encoding="utf-8", newline="") as f:
            for parts in csv.reader(f):
                if len(parts) < 3 or parts[0].startswith("datetime"):
                    continue
                d = _parse_date(parts[0][:10])
                if d is None:
                    continue
                col = lambda i: parts[i].strip() if len(parts) > i else ""
                try:
                    time_spent = float(col(7)) if col(7) != "" else None
                except ValueError:
                    time_spent = None
                rows.append({
                    "date": d,
                    "time": parts[0][11:16],
                    "word": parts[1],
                    "result": parts[2],
                    "given": col(3),
                    "expected": col(4),
                    "prompt": col(5),
                    "direction": col(6),
                    "time_spent": time_spent,
                })
    except Exception:
        pass
    return rows


def load_log() -> list:
    """Read statistics.csv -> list of (date, word, result) tuples."""
    return [(r["date"], r["word"], r["result"]) for r in read_log_rows()]


def load_user_data() -> dict:
    """Read <username>_data.json directly (no prompts, no heavy imports)."""
    cu = _load_json(CURRENT_USER_FILE, {})
    username = cu.get("username") if isinstance(cu, dict) else None
    if not username:
        return {}
    data = _load_json(os.path.join(BASE_DIR, f"{username}_data.json"), {})
    return data if isinstance(data, dict) else {}


def _load_config() -> dict:
    """config.json as a dict — read directly to avoid importing utils/balance_obj
    (which pull in the parental-control API)."""
    cfg = _load_json(os.path.join(BASE_DIR, "config.json"), {})
    return cfg if isinstance(cfg, dict) else {}


def _load_credit_config() -> tuple:
    """(base_rate, escalation, weekly_reset) from config.json."""
    cfg = _load_config()
    return (cfg.get("BASE_RATE_PER_MINUTE", 5),
            cfg.get("ESCALATION_PER_HOUR", 0.5),
            cfg.get("Credit_Reset_Weekly", True))


def _load_daily_time_limit() -> int:
    """DAILY_COALIDE_TIME_LIMIT in seconds (0 = off), sanitised."""
    try:
        return max(0, int(_load_config().get("DAILY_COALIDE_TIME_LIMIT", 0) or 0))
    except (TypeError, ValueError):
        return 0


def _load_languages() -> tuple:
    """(source_language, target_language) — used to label question directions."""
    cfg = _load_config()
    return (str(cfg.get("Source_Language", "Türkçe")),
            str(cfg.get("Target_Language", "İngilizce")))


def _fmt_duration(seconds) -> str:
    """Seconds -> a compact Turkish duration: "2 sa 5 dk", "3 dk 20 sn", "45 sn"."""
    try:
        total = int(round(max(0.0, float(seconds or 0))))
    except (TypeError, ValueError):
        return "0 sn"
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} sa {minutes} dk" if minutes else f"{hours} sa"
    if minutes:
        return f"{minutes} dk {secs} sn" if secs else f"{minutes} dk"
    return f"{secs} sn"


def _cost_for_minutes(minutes: int, base: float, esc: float, already: int = 0) -> int:
    """Credit cost of `minutes` of screen time for one date, given `already`
    minutes redeemed for that date. Same escalating formula as
    balance_obj.User.cost_for_minutes — order within a day doesn't matter,
    so a date's total spend can be reconstructed exactly from its minutes."""
    total = 0.0
    for m in range(minutes):
        hour_bracket = (already + m) // 60
        total += base * (1 + esc * hour_bracket)
    return round(total)


def _max_redeemable(balance: int, base: float, esc: float, already: int = 0) -> int:
    """Largest number of minutes affordable with `balance` for a date that
    already has `already` minutes redeemed (mirrors balance_obj)."""
    minutes = 0
    total = 0.0
    while already + minutes < MINUTES_PER_DAY:
        rate = base * (1 + esc * ((already + minutes) // 60))
        if round(total + rate) > balance:
            break
        total += rate
        minutes += 1
    return minutes


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _day_label(d: date) -> str:
    return f"{d.day} {TR_MONTHS[d.month - 1]}"


def build_stats() -> dict:
    today = date.today()
    progress = _load_json(PROGRESS_FILE, {})
    words = _load_json(WORDS_FILE, [])
    if not isinstance(words, list):
        words = []
    log_rows = read_log_rows()
    log = [(r["date"], r["word"], r["result"]) for r in log_rows]
    user = load_user_data()

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

    # ---- maturity buckets (Anki-style) ----
    buckets = [
        ("Başlanmadı", not_started, MUTED),
        ("Yeni  (≤1 gün)", sum(1 for e in started if e["interval"] <= 1), RED),
        ("Öğreniliyor (2-6g)", sum(1 for e in started if 2 <= e["interval"] <= 6), YELLOW),
        ("Genç  (1-3 hafta)", sum(1 for e in started if 7 <= e["interval"] < MATURE_INTERVAL), PURPLE),
        ("Olgun (3h - 2 ay)", sum(1 for e in started if MATURE_INTERVAL <= e["interval"] < 60), GREEN),
        ("Usta  (2 ay +)", sum(1 for e in started if e["interval"] >= 60), GREEN),
    ]

    # ---- new words per day / per week ----
    new_dates = [e["first"] for e in started if e["first"]]
    new_by_day = Counter(new_dates)
    new_today = new_by_day.get(today, 0)

    weekly_new = []
    ws0 = _week_start(today)
    for i in range(7, -1, -1):
        ws = ws0 - timedelta(weeks=i)
        cnt = sum(1 for d in new_dates if ws <= d < ws + timedelta(days=7))
        label = f"{_day_label(ws)} +" if ws != ws0 else "Bu hafta"
        weekly_new.append((label, cnt, GREEN if cnt else MUTED))

    daily_new = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        cnt = new_by_day.get(d, 0)
        daily_new.append((_day_label(d), cnt, PURPLE if cnt else MUTED))

    # ---- answers from the log ----
    answers_by_day = {}
    for d, _w, res in log:
        answers_by_day.setdefault(d, Counter())[res] += 1
    log_totals = Counter(res for _d, _w, res in log)

    daily_answers = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = answers_by_day.get(d, Counter())
        daily_answers.append((_day_label(d), [
            (c.get("correct", 0), GREEN),
            (c.get("wrong", 0), RED),
            (c.get("blank", 0), YELLOW),
        ]))

    spark_30 = [sum(answers_by_day.get(today - timedelta(days=i), Counter()).values())
                for i in range(29, -1, -1)]
    spark_new_30 = [new_by_day.get(today - timedelta(days=i), 0)
                    for i in range(29, -1, -1)]

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
    forecast = [("Gecikmiş", overdue, RED)]
    for i in range(14):
        d = today + timedelta(days=i)
        cnt = sum(1 for e in started if e["next"] == d)
        label = "Bugün" if i == 0 else "Yarın" if i == 1 else _day_label(d)
        forecast.append((label, cnt, YELLOW if i == 0 else PURPLE if cnt else MUTED))

    # ---- SM-2 health ----
    eases = [e["ease"] for e in started]
    intervals = [e["interval"] for e in started]
    longest = max(started, key=lambda e: e["interval"], default=None)

    # ---- hardest words / table ----
    attempted = [e for e in started if e["total"] > 0]
    hardest = sorted(attempted, key=lambda e: (e["rate"], -e["wrong"]))[:5]
    table_rows = sorted(started, key=lambda e: (e["rate"], -e["wrong"]))

    # ---- answers per day, whole history (the parent dashboard's "Genel
    #      Başarı" widget sums these for any chosen window) ----
    answers_by_date = {
        d.isoformat(): [c.get("correct", 0), c.get("wrong", 0), c.get("blank", 0)]
        for d, c in sorted(answers_by_day.items())
    }

    # ---- per-answer detail (recent days only; the parent dashboard's
    #      "Cevap Günlüğü" widget reads this) ----
    log_cutoff = today - timedelta(days=ANSWER_LOG_DAYS - 1)
    answer_log = [
        {"date": r["date"], "time": r["time"], "word": r["word"],
         "result": r["result"], "given": r["given"], "expected": r["expected"],
         "prompt": r["prompt"], "direction": r["direction"]}
        for r in log_rows if r["date"] >= log_cutoff
    ]

    # ---- word types ----
    word_types = Counter((w.get("word_type") or "?").strip().lower() or "?"
                         for w in words if isinstance(w, dict))

    # ---- screen time / credits ----
    base_rate, escalation, weekly_reset = _load_credit_config()
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
        redeemed_14.append((_day_label(d), m, YELLOW if m else MUTED))

    # minutes redeemed per week (8 weeks) — history only spans ~60 days
    # because balance_obj garbage-collects older redemption entries
    redeemed_weekly = []
    for i in range(7, -1, -1):
        ws = ws0 - timedelta(weeks=i)
        m = sum(v for d, v in redeemed.items() if ws <= d < ws + timedelta(days=7))
        label = f"{_day_label(ws)} +" if ws != ws0 else "Bu hafta"
        redeemed_weekly.append((label, m, GREEN if m else MUTED))

    # exact credits spent per day, reconstructed from redeemed minutes
    spent_by_day = {d: _cost_for_minutes(int(m), base_rate, escalation)
                    for d, m in redeemed.items()}
    spent_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = spent_by_day.get(d, 0)
        spent_14.append((_day_label(d), c, RED if c else MUTED))

    # estimated credits earned per day (correct answers × 7, from the log)
    earned_by_day = {d: c.get("correct", 0) * CREDITS_PER_CORRECT
                     for d, c in answers_by_day.items()}
    earned_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = earned_by_day.get(d, 0)
        earned_14.append((_day_label(d), c, GREEN if c else MUTED))

    week_start_d = ws0
    earned_week = sum(v for d, v in earned_by_day.items() if d >= week_start_d)
    spent_week = sum(v for d, v in spent_by_day.items() if d >= week_start_d)
    minutes_week = sum(v for d, v in redeemed.items() if d >= week_start_d)

    redeemed_today = int(redeemed.get(today, 0))
    redeemed_tomorrow = int(redeemed.get(today + timedelta(days=1), 0))
    max_today = _max_redeemable(balance, base_rate, escalation, redeemed_today)
    max_tomorrow = _max_redeemable(balance, base_rate, escalation, redeemed_tomorrow)
    current_rate = base_rate * (1 + escalation * (redeemed_today // 60))
    price_brackets = [(h, base_rate * (1 + escalation * h)) for h in range(4)]
    days_to_reset = 7 - today.weekday() if weekly_reset else None

    spark_minutes_30 = [redeemed.get(today - timedelta(days=i), 0)
                        for i in range(29, -1, -1)]

    # Full per-day series (whole retained history), keyed by ISO date. The
    # dashboard sums/slices these for its per-widget time-window pickers, the
    # same way "answers_by_date" already backs the Genel Başarı window. Older
    # dashboards simply ignore keys they don't know.
    new_by_date = {d.isoformat(): c for d, c in new_by_day.items()}
    earned_by_date = {d.isoformat(): c for d, c in earned_by_day.items()}
    spent_by_date = {d.isoformat(): c for d, c in spent_by_day.items()}
    minutes_by_date = {d.isoformat(): int(m) for d, m in redeemed.items()}

    # ---- time spent answering -------------------------------------------
    # Every answer's duration has been logged since 2.3.3 (statistics.csv's
    # time_spent column). Rows from older builds have no duration at all, so
    # they are left out of every figure here rather than counted as zero
    # seconds — which would understate a total and drag an average down.
    timed_rows = [r for r in log_rows if isinstance(r["time_spent"], (int, float))]
    seconds_by_day, timed_by_day = {}, Counter()
    for r in timed_rows:
        seconds_by_day[r["date"]] = seconds_by_day.get(r["date"], 0.0) + r["time_spent"]
        timed_by_day[r["date"]] += 1

    timed_count = len(timed_rows)
    time_today = seconds_by_day.get(today, 0.0)
    time_week = sum(v for d, v in seconds_by_day.items() if d >= ws0)
    time_total = sum(seconds_by_day.values())
    time_avg = time_total / timed_count if timed_count else 0.0
    timed_today = timed_by_day.get(today, 0)
    time_avg_today = time_today / timed_today if timed_today else 0.0
    sec_7 = sum(seconds_by_day.get(today - timedelta(days=i), 0.0) for i in range(7))
    cnt_7 = sum(timed_by_day.get(today - timedelta(days=i), 0) for i in range(7))
    time_avg_7 = sec_7 / cnt_7 if cnt_7 else 0.0
    time_best_day = max(seconds_by_day.items(), key=lambda kv: kv[1], default=None)

    # daily budget (DAILY_COALIDE_TIME_LIMIT, 0 = off)
    daily_time_limit = _load_daily_time_limit()
    time_remaining = max(0.0, daily_time_limit - time_today) if daily_time_limit else 0.0
    limit_used_pct = (min(100.0, time_today / daily_time_limit * 100)
                      if daily_time_limit else 0.0)
    # How many more questions the remaining budget is worth at the current
    # pace -- the same projection the main menu shows under "Kalan Süre".
    # Today's average is the honest pace, but at the start of a day nothing
    # is logged yet, so fall back to the all-time average rather than
    # showing nothing.
    pace_seconds = time_avg_today or time_avg
    questions_left = (int(time_remaining / pace_seconds)
                      if daily_time_limit and pace_seconds else 0)

    time_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        mins = round(seconds_by_day.get(d, 0.0) / 60, 1)
        time_14.append((_day_label(d), mins, PURPLE if mins else MUTED))
    spark_time_30 = [round(seconds_by_day.get(today - timedelta(days=i), 0.0) / 60)
                     for i in range(29, -1, -1)]

    # answer-speed histogram
    speed_buckets = []
    for lo, hi, label in SPEED_BINS:
        cnt = sum(1 for r in timed_rows
                  if r["time_spent"] >= lo and (hi is None or r["time_spent"] < hi))
        speed_buckets.append((label, cnt, PURPLE if cnt else MUTED))
    sorted_times = sorted(r["time_spent"] for r in timed_rows)
    time_median = sorted_times[timed_count // 2] if timed_count else 0.0
    time_fastest = sorted_times[0] if timed_count else 0.0
    time_slowest = sorted_times[-1] if timed_count else 0.0

    # how long a correct / wrong / blank answer takes on average
    time_by_result = {}
    for key in ("correct", "wrong", "blank"):
        vals = [r["time_spent"] for r in timed_rows if r["result"] == key]
        time_by_result[key] = {"avg": (sum(vals) / len(vals)) if vals else 0.0,
                               "count": len(vals), "total": sum(vals)}

    # slowest / fastest words. A single timed answer says very little, so rank
    # on words with a couple of them — unless nothing qualifies yet, in which
    # case rank everything so the panel isn't empty on day one.
    per_word = {}
    for r in timed_rows:
        e = per_word.setdefault(r["word"], [0.0, 0])
        e[0] += r["time_spent"]
        e[1] += 1
    word_speed = [{"word": w, "avg": t / n, "count": n}
                  for w, (t, n) in per_word.items() if n >= MIN_TIMED_ANSWERS]
    if not word_speed:
        word_speed = [{"word": w, "avg": t / n, "count": n}
                      for w, (t, n) in per_word.items()]
    slowest_words = sorted(word_speed, key=lambda e: -e["avg"])[:5]
    fastest_words = sorted(word_speed, key=lambda e: e["avg"])[:5]

    # time-of-day activity, from the clock time each answer was logged at
    hourly = [[h, 0, 0, 0] for h in range(24)]
    res_idx = {"correct": 1, "wrong": 2, "blank": 3}
    for r in log_rows:
        idx = res_idx.get(r["result"])
        if idx is None:
            continue
        try:
            hour = int(r["time"][:2])
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23:
            hourly[hour][idx] += 1
    hour_blocks = []
    for start in range(0, 24, HOUR_BLOCK):
        cnt = sum(sum(hourly[h][1:]) for h in range(start, start + HOUR_BLOCK))
        hour_blocks.append((f"{start:02d}-{start + HOUR_BLOCK:02d}", cnt,
                            YELLOW if cnt else MUTED))
    busiest_hour = max(range(24), key=lambda h: sum(hourly[h][1:]))
    if not sum(hourly[busiest_hour][1:]):
        busiest_hour = None

    # question direction — which way round the question was asked (logged
    # since 2.3.0): was the target-language word wanted, or the source one?
    src_lang, tgt_lang = _load_languages()
    direction_stats = []
    for key, label in (("target", f"{src_lang} → {tgt_lang}"),
                       ("source", f"{tgt_lang} → {src_lang}")):
        rows_d = [r for r in log_rows if r["direction"] == key]
        counts = Counter(r["result"] for r in rows_d)
        tot = len(rows_d)
        times = [r["time_spent"] for r in rows_d
                 if isinstance(r["time_spent"], (int, float))]
        direction_stats.append({
            "key": key, "label": label, "total": tot,
            "correct": counts.get("correct", 0), "wrong": counts.get("wrong", 0),
            "blank": counts.get("blank", 0),
            "rate": (counts.get("correct", 0) / tot * 100) if tot else 0.0,
            "avg_time": (sum(times) / len(times)) if times else 0.0,
        })

    # efficiency — both figures use timed answers only, so they stay consistent
    minutes_spent = time_total / 60
    answers_per_minute = timed_count / minutes_spent if minutes_spent else 0.0
    credits_per_minute = (time_by_result["correct"]["count"] * CREDITS_PER_CORRECT
                          / minutes_spent) if minutes_spent else 0.0

    seconds_by_date = {d.isoformat(): round(v, 2) for d, v in seconds_by_day.items()}
    timed_by_date = {d.isoformat(): c for d, c in timed_by_day.items()}

    return {
        "today": today,
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
        "log_totals": log_totals,
        "log_total": log_total,
        "son10": son10,
        "son10_total": son10_total,
        "overall_rate": overall_rate,
        "best_day": best_day,
        "first_log": first_log,
        "active_day_count": len(answers_by_day),
        "forecast": forecast,
        "eases": eases,
        "intervals": intervals,
        "longest": longest,
        "hardest": hardest,
        "table_rows": table_rows,
        "answers_by_date": answers_by_date,
        "new_by_date": new_by_date,
        "earned_by_date": earned_by_date,
        "spent_by_date": spent_by_date,
        "minutes_by_date": minutes_by_date,
        "answer_log": answer_log,
        "answer_log_days": ANSWER_LOG_DAYS,
        "word_types": word_types,
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
        "last_reset": _parse_date(user.get("last_reset_date")),
        "spark_minutes_30": spark_minutes_30,
        # ---- time & speed (statistics.csv time_spent / direction) ----
        "timed_count": timed_count,
        "time_today": time_today,
        "time_week": time_week,
        "time_total": time_total,
        "time_avg": time_avg,
        "time_avg_today": time_avg_today,
        "time_avg_7": time_avg_7,
        "time_median": time_median,
        "time_fastest": time_fastest,
        "time_slowest": time_slowest,
        "time_best_day": time_best_day,
        "daily_time_limit": daily_time_limit,
        "time_remaining": time_remaining,
        "limit_used_pct": limit_used_pct,
        "pace_seconds": pace_seconds,
        "questions_left": questions_left,
        "time_14": time_14,
        "spark_time_30": spark_time_30,
        "seconds_by_date": seconds_by_date,
        "timed_by_date": timed_by_date,
        "speed_buckets": speed_buckets,
        "time_by_result": time_by_result,
        "slowest_words": slowest_words,
        "fastest_words": fastest_words,
        "hourly": hourly,
        "hour_blocks": hour_blocks,
        "busiest_hour": busiest_hour,
        "direction_stats": direction_stats,
        "answers_per_minute": answers_per_minute,
        "credits_per_minute": credits_per_minute,
        "min_timed_answers": MIN_TIMED_ANSWERS,
    }


# --------------------------------------------------------------------------
# Chart rendering (Rich markup strings)
# --------------------------------------------------------------------------

_PARTIALS = " ▏▎▍▌▋▊▉"


def _bar(width_cells: float, max_width: int) -> str:
    full = int(width_cells)
    frac = width_cells - full
    bar = "█" * min(full, max_width)
    if full < max_width and frac >= 1 / 8:
        bar += _PARTIALS[int(frac * 8)]
    return bar


def hbar_chart(rows, width: int = 30, label_w: int = 10) -> str:
    """rows: list of (label, value, color) -> horizontal bar chart markup."""
    vmax = max((v for _l, v, _c in rows), default=0)
    lines = []
    for label, v, color in rows:
        w = 0 if vmax == 0 else v / vmax * width
        bar = _bar(w, width)
        if v > 0 and not bar:
            bar = "▏"
        lines.append(f"[{MUTED}]{label:<{label_w}}[/] [{color}]{bar}[/] [bold]{v}[/]")
    return "\n".join(lines) if lines else f"[dim]Henüz veri yok.[/]"


def stacked_chart(rows, width: int = 28, label_w: int = 8) -> str:
    """rows: list of (label, [(value, color), ...]) -> stacked bar chart."""
    vmax = max((sum(v for v, _c in parts) for _l, parts in rows), default=0)
    lines = []
    for label, parts in rows:
        total = sum(v for v, _c in parts)
        segs, detail = "", []
        if total and vmax:
            bar_w = round(total / vmax * width)
            prev = cum = 0
            for v, color in parts:
                if v <= 0:
                    continue
                cum += v
                edge = round(cum / total * bar_w)
                if edge > prev:
                    segs += f"[{color}]{'█' * (edge - prev)}[/]"
                prev = edge
        for (v, color), sym in zip(parts, ("✓", "✗", "∅")):
            if v:
                detail.append(f"[{color}]{v}{sym}[/]")
        tail = f" [bold]{total}[/] " + " ".join(detail) if total else f" [dim]0[/]"
        lines.append(f"[{MUTED}]{label:<{label_w}}[/] {segs}{tail}")
    return "\n".join(lines) if lines else "[dim]Henüz veri yok.[/]"


def rate_color(rate: float) -> str:
    return GREEN if rate >= 80 else YELLOW if rate >= 50 else RED


# --------------------------------------------------------------------------
# Textual UI
# --------------------------------------------------------------------------

from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import (Button, DataTable, Digits, Footer, Header,
                             Sparkline, Static, TabbedContent, TabPane)


# Maturity filter for the word table: (key, label, lo, hi) with lo/hi inclusive
# SM-2 interval bounds. "all" (lo=None) shows every started word; the other rows
# mirror the stats maturity buckets (MATURE_INTERVAL=21). Not-started words have
# no progress row, so they never appear in this (started-word) table.
WORD_FILTERS = [
    ("all", "Tümü", None, None),
    ("new", "Yeni", 0, 1),
    ("learning", "Öğreniliyor", 2, 6),
    ("young", "Genç", 7, 20),
    ("mature", "Olgun", 21, 59),
    ("master", "Usta", 60, float("inf")),
]


def _word_filter_count(rows, lo, hi) -> int:
    """How many started words fall in a filter's [lo, hi] range ("all" = every)."""
    if lo is None:
        return len(rows)
    return sum(1 for e in rows if lo <= e["interval"] <= hi)


class WordTable(DataTable):
    """All tracked words, hardest first. Populated on mount so a recompose
    (refresh) rebuilds it with fresh data. Supports an in-place maturity filter
    (set_range) so the parent can narrow the list to one SM-2 bucket."""

    def __init__(self, rows, today, lo=None, hi=None):
        super().__init__(id="word-table")
        self._all_rows = rows
        self._today = today
        self._lo = lo
        self._hi = hi

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Kelime", "Başarı", "✓", "✗", "∅",
                         "Tekrar", "Aralık", "Sonraki Tekrar")
        self._repopulate()

    def filtered_rows(self) -> list:
        if self._lo is None:
            return self._all_rows
        return [e for e in self._all_rows if self._lo <= e["interval"] <= self._hi]

    def set_range(self, lo, hi) -> int:
        """Apply a maturity filter and rebuild the rows. Returns the row count."""
        self._lo, self._hi = lo, hi
        return self._repopulate()

    def _repopulate(self) -> int:
        self.clear()  # keeps the columns, drops the rows
        rows = self.filtered_rows()
        for e in rows:
            rc = rate_color(e["rate"])
            if e["next"]:
                delta = (e["next"] - self._today).days
                nxt = Text(f"{e['next'].isoformat()}  ({delta:+d}g)",
                           style=RED if delta <= 0 else MUTED)
            else:
                nxt = Text("—", style=MUTED)
            self.add_row(
                Text(e["word"], style="bold"),
                Text(f"%{e['rate']:.0f}", style=f"bold {rc}") if e["total"]
                else Text("—", style=MUTED),
                Text(str(e["correct"]), style=GREEN),
                Text(str(e["wrong"]), style=RED),
                Text(str(e["blank"]), style=YELLOW),
                Text(str(e["repetitions"])),
                Text(f"{e['interval']}g"),
                nxt,
            )
        return len(rows)


class StatsApp(App):
    """Coalide statistics TUI."""

    TITLE = "Coalide — İstatistikler"
    BINDINGS = [
        Binding("q,escape", "quit", "Çıkış"),
        Binding("r", "refresh_stats", "Yenile"),
    ]

    CSS = f"""
    Screen {{ background: {BG}; }}
    Header {{ background: #1a1a2e; }}
    TabbedContent {{ height: 1fr; }}
    .tab-body {{ padding: 1 2; }}

    .tiles {{
        grid-size: 3;
        grid-gutter: 1 2;
        grid-rows: auto;
        height: auto;
        margin-bottom: 1;
    }}
    .tile {{
        background: {PANEL_BG};
        padding: 0 1;
        height: auto;
        align: center middle;
    }}
    .tile-label {{ width: 100%; text-align: center; color: {MUTED}; text-style: bold; }}
    .tile Digits {{ width: auto; }}
    .t-purple {{ border: round {PURPLE}; }}  .t-purple Digits {{ color: {PURPLE}; }}
    .t-green  {{ border: round {GREEN}; }}   .t-green Digits  {{ color: {GREEN}; }}
    .t-yellow {{ border: round {YELLOW}; }}  .t-yellow Digits {{ color: {YELLOW}; }}
    .t-red    {{ border: round {RED}; }}     .t-red Digits    {{ color: {RED}; }}

    .panel {{
        background: {PANEL_BG};
        padding: 1 2;
        margin-bottom: 1;
        height: auto;
        color: #e0e0f0;
    }}
    .p-purple {{ border: round {PURPLE}; }}
    .p-green  {{ border: round {GREEN}; }}
    .p-yellow {{ border: round {YELLOW}; }}
    .p-red    {{ border: round {RED}; }}

    Sparkline {{ height: 2; margin-top: 1; }}
    Sparkline > .sparkline--max-color {{ color: {GREEN}; }}
    Sparkline > .sparkline--min-color {{ color: #2a2a4a; }}

    #word-table-title {{ height: auto; margin-bottom: 1; }}
    #word-table {{ height: 1fr; background: {PANEL_BG}; }}

    #word-filter {{ height: auto; margin-bottom: 1; }}
    #word-filter Button {{ margin-right: 1; min-width: 6; }}
    #word-filter Button.active {{
        background: {PURPLE};
        color: {BG};
        text-style: bold;
    }}
    """

    # Which maturity bucket the word table is filtered to; persists across the
    # 'r' refresh (recompose) since the App instance is reused. See WORD_FILTERS.
    _word_filter_key = "all"

    # ---- composition ----------------------------------------------------

    def compose(self) -> ComposeResult:
        s = build_stats()
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("📊 Genel Bakış", id="tab-genel"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._genel(s)
            with TabPane("💰 Krediler", id="tab-kredi"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._krediler(s)
            with TabPane("📅 Haftalık & Günlük", id="tab-hafta"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._haftalik(s)
            with TabPane("⏱ Süre & Hız", id="tab-sure"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._sure(s)
            with TabPane("🔤 Kelimeler", id="tab-kelime"):
                with Vertical(classes="tab-body"):
                    yield from self._kelimeler(s)
            with TabPane("🔮 Gelecek & SM-2", id="tab-gelecek"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._gelecek(s)
        yield Footer(show_command_palette=False)

    @staticmethod
    def _panel(title: str, body: str, accent_class: str, accent: str) -> Static:
        return Static(f"[bold {accent}]{title}[/]\n\n{body}",
                      classes=f"panel {accent_class}")

    @staticmethod
    def _tile_grid(tiles, grid_id: str | None = None) -> ComposeResult:
        with Grid(id=grid_id, classes="tiles"):
            for label, value, klass in tiles:
                with Vertical(classes=f"tile {klass}"):
                    yield Static(label, classes="tile-label")
                    yield Digits(str(value))

    def _genel(self, s) -> ComposeResult:
        balance = s["balance"]
        tiles = [
            ("📚 Toplam Kelime", s["total_words"], "t-purple"),
            ("🚀 Başlanan", s["started_count"], "t-green"),
            (f"🏆 Öğrenilen ({MATURE_INTERVAL}g+)", s["mastered"], "t-yellow"),
            ("✨ Bugün Yeni", s["new_today"], "t-green"),
            ("⏰ Tekrar Bekleyen", s["due_now"], "t-red"),
            ("🔥 Seri (gün)", s["streak"], "t-yellow"),
            ("💬 Toplam Cevap", s["log_total"] or s["son10_total"], "t-purple"),
            ("🎯 Başarı (%)", round(s["overall_rate"]), "t-green"),
            ("💵 Kredi", balance, "t-yellow"),
        ]
        yield from self._tile_grid(tiles, grid_id="tiles")

        yield self._panel("📦 Kelime Durumu (SM-2 olgunluk)",
                          hbar_chart(s["buckets"], label_w=20),
                          "p-purple", PURPLE)

        if s["hardest"]:
            lines = []
            for e in s["hardest"]:
                rc = rate_color(e["rate"])
                lines.append(
                    f"[bold]{escape(e['word']):<16}[/] [{rc}]%{e['rate']:.0f}[/]  "
                    f"([{GREEN}]{e['correct']}✓[/] [{RED}]{e['wrong']}✗[/] "
                    f"[{YELLOW}]{e['blank']}∅[/])"
                )
            yield self._panel("🧗 En Zor 5 Kelime", "\n".join(lines), "p-red", RED)

        yield self._panel("♾️ Tüm Zamanlar", self._alltime_text(s), "p-green", GREEN)

    @staticmethod
    def _alltime_text(s) -> str:
        lt = s["log_totals"]
        lines = []
        if s["log_total"]:
            lines.append(
                f"Toplam cevap: [bold]{s['log_total']}[/]  "
                f"([{GREEN}]{lt.get('correct', 0)}✓[/] [{RED}]{lt.get('wrong', 0)}✗[/] "
                f"[{YELLOW}]{lt.get('blank', 0)}∅[/])"
            )
            lines.append(f"Genel başarı: [bold {rate_color(s['overall_rate'])}]"
                         f"%{s['overall_rate']:.1f}[/]")
            lines.append(f"Çalışılan gün: [bold]{s['active_day_count']}[/]")
            if s["best_day"]:
                d, c = s["best_day"]
                lines.append(f"En yoğun gün: [bold]{_day_label(d)}[/] "
                             f"({sum(c.values())} cevap)")
            if s["active_day_count"]:
                avg = s["log_total"] / s["active_day_count"]
                lines.append(f"Aktif gün ortalaması: [bold]{avg:.1f}[/] cevap")
            if s["first_log"]:
                lines.append(f"Kayıt başlangıcı: [bold]{s['first_log'].isoformat()}[/]")
        if s["timed_count"]:
            lines.append(f"Soru başında geçen toplam süre: "
                         f"[bold]{_fmt_duration(s['time_total'])}[/] "
                         f"[{MUTED}]({s['timed_count']} cevap)[/]")
            lines.append(f"Ortalama cevap süresi: [bold]{s['time_avg']:.1f} sn[/]")
        else:
            lines.append(f"[{MUTED}]Cevap geçmişi bu sürümle kaydedilmeye başlandı — "
                         f"quiz çözdükçe burada birikecek.[/]")
        s10 = s["son10"]
        lines.append("")
        lines.append(
            f"[{MUTED}]Kelime bazlı (son 10 pencere):[/] "
            f"[{GREEN}]{s10['correct']}✓[/] [{RED}]{s10['wrong']}✗[/] "
            f"[{YELLOW}]{s10['blank']}∅[/]  (toplam {s['son10_total']})"
        )
        return "\n".join(lines)

    def _krediler(self, s) -> ComposeResult:
        tiles = [
            ("💵 Bakiye", s["balance"], "t-yellow"),
            ("⏱ Alınabilir (dk, bugün)", s["max_today"], "t-green"),
            ("📺 Bugün Alınan (dk)", s["redeemed_today"], "t-purple"),
            ("🪙 Bu Hafta Kazanılan", s["earned_week"], "t-green"),
            ("💸 Bu Hafta Harcanan", s["spent_week"], "t-red"),
            ("🗓 Sıfırlamaya Kalan (gün)",
             s["days_to_reset"] if s["days_to_reset"] is not None else 0, "t-red"),
        ]
        yield from self._tile_grid(tiles)

        body = hbar_chart(s["earned_14"], label_w=8)
        body += (f"\n\n[{MUTED}]Her doğru cevap = [bold {GREEN}]"
                 f"{CREDITS_PER_CORRECT} kredi[/].  Kayıtlı toplam kazanç:[/] "
                 f"[bold {GREEN}]{s['earned_total']} kredi[/]")
        if not s["log_total"]:
            body += (f"\n[{MUTED}]Cevap geçmişi bu sürümle kaydedilmeye başlandı — "
                     f"kazançlar quiz çözdükçe görünecek.[/]")
        yield self._panel("🪙 Kazanılan Krediler (son 14 gün)", body, "p-green", GREEN)

        body = hbar_chart(s["spent_14"], label_w=8)
        body += (f"\n\n[{MUTED}]Alınan dakikalardan birebir hesaplanır. "
                 f"Toplam harcama (son 60 gün):[/] "
                 f"[bold {RED}]{s['spent_total']} kredi[/]")
        yield self._panel("💸 Harcanan Krediler (son 14 gün)", body, "p-red", RED)

        body = hbar_chart(s["redeemed_14"], label_w=8)
        body += "\n\n" + hbar_chart(s["redeemed_weekly"], label_w=10)
        body += (f"\n\n[{MUTED}]Bu hafta:[/] [bold {YELLOW}]{s['minutes_week']} dk[/]"
                 f"   [{MUTED}]Toplam (son 60 gün):[/] "
                 f"[bold {YELLOW}]{s['redeemed_total']} dk[/]")
        yield self._panel("📺 Alınan Ekran Süresi — günlük (14 gün) ve haftalık (8 hafta)",
                          body, "p-yellow", YELLOW)

        lines = []
        for h, rate in s["price_brackets"]:
            marker = f"  [bold {YELLOW}]◀ şu an[/]" if h == s["redeemed_today"] // 60 else ""
            lines.append(f"{h + 1}. saat: [bold]{rate:g} kredi/dk[/]{marker}")
        lines.append("")
        lines.append(f"Şu anki dakika fiyatı: [bold {YELLOW}]{s['current_rate']:g} kredi[/]"
                     f"  [{MUTED}](bugün {s['redeemed_today']} dk alındığı için)[/]")
        lines.append(f"Bakiyenle alınabilir: [bold {GREEN}]{s['max_today']} dk (bugün)[/]"
                     f" | [bold {GREEN}]{s['max_tomorrow']} dk (yarın)[/]")
        mins_per_correct = CREDITS_PER_CORRECT / s["base_rate"] if s["base_rate"] else 0
        lines.append(f"1 doğru cevap ≈ [bold]{mins_per_correct:.1f} dk[/] ekran süresi"
                     f"  [{MUTED}](taban fiyattan)[/]")
        if s["days_to_reset"] is not None:
            reset_day = s["today"] + timedelta(days=s["days_to_reset"])
            lines.append("")
            lines.append(f"[{MUTED}]Krediler her Pazartesi sıfırlanır — sonraki sıfırlama:"
                         f"[/] [bold {RED}]{_day_label(reset_day)}[/]"
                         f" [{MUTED}]({s['days_to_reset']} gün sonra)[/]")
        if s["last_reset"]:
            lines.append(f"[{MUTED}]Son sıfırlama: {_day_label(s['last_reset'])}[/]")
        yield self._panel("🏷️ Fiyat Tarifesi — her ek saat dakikayı pahalılaştırır",
                          "\n".join(lines), "p-purple", PURPLE)

        with Vertical(classes="panel p-yellow"):
            yield Static(f"[bold {YELLOW}]📉 Ekran süresi — son 30 gün (dk/gün)[/]")
            yield Sparkline(s["spark_minutes_30"], summary_function=max)

    def _haftalik(self, s) -> ComposeResult:
        yield self._panel("🌱 Haftalık Yeni Kelimeler (son 8 hafta)",
                          hbar_chart(s["weekly_new"], label_w=10),
                          "p-green", GREEN)
        yield self._panel("✨ Günlük Yeni Kelimeler (son 14 gün)",
                          hbar_chart(s["daily_new"], label_w=8),
                          "p-purple", PURPLE)
        legend = (f"[{GREEN}]█ Doğru[/]  [{RED}]█ Yanlış[/]  [{YELLOW}]█ Boş[/]\n\n")
        yield self._panel("💬 Günlük Cevaplar (son 14 gün)",
                          legend + stacked_chart(s["daily_answers"]),
                          "p-yellow", YELLOW)
        with Vertical(classes="panel p-green"):
            yield Static(f"[bold {GREEN}]⚡ Aktivite — son 30 gün "
                         f"(günlük cevap sayısı)[/]")
            yield Sparkline(s["spark_30"], summary_function=max)
        with Vertical(classes="panel p-purple"):
            yield Static(f"[bold {PURPLE}]🌱 Yeni kelime — son 30 gün[/]")
            yield Sparkline(s["spark_new_30"], summary_function=max)

    def _sure(self, s) -> ComposeResult:
        limit = s["daily_time_limit"]
        tiles = [
            ("⏱ Bugün (dk)", round(s["time_today"] / 60), "t-purple"),
            ("🎯 Günlük Limit (dk)", round(limit / 60) if limit else 0, "t-yellow"),
            ("⏳ Kalan (dk)", round(s["time_remaining"] / 60) if limit else 0, "t-green"),
            ("🔮 Kalan Soru", s["questions_left"] if limit else 0, "t-green"),
            ("⚡ Ort. Cevap (sn)", f"{s['time_avg']:.1f}", "t-green"),
            ("📅 Bu Hafta (dk)", round(s["time_week"] / 60), "t-purple"),
            ("♾️ Toplam (sa)", f"{s['time_total'] / 3600:.1f}", "t-yellow"),
            ("💬 Süresi Kayıtlı", s["timed_count"], "t-purple"),
            ("🚀 Cevap / dk", f"{s['answers_per_minute']:.1f}", "t-green"),
            ("🪙 Kredi / dk", f"{s['credits_per_minute']:.1f}", "t-yellow"),
        ]
        yield from self._tile_grid(tiles)

        if not s["timed_count"]:
            yield self._panel(
                "⏱ Süre Kaydı",
                f"[{MUTED}]Cevap süreleri bu sürümle kaydedilmeye başlandı — "
                f"quiz çözdükçe bu sekme dolacak. Daha önce cevaplanan sorular "
                f"süre içermediği için ortalamalara hiç katılmaz.[/]",
                "p-yellow", YELLOW)

        body = hbar_chart(s["time_14"], label_w=8)
        if limit:
            used = s["limit_used_pct"]
            lc = GREEN if used < 70 else YELLOW if used < 90 else RED
            body += (f"\n\n[{MUTED}]Günlük sınır:[/] [bold]{_fmt_duration(limit)}[/]"
                     f"   [{MUTED}]Bugün:[/] [bold {lc}]{_fmt_duration(s['time_today'])} "
                     f"(%{used:.0f})[/]"
                     f"   [{MUTED}]Kalan:[/] [bold {lc}]{_fmt_duration(s['time_remaining'])}[/]")
            if s["pace_seconds"]:
                body += (f"\n[{MUTED}]Bu hızda gidersen[/] "
                         f"[bold {lc}]{s['questions_left']} soru[/] "
                         f"[{MUTED}]daha çözebilirsin "
                         f"(ort. {s['pace_seconds']:.1f} sn/soru).[/]")
        else:
            body += (f"\n\n[{MUTED}]Günlük süre sınırı kapalı "
                     f"(DAILY_COALIDE_TIME_LIMIT = 0).[/]")
        if s["time_best_day"]:
            d, secs = s["time_best_day"]
            body += (f"\n[{MUTED}]En uzun çalışılan gün:[/] [bold]{_day_label(d)}[/] "
                     f"[{MUTED}]({_fmt_duration(secs)})[/]")
        yield self._panel("⏱ Günlük Çalışma Süresi (son 14 gün, dakika)",
                          body, "p-purple", PURPLE)

        with Vertical(classes="panel p-purple"):
            yield Static(f"[bold {PURPLE}]📉 Çalışma süresi — son 30 gün (dk/gün)[/]")
            yield Sparkline(s["spark_time_30"], summary_function=max)

        body = hbar_chart(s["speed_buckets"], label_w=10)
        if s["timed_count"]:
            body += (f"\n\n[{MUTED}]Ortalama:[/] [bold]{s['time_avg']:.1f} sn[/]"
                     f"   [{MUTED}]Ortanca:[/] [bold]{s['time_median']:.1f} sn[/]"
                     f"   [{MUTED}]En hızlı:[/] [bold {GREEN}]{s['time_fastest']:.1f} sn[/]"
                     f"   [{MUTED}]En yavaş:[/] [bold {RED}]{s['time_slowest']:.1f} sn[/]")
            body += (f"\n[{MUTED}]Son 7 gün ortalaması:[/] "
                     f"[bold]{s['time_avg_7']:.1f} sn[/]"
                     f"   [{MUTED}]Bugün:[/] [bold]{s['time_avg_today']:.1f} sn[/]")
        yield self._panel("⚡ Cevap Hızı Dağılımı", body, "p-green", GREEN)

        lines = []
        for key, label, color, sym in (("correct", "Doğru", GREEN, "✓"),
                                       ("wrong", "Yanlış", RED, "✗"),
                                       ("blank", "Boş", YELLOW, "∅")):
            r = s["time_by_result"][key]
            if r["count"]:
                lines.append(f"[{color}]{sym} {label:<7}[/] ortalama "
                             f"[bold]{r['avg']:.1f} sn[/]  "
                             f"[{MUTED}]({r['count']} cevap, toplam "
                             f"{_fmt_duration(r['total'])})[/]")
            else:
                lines.append(f"[{color}]{sym} {label:<7}[/] [{MUTED}]süresi kayıtlı "
                             f"cevap yok[/]")
        yield self._panel("🎯 Sonuca Göre Ortalama Süre", "\n".join(lines),
                          "p-yellow", YELLOW)

        if s["slowest_words"]:
            yield self._panel("🐢 En Yavaş 5 Kelime",
                              self._word_speed_text(s["slowest_words"], RED),
                              "p-red", RED)
            yield self._panel("🐇 En Hızlı 5 Kelime",
                              self._word_speed_text(s["fastest_words"], GREEN),
                              "p-green", GREEN)

        body = hbar_chart(s["hour_blocks"], label_w=8)
        if s["busiest_hour"] is not None:
            h = s["busiest_hour"]
            cnt = sum(s["hourly"][h][1:])
            body += (f"\n\n[{MUTED}]En yoğun saat:[/] "
                     f"[bold {YELLOW}]{h:02d}:00-{h + 1:02d}:00[/] "
                     f"[{MUTED}]({cnt} cevap)[/]")
        yield self._panel("🕒 Günün Saatlerine Göre Aktivite (tüm zamanlar)",
                          body, "p-yellow", YELLOW)

        lines = []
        for d in s["direction_stats"]:
            if not d["total"]:
                lines.append(f"[bold]{escape(d['label'])}[/] [{MUTED}]— henüz kayıt yok[/]")
                continue
            rc = rate_color(d["rate"])
            line = (f"[bold]{escape(d['label'])}[/]  [bold {rc}]%{d['rate']:.0f}[/]  "
                    f"([{GREEN}]{d['correct']}✓[/] [{RED}]{d['wrong']}✗[/] "
                    f"[{YELLOW}]{d['blank']}∅[/])  [{MUTED}]{d['total']} soru[/]")
            if d["avg_time"]:
                line += f"  [{MUTED}]ort. {d['avg_time']:.1f} sn[/]"
            lines.append(line)
        lines.append("")
        lines.append(f"[{MUTED}]Soru yönü her soruda rastgele seçilir; iki yön "
                     f"arasındaki fark hangi yönün daha zor geldiğini gösterir.[/]")
        yield self._panel("🔄 Soru Yönü", "\n".join(lines), "p-purple", PURPLE)

    @staticmethod
    def _word_speed_text(rows, color: str) -> str:
        lines = []
        for e in rows:
            lines.append(f"[bold]{escape(e['word']):<16}[/] [{color}]{e['avg']:.1f} sn[/]  "
                         f"[{MUTED}]({e['count']} cevap)[/]")
        return "\n".join(lines)

    TOP_WORD_TYPES = 6  # rest are summarised, see _kelimeler

    def _kelimeler(self, s) -> ComposeResult:
        # The chart is one line per word type, and the table below only gets
        # the height left over — with a big word list the chart used to grow
        # until the table was squeezed down to a couple of rows. Show the top
        # few types and count the rest instead.
        types = s["word_types"].most_common()
        body = hbar_chart([(t, c, PURPLE) for t, c in types[:self.TOP_WORD_TYPES]],
                          label_w=12)
        rest = types[self.TOP_WORD_TYPES:]
        if rest:
            body += (f"\n[{MUTED}]+ {len(rest)} tür daha "
                     f"({sum(c for _t, c in rest)} kelime)[/]")
        panel = self._panel("🏷️ Kelime Türleri", body, "p-purple", PURPLE)
        panel.id = "word-types"
        yield panel
        # Maturity filter: one button per SM-2 bucket, so the parent can narrow
        # the word list. The selected bucket persists across refresh.
        self._started_count = s["started_count"]
        rows = s["table_rows"]
        with Horizontal(id="word-filter"):
            for key, label, lo, hi in WORD_FILTERS:
                cnt = _word_filter_count(rows, lo, hi)
                classes = "active" if key == self._word_filter_key else ""
                yield Button(f"{label} ({cnt})", id=f"wf-{key}", classes=classes)
        # A plain title line rather than a bordered panel: on a short terminal
        # every row it would cost comes straight out of the table.
        lo, hi = self._current_filter_range()
        shown = _word_filter_count(rows, lo, hi)
        yield Static(self._word_table_title(shown), id="word-table-title")
        yield WordTable(rows, s["today"], lo, hi)

    def _gelecek(self, s) -> ComposeResult:
        yield self._panel("🔮 Tekrar Takvimi (gelecek 14 gün)",
                          hbar_chart(s["forecast"], label_w=9),
                          "p-purple", PURPLE)
        lines = []
        if s["eases"]:
            avg_e = sum(s["eases"]) / len(s["eases"])
            avg_i = sum(s["intervals"]) / len(s["intervals"])
            lines.append(f"Ortalama kolaylık faktörü (EF): [bold]{avg_e:.2f}[/]  "
                         f"[{MUTED}](1.30 = en zor, 2.50 = varsayılan)[/]")
            lines.append(f"En düşük EF: [bold]{min(s['eases']):.2f}[/]   "
                         f"En yüksek EF: [bold]{max(s['eases']):.2f}[/]")
            lines.append(f"Ortalama tekrar aralığı: [bold]{avg_i:.0f} gün[/]")
            if s["longest"]:
                lines.append(f"En uzun aralık: [bold]{escape(s['longest']['word'])}[/] "
                             f"([{GREEN}]{s['longest']['interval']} gün[/])")
        else:
            lines.append(f"[{MUTED}]Henüz çalışılmış kelime yok.[/]")
        yield self._panel("🧠 SM-2 Sağlığı", "\n".join(lines), "p-green", GREEN)

    # ---- word-table maturity filter -------------------------------------

    def _current_filter_range(self):
        """(lo, hi) for the active filter key; (None, None) for 'all'."""
        for key, _label, lo, hi in WORD_FILTERS:
            if key == self._word_filter_key:
                return lo, hi
        return None, None

    def _word_table_title(self, shown: int) -> str:
        total = getattr(self, "_started_count", shown)
        count = f"{shown}" if shown == total else f"{shown}/{total}"
        return (f"[bold {GREEN}]🔤 Tüm Kelimeler — en zordan kolaya "
                f"({count} başlanan)[/]"
                f"   [{MUTED}]↑↓ / PgUp / PgDn ile gezinin[/]")

    @on(Button.Pressed, "#word-filter Button")
    def _on_word_filter(self, event: Button.Pressed) -> None:
        key = (event.button.id or "").removeprefix("wf-")
        match = next((f for f in WORD_FILTERS if f[0] == key), None)
        if match is None:
            return
        self._word_filter_key = key
        _key, _label, lo, hi = match
        shown = self.query_one("#word-table", WordTable).set_range(lo, hi)
        for btn in self.query("#word-filter Button"):
            btn.set_class(btn.id == f"wf-{key}", "active")
        self.query_one("#word-table-title", Static).update(
            self._word_table_title(shown))

    # ---- actions ---------------------------------------------------------

    @on(TabbedContent.TabActivated)
    def _focus_table(self, event: TabbedContent.TabActivated) -> None:
        """Opening the Kelimeler tab hands focus to the table, so the arrow
        keys and PageUp/PageDown scroll the word list straight away."""
        if event.pane.id != "tab-kelime":
            return
        def focus_table() -> None:
            try:
                self.query_one("#word-table", DataTable).focus()
            except NoMatches:
                pass
        self.call_after_refresh(focus_table)

    def action_refresh_stats(self) -> None:
        self.refresh(recompose=True)
        self.notify("İstatistikler yenilendi.", title="🔄 Yenile", timeout=3)


def main():
    StatsApp().run()


if __name__ == "__main__":
    main()

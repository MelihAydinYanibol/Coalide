"""
Web-app learning engine for Coalide.

This is a per-user, web-safe port of the terminal app's spaced-repetition
core (``sm2.py`` + ``objects/word_obj.py``). The scheduling math, quality
grading and question-selection algorithm are kept identical to the terminal
version so a learner gets the same behaviour; the difference is that all
progress state lives per-user under ``webapp/data/`` instead of in the single
shared ``progress.json`` the terminal app writes.

The vocabulary database (``words.json``) and the :class:`Word` model are
reused directly from the parent project, so there is a single source of truth
for the words themselves.
"""

from __future__ import annotations

import json
import os
import random
import sys
from datetime import date, datetime, time, timedelta
from operator import attrgetter

# Make the parent project importable so we can reuse the Word model and the
# vocabulary database without duplicating them here.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from objects.word_obj import Word  # noqa: E402  (path setup must come first)

WORDS_FILE = os.path.join(PROJECT_ROOT, "words.json")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

NEW_WORD_SENTINEL = "2020-10-10"  # next_review_date for brand-new (never reviewed) words

os.makedirs(DATA_DIR, exist_ok=True)


# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #

def get_config() -> dict:
    """
    Load the shared ``config.json`` from the project root, falling back to the
    terminal app's defaults. We read the file directly (rather than importing
    ``utils``) to avoid the terminal module's import-time side effects, but we
    honour the same keys so the web and terminal apps behave consistently.
    """
    defaults = {
        "Daily_New_Word_Cap": 15,
        "No_Repeat_Window": 8,
        "SHUFFLE_NEW_WORDS": False,
        "Source_Language": "Türkçe",
        "Target_Language": "İngilizce",
        "SPAM_PROTECTION": True,
        "Credit_Reset_Weekly": True,
        "Credit_Window_Start": "07:00",
        "Credit_Window_End": "22:00",
        "CREDITS_PER_CORRECT": 7,
    }
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            defaults.update(loaded)
    except (OSError, json.JSONDecodeError):
        pass
    return defaults


# --------------------------------------------------------------------------- #
# Answer handling (ported from new_master.normalize_answer)                    #
# --------------------------------------------------------------------------- #

def normalize_answer(s: str) -> str:
    """
    Normalise an answer for comparison. Drops an accidental trailing comma and
    handles Turkish "İ"/"I" casing correctly (Python's ``.lower()`` mishandles
    them), exactly like the terminal app.
    """
    s = (s or "").strip().rstrip(",").strip()
    return s.replace("İ", "i").replace("I", "ı").lower()


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return value
    return [value]


# --------------------------------------------------------------------------- #
# Per-user progress persistence                                                #
# --------------------------------------------------------------------------- #

def _safe_username(username: str) -> str:
    keep = [c for c in (username or "") if c.isalnum() or c in ("-", "_")]
    return "".join(keep).strip() or "guest"


def _progress_path(username: str) -> str:
    return os.path.join(DATA_DIR, f"{_safe_username(username)}_progress.json")


def load_progress(username: str) -> dict:
    path = _progress_path(username)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_progress(username: str, progress: dict) -> None:
    with open(_progress_path(username), "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=4)


def save_word_progress(username: str, word: Word) -> None:
    """Persist a single word's SM-2 + stats state into the user's progress file."""
    progress = load_progress(username)
    progress[word.target] = {
        "next_review_date": word.next_review_date,
        "last_review_date": word.last_review_date,
        "first_review_date": word.first_review_date,
        "repetitions": word.repetitions,
        "ease_factor": word.ease_factor,
        "interval": word.interval,
        "rate": word.rate,
        "total_attempts": word.total_attempts,
        "correct_attempts": word.correct_attempts,
        "wrong_attempts": word.wrong_attempts,
        "blank_attempts": word.blank_attempts,
        "last_ten_attempts": word.last_ten_attempts,
    }
    _write_progress(username, progress)


# --------------------------------------------------------------------------- #
# Word loading (per-user)                                                      #
# --------------------------------------------------------------------------- #

def load_word_list(username: str) -> list[Word]:
    """
    Build the user's word list: every definition from ``words.json`` with this
    user's saved progress merged in. Mirrors ``word_engine.get_words`` but
    reads per-user progress instead of the shared ``progress.json``.
    """
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    progress = load_progress(username)
    words: list[Word] = []
    for item in data:
        item = dict(item)
        item["sentence"] = tuple(item["sentence"])
        item.pop("next_review_date", None)  # progress is per-user, not from words.json
        word = Word(**{k: v for k, v in item.items() if k in (
            "language", "word_type", "source", "sentence", "target", "past", "v3")})

        p = progress.get(word.target)
        if p:
            word.next_review_date = p.get("next_review_date")
            word.last_review_date = p.get("last_review_date")
            word.first_review_date = p.get("first_review_date", p.get("last_review_date"))
            word.repetitions = p.get("repetitions", 0)
            word.ease_factor = p.get("ease_factor", 2.5)
            word.interval = p.get("interval", 0)
            word.last_ten_attempts = p.get("last_ten_attempts", [])
            word.total_attempts = p.get("total_attempts", 0)
            word.correct_attempts = p.get("correct_attempts", 0)
            word.wrong_attempts = p.get("wrong_attempts", 0)
            word.blank_attempts = p.get("blank_attempts", 0)
        else:
            word.next_review_date = NEW_WORD_SENTINEL
        words.append(word)
    return words


def _order_word_list(words: list[Word], shuffle_new: bool) -> list[Word]:
    words.sort(key=attrgetter("next_review_date"))
    if shuffle_new:
        new_words = [w for w in words if w.next_review_date == NEW_WORD_SENTINEL]
        if len(new_words) > 1:
            random.shuffle(new_words)
            others = [w for w in words if w.next_review_date != NEW_WORD_SENTINEL]
            words[:] = new_words + others
    return words


def _find_word(words: list[Word], word_id: str) -> Word | None:
    for w in words:
        if w.id == word_id:
            return w
    return None


# --------------------------------------------------------------------------- #
# Question selection (ported from sm2.get_next_question)                       #
# --------------------------------------------------------------------------- #

def get_next_word(username: str, feed: list[str] | None = None) -> tuple[Word | None, bool]:
    """
    Return ``(word, is_target_wanted)`` chosen with the SM-2 due logic, or
    ``(None, ...)`` if the word list is empty. Falls back to the soonest word
    so a session never runs dry, respecting the daily new-word cap and the
    no-repeat window — identical to the terminal engine.
    """
    if feed is None:
        feed = []

    config = get_config()
    daily_cap = config.get("Daily_New_Word_Cap", 15)
    no_repeat = config.get("No_Repeat_Window", 8)

    words = load_word_list(username)
    _order_word_list(words, config.get("SHUFFLE_NEW_WORDS", False))

    todays_new = [w for w in words if w.first_review_date == str(date.today())]
    cap_reached = len(todays_new) >= daily_cap

    due = [w for w in words if w.is_due]
    if cap_reached:
        due = [w for w in due if w.next_review_date != NEW_WORD_SENTINEL]

    if not due:
        pool = [w for w in words if w.next_review_date != NEW_WORD_SENTINEL] if cap_reached else list(words)
        pool.sort(key=attrgetter("next_review_date"))
        due = pool
        if not due:
            return None, True

    due.sort(key=attrgetter("next_review_date"))

    recent = set(feed[-no_repeat:])
    filtered = [w for w in due if w.id not in recent]
    if filtered:
        due = filtered

    next_word = due[0]
    is_target_wanted = random.randint(0, 1) == 1
    return next_word, is_target_wanted


# --------------------------------------------------------------------------- #
# Grading (ported from sm2.calculate_quality / update_sm2 / word_obj.add_result)
# --------------------------------------------------------------------------- #

def calculate_quality(is_correct, word_length: int, time_taken: float) -> int:
    """Grade an answer into an SM-2 quality score (0-5) from correctness + speed."""
    time_cap = word_length * 2
    if is_correct is None:  # blank
        return 0
    if time_taken <= time_cap:
        return 5 if is_correct else 1
    return 4 if is_correct else 2


def apply_result(word: Word, is_correct, quality: int) -> None:
    """
    Update a word's SM-2 schedule and last-ten stats, then persist. ``is_correct``
    is True / False / None(blank). Mirrors ``update_sm2`` + ``Word.add_result``.
    """
    today = date.today()

    # --- SM-2 schedule update ---
    if quality < 3:
        word.repetitions = 0
        word.interval = 1
        word.next_review_date = today.isoformat()  # due again today
    else:
        if word.repetitions == 0:
            word.interval = 1
        elif word.repetitions == 1:
            word.interval = 6
        else:
            word.interval = round(word.interval * word.ease_factor)
        word.repetitions += 1
        word.next_review_date = (today + timedelta(days=word.interval)).isoformat()

    word.ease_factor = max(
        1.3,
        word.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )

    if word.first_review_date is None:
        word.first_review_date = today.isoformat()
    word.last_review_date = today.isoformat()

    # --- last-ten stats update ---
    result = None if is_correct is None else bool(is_correct)
    word.last_ten_attempts = word.last_ten_attempts[-9:] + [result]
    word.total_attempts = len(word.last_ten_attempts)
    word.correct_attempts = word.last_ten_attempts.count(True)
    word.wrong_attempts = word.last_ten_attempts.count(False)
    word.blank_attempts = word.last_ten_attempts.count(None)


# --------------------------------------------------------------------------- #
# Presentation helpers                                                         #
# --------------------------------------------------------------------------- #

def build_question(word: Word, is_target_wanted: bool) -> dict:
    """Serialise a Word into a question payload for the frontend."""
    source_display = word.source[0] if isinstance(word.source, list) and word.source else word.source
    prompt = source_display if is_target_wanted else word.target
    blank = "_" * (len(word.target) * 2)
    example = f"{word.sentence[0]} {blank} {word.sentence[1]}".strip()

    return {
        "word_id": word.id,
        "prompt": prompt,
        "is_target_wanted": is_target_wanted,
        "word_type": word.word_type,
        "example_sentence": example,
        "rate": word.rate,
        "total_attempts": word.total_attempts,
        "correct_attempts": word.correct_attempts,
        "is_new": word.total_attempts == 0,
    }


def grade_answer(word: Word, is_target_wanted: bool, answer: str, time_taken: float) -> dict:
    """
    Grade the user's answer for ``word``, update + persist progress, and return
    a result payload. Handles list-valued source translations (any accepted).
    """
    expected = word.target if is_target_wanted else word.source
    raw = (answer or "").strip()

    if raw == "":
        is_correct = None
    elif isinstance(expected, list):
        norm = normalize_answer(raw)
        is_correct = norm in [normalize_answer(e) for e in expected]
    else:
        is_correct = normalize_answer(raw) == normalize_answer(expected)

    expected_list = _as_list(expected)
    length = max(len(e) for e in expected_list)
    quality = calculate_quality(is_correct, length, time_taken)
    apply_result(word, is_correct, quality)

    # Full word info for the answer reveal / pronunciation.
    full_sentence = f"{word.sentence[0]} {word.target} {word.sentence[1]}".strip()
    return {
        "is_correct": is_correct,          # True / False / None(blank)
        "correct_answer": expected_list[0],
        "all_answers": expected_list,
        "target": word.target,
        "source": _as_list(word.source),
        "full_sentence": full_sentence,
        "rate": word.rate,
        "correct_attempts": word.correct_attempts,
        "total_attempts": word.total_attempts,
        "quality": quality,
    }


# --------------------------------------------------------------------------- #
# Session / user stats                                                         #
# --------------------------------------------------------------------------- #

def user_stats(username: str) -> dict:
    """Aggregate learning stats for the dashboard header."""
    words = load_word_list(username)
    progress = load_progress(username)

    learned = [w for w in words if w.target in progress]
    total_attempts = sum(w.total_attempts for w in learned)
    total_correct = sum(w.correct_attempts for w in learned)
    due_now = sum(1 for w in words if w.is_due and w.target in progress)
    mastered = sum(1 for w in learned if w.rate >= 80 and w.total_attempts >= 3)

    overall_rate = round((total_correct / total_attempts) * 100, 1) if total_attempts else 0.0
    return {
        "total_words": len(words),
        "words_seen": len(learned),
        "due_now": due_now,
        "mastered": mastered,
        "overall_rate": overall_rate,
    }

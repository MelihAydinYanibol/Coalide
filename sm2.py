"""
This module returns the next Question object according to SM-2 algorithm.


"""

from word_engine import get_words
from operator import attrgetter
from objects.word_obj import Word,save_progress
from objects.question_obj import Question
from utils import lg,get_config
import json
import os
import random

config = get_config()

DAILY_NEW_WORD_CAP = config.get("Daily_New_Word_Cap", 15) # how many brand-new words can be introduced per day
NO_REPEAT_WINDOW = config.get("No_Repeat_Window", 8) # a word can't repeat within this many questions
SHUFFLE_NEW_WORDS = config.get("SHUFFLE_NEW_WORDS", False) # introduce new words in random order instead of words.json order

NEW_WORD_SENTINEL = "2020-10-10" # next_review_date assigned to brand-new (never-reviewed) words

# Everything randomized about the question currently on screen -- the direction
# and, when the prompt side has aliases, which one is shown -- remembered on
# disk. Without this a kid could type "exit" and restart the quiz to re-roll:
# the other direction shows them the answer they were just asked for, and a
# different alias is a second free hint at the same answer. Only one question is
# ever pending, so a single slot is enough.
#
# Deliberately NOT stored in progress.json: every key there counts as a "started"
# word in the stats screen (see stats_menu.build_stats), and merely being shown a
# question shouldn't move those numbers.
PENDING_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pending_question.json")


def _load_pending_question(word_id: str) -> tuple[bool, int] | None:
    """
    The saved (direction, prompt_index) for `word_id`, or None when nothing is
    pending for it. A slot written before prompt_index existed still loads, as
    index 0.
    """
    try:
        with open(PENDING_FILE, "r", encoding="UTF-8") as f:
            pending = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(pending, dict) or pending.get("word_id") != word_id:
        return None
    direction = pending.get("is_target_wanted")
    if not isinstance(direction, bool):
        return None
    index = pending.get("prompt_index", 0)
    return direction, index if isinstance(index, int) and index >= 0 else 0


def _save_pending_question(word_id: str, is_target_wanted: bool, prompt_index: int) -> None:
    try:
        with open(PENDING_FILE, "w", encoding="UTF-8") as f:
            json.dump({"word_id": word_id, "is_target_wanted": is_target_wanted,
                       "prompt_index": prompt_index}, f)
    except OSError:
        lg("Could not save the pending question.")  # must never break the quiz


def _clear_pending_question() -> None:
    """Forget the pending question once it has been answered."""
    try:
        os.remove(PENDING_FILE)
    except OSError:
        pass  # already gone (or unwritable) -- nothing to forget either way


def _random_prompt_index(word: Word, is_target_wanted: bool) -> int:
    """
    Pick which alias to show when the prompt side has several ("almak" / "elde
    etmek" for "get"); 0 when that side is a plain string. Goes through a
    throwaway Question so the "which side is the prompt" rule stays in one place.
    """
    prompt = Question(word=word, is_target_wanted=is_target_wanted).prompt
    if isinstance(prompt, list) and prompt:
        return random.randrange(len(prompt))
    return 0


def _order_word_list(words: list[Word]):
    """
    Sort words by next_review_date (earliest first) in place.

    Brand-new words all share NEW_WORD_SENTINEL, the earliest possible date, so
    they land at the front of the list. By default they stay in words.json order;
    when SHUFFLE_NEW_WORDS is enabled we shuffle just those new words among
    themselves so they're introduced in a random order. Because every downstream
    sort is a stable sort on the same key, this randomized order is preserved
    throughout the session.
    """
    words.sort(key=attrgetter('next_review_date')) # sort by next review date, earliest first
    if SHUFFLE_NEW_WORDS:
        new_words = [w for w in words if w.next_review_date == NEW_WORD_SENTINEL]
        if len(new_words) > 1:
            random.shuffle(new_words)
            others = [w for w in words if w.next_review_date != NEW_WORD_SENTINEL]
            words[:] = new_words + others
    return words


word_list = get_words("words.json")
lg(word_list)
_order_word_list(word_list)

# if the word is new, it's next_review_date will equal to "00-00-01" which is the earliest possible date, so it will be at the front of the list

def reload_words():
    """
    Re-read words.json from disk and re-sort word_list. Needed because word_list
    is loaded once at import time, so callers that update words.json on disk
    (e.g. check_and_update_words in new_master.py) must call this afterwards for
    the change to take effect in the current process.
    """
    global word_list
    word_list = get_words("words.json")
    _order_word_list(word_list)

def _fallback_pool(cap_reached: bool):
    """
    Nothing is due right now. Instead of ending the session, serve the
    soonest-upcoming word early. If the daily new-word cap has been hit,
    exclude brand-new (sentinel-dated) words from this pool too --
    otherwise the fallback would quietly blow past the cap it's supposed
    to respect.
    """
    pool = [w for w in word_list if w.next_review_date != "2020-10-10"] if cap_reached else list(word_list)
    pool.sort(key=attrgetter('next_review_date'))
    return pool

def get_next_question(feed: list | None = None) -> Question:
    """
    Get the next Question object according to SM-2 algorithm.
    Falls back to early review if nothing is currently due, so the
    session never runs out of questions to ask.
 
    :return: The next Question object, or None only if the word list itself is empty.
    """
    if feed is None:
        feed = []
 
    from datetime import date
    # Only words *introduced* (first ever reviewed) today count toward the
    # daily new-word cap -- reviewing old words shouldn't block new ones.
    todays_new_words = [word for word in word_list if word.first_review_date == str(date.today())]
    cap_reached = len(todays_new_words) >= DAILY_NEW_WORD_CAP
 
    due_words = [word for word in word_list if word.is_due]
    if cap_reached:
        due_words = [word for word in due_words if word.next_review_date != "2020-10-10"]
 
    if not due_words:
        due_words = _fallback_pool(cap_reached)
        if not due_words:
            return None  # word list itself is empty -- nothing to fall back to
 
    due_words.sort(key=attrgetter('next_review_date'))
 
    # NO_REPEAT_WINDOW logic
    recent_words = set(feed[-NO_REPEAT_WINDOW:])
    due_words_filtered = [word for word in due_words if word.id not in recent_words]
    if due_words_filtered:
        due_words = due_words_filtered
 
    next_word = due_words[0]
    # Reuse the presentation -- direction and which alias is shown -- if this
    # word was already put on screen and left unanswered, so quitting and
    # restarting can't re-roll either of them (see PENDING_FILE).
    pending = _load_pending_question(next_word.id)
    if pending is None:
        is_target_wanted = random.randint(0, 1) == 1
        prompt_index = _random_prompt_index(next_word, is_target_wanted)
        _save_pending_question(next_word.id, is_target_wanted, prompt_index)
    else:
        is_target_wanted, prompt_index = pending
    return Question(word=next_word, is_target_wanted=is_target_wanted,
                    prompt_index=prompt_index)

def calculate_quality(is_correct, word_length:int, time_taken: float) -> int:
    """
    Calculate the quality of the user's response based on correctness and time taken.

    :param is_correct: Whether the user's answer was correct.
    :param time_taken: Time taken to answer in seconds.
    :return: Quality score (0-5).
    """

    TIME_CAP = word_length * 2  # Time cap based on word length

    if time_taken <= TIME_CAP:
        if is_correct == True:
            return 5
        elif is_correct == False:
            return 1
    else:
        if is_correct == True:
            return 4
        elif is_correct == False:
            return 2
    if is_correct == None: # None is for blank
        return 0

def update_sm2(word, quality: int):
    from datetime import date, timedelta

    if quality < 3:
        word.repetitions = 0
        word.interval = 1
        word.next_review_date = date.today().isoformat()  # due again today, not tomorrow
    else:
        if word.repetitions == 0:
            word.interval = 1
        elif word.repetitions == 1:
            word.interval = 6
        else:
            word.interval = round(word.interval * word.ease_factor)
        word.repetitions += 1
        word.next_review_date = (date.today() + timedelta(days=word.interval)).isoformat()

    # ease factor update (same for pass or fail, standard SM-2 formula)
    word.ease_factor = max(
        1.3,
        word.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )

    if word.first_review_date is None:
        word.first_review_date = date.today().isoformat()  # first ever review = word introduced today
    word.last_review_date = date.today().isoformat()  # Update the last review date to today
    save_progress(word)  # Save the updated word progress to progress.json
    _clear_pending_question()  # answered -- the next outing re-rolls the presentation
    return word


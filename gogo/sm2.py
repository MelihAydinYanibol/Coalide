"""
This module returns the next Question object according to SM-2 algorithm.


"""

from word_engine import get_words
from operator import attrgetter
from objects.word_obj import Word,save_progress
from objects.question_obj import Question
import random

DAILY_NEW_WORD_CAP  = 15 # how many brand-new words can be introduced per day
NO_REPEAT_WINDOW = 8 # a word can't repeat within this many questions



word_list = get_words("words.json")
print(word_list)
word_list.sort(key=attrgetter('next_review_date')) # sort by next review date, earliest first

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
    word_list.sort(key=attrgetter('next_review_date'))

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
    todays_answered_words = [word for word in word_list if word.last_review_date == str(date.today())]
    cap_reached = len(todays_answered_words) >= DAILY_NEW_WORD_CAP
 
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
    is_target_wanted = random.randint(0, 1) == 1
    return Question(word=next_word, is_target_wanted=is_target_wanted)

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

    word.last_review_date = date.today().isoformat()  # Update the last review date to today
    save_progress(word)  # Save the updated word progress to progress.json
    return word


"""
This module returns the next Question object according to SM-2 algorithm
We will have 5 Boxes (lists), each box corresponds to a review interval.

"""

from word_engine import get_words
from operator import attrgetter
from objects.word_obj import Word
from objects.question_obj import Question
import random

DAILY_NEW_WORD_CAP  = 15 # how many brand-new words can be introduced per day
NO_REPEAT_WINDOW = 8 # a word can't repeat within this many questions



word_list = get_words("words.json")
print(word_list)
word_list.sort(key=attrgetter('next_review_date')) # sort by next review date, earliest first

# if the word is new, it's next_review_date will equal to "00-00-01" which is the earliest possible date, so it will be at the front of the list

def get_next_question(feed: list | None = None) -> Question:
    """
    Get the next Question object according to SM-2 algorithm.

    :return: The next Question object.
    """

    if feed is None: feed = []

    # Filter words that are due for review
    due_words = [word for word in word_list if word.is_due]

    # If there are no due words, return None
    if not due_words:
        return None
    due_words.sort(key=attrgetter('next_review_date'))  # sort by next review date, earliest first
    

    # DAILY_NEW_WORD_CAP LOGIC STARTS HERE
    from datetime import date
    todays_answered_words = [word for word in word_list if word.last_review_date == str(date.today())]
    if len(todays_answered_words) >= DAILY_NEW_WORD_CAP:
        # Filter out new words (those with next_review_date equal to "2020-10-10")
        due_words = [word for word in due_words if word.next_review_date != "2020-10-10"]
        if not due_words:
            return None  # No more questions can be asked today
    
    # NO_REPEAT_WINDOW LOGIC STARTS HERE
    # Filter out words that have been asked in the last NO_REPEAT_WINDOW questions
    recent_words = set(feed[-NO_REPEAT_WINDOW:])  # Get the last NO_REPEAT_WINDOW words asked
    due_words_filtered = [word for word in due_words if word.id not in recent_words]
    if due_words_filtered == []:
        # If no words are left after filtering, discard the filter.
        pass
    else: due_words = due_words_filtered

    # Select the first due word (earliest next_review_date)
    next_word = due_words[0]

    if random.randint(0, 1) == 1:
        is_target_wanted = True
    else:
        is_target_wanted = False

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
    """
    Standard SM-2 update. Expects `word` to have:
        - repetitions: int
        - ease_factor: float (starts at 2.5)
        - interval: int (days)
    Mutates them in place and sets next_review_date.
    """
    from datetime import date, timedelta
 
    if quality < 3:
        word.repetitions = 0
        word.interval = 1
    else:
        if word.repetitions == 0:
            word.interval = 1
        elif word.repetitions == 1:
            word.interval = 6
        else:
            word.interval = round(word.interval * word.ease_factor)
        word.repetitions += 1
 
    # ease factor update (same for pass or fail, standard SM-2 formula)
    word.ease_factor = max(
        1.3,
        word.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
 
    word.next_review_date = (date.today() + timedelta(days=word.interval)).isoformat()
    word.last_review_date = date.today().isoformat()  # Update the last review date to today
    save_progress(word)  # Save the updated word progress to progress.json
    return word

def save_progress(word: Word):
    """
    Save the progress of a word to the progress.json file.

    :param word: The Word object whose progress is to be saved.
    """
    import json
    import os

    progress_file_path = "progress.json"

    # Load existing progress data
    if os.path.exists(progress_file_path):
        with open(progress_file_path, 'r', encoding='utf-8') as file:
            progress_data = json.load(file)
    else:
        progress_data = {}

    # Update the progress data for the given word
    progress_data[word.target] = {
        "next_review_date": word.next_review_date,
        "last_review_date": word.last_review_date,
        "repetitions": word.repetitions,
        "ease_factor": word.ease_factor,
        "interval": word.interval
    }

    # Save the updated progress data back to the file
    with open(progress_file_path, 'w', encoding='utf-8') as file:
        json.dump(progress_data, file, ensure_ascii=False, indent=4)
        file.close()
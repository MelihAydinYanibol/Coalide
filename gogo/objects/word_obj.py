"""
Rethinking how word objects work.

word object will have the following attributes:
- language: str
- word_type: str
- sentence: tuple[str, str]
- target: str
- past: str
- v3: str

past and v3 are only relevant for verbs, but they will be present for all words. For non-verbs, they will be empty strings.

Language attribute will return the language code according to ISO 639 language codes (https://en.wikipedia.org/wiki/List_of_ISO_639_language_codes)
User will be able to set the language when initating the word object. If not set, it will raise an error. The language attribute will be used to determine the language of the word and its translation.

"""

class Word:
    """
    Word object represents a word in the flashcard system. It contains information about the word, its type, its tenses, and its translations.
    :param language: The language code of the word (ISO 639 language codes).
    :param word_type: The type of the word (e.g., "verb", "noun", "adjective").
    :param sentence: A tuple containing two parts of a sentence where the word is used. The first part is the beginning of the sentence, and the second part is the end of the sentence.
    :param target: The target word (the word being learned).
    :param past: The past tense of the word (only relevant for verbs).
    :param v3: The third form of the word (only relevant for verbs).
    :param next_review_date: The date when the word is next due for review (in "YYYY-MM-DD" format). If None, the word has never been reviewed.
    :param last_review_date: The date when the word was last reviewed (in "YYYY-MM-DD" format). If None, the word has never been reviewed.
    :param repetitions: The number of times the word has been reviewed.
    :param ease_factor: The ease factor of the word, used in the SM2 algorithm to determine the interval between reviews.
    :param interval: The interval in days until the next review.
    """
    def __init__(
            self,
            language: str,
            word_type: str,
            source: list,
            sentence: tuple[str, str],
            target: str,
            past: str = "",
            v3: str = "",
            next_review_date: str | None = None, 
            last_review_date: str | None = None,
            total_attempts: int = 0,
            correct_attempts: int = 0,
            wrong_attempts: int = 0,
            blank_attempts: int = 0):
        
        if not language:
            raise ValueError("Language must be set for Word object.")
        if not target:
            raise ValueError("Target word must be set for Word object.")
        self.language = language
        self.word_type = word_type
        self.sentence = sentence
        self.target = target
        self.past = past
        self.v3 = v3
        self.source = source
        self.id = f"{self.language}_{self.target}"  # Unique identifier for the word
        
        # SM2 Algorithm tracking
        self.next_review_date = next_review_date
        self.last_review_date = last_review_date
        self.repetitions = 0
        self.ease_factor = 2.5
        self.interval = 0  # in days

        # Success rate tracking (Last 10 attempts)
        self.total_attempts = 0
        self.correct_attempts = 0 # last 10
        self.wrong_attempts = 0 # last 10
        self.blank_attempts = 0 # last 10
        self.last_ten_attempts = []  # List to track the last ten attempts for this word
    @property
    def is_verb(self) -> bool:
        return self.word_type.lower() == "verb"

    @property
    def is_due(self) -> bool:
        if self.next_review_date is None:
            return True  # never reviewed = always eligible
        import datetime
        return datetime.date.fromisoformat(self.next_review_date) <= datetime.date.today()

    @property
    def rate(self) -> float:
        """
        Calculate the success rate of the word based on attempts.
        :return: Success rate as a float between 0 and 1. Returns None if there are no attempts.
        """
        if self.total_attempts == 0:
            return 0.0  # No attempts made yet
        return round((self.correct_attempts / self.total_attempts) * 10, 1)

    def add_result(self, is_correct: bool, is_blank: bool = False):
        """
        Update the word's statistics based on the result of a review attempt.
        :param is_correct: Whether the user's answer was correct.
        :param is_blank: Whether the user's answer was blank.
        """
        if is_blank:
            is_correct = None  # Treat blank attempts as None for tracking purposes
    
        self.last_ten_attempts = self.last_ten_attempts[-9:] + [is_correct]  # Keep only the last 10 attempts
        self.total_attempts = len(self.last_ten_attempts)
        
        # RESET
        self.correct_attempts = self.wrong_attempts = self.blank_attempts = 0
        
        # SUM

        self.correct_attempts = self.last_ten_attempts.count(True)
        self.wrong_attempts = self.last_ten_attempts.count(False)
        self.blank_attempts = self.last_ten_attempts.count(None)

        save_progress(self)  # Save progress after updating stats

    def __repr__(self) -> str:
        return (
            f"Word(language={self.language!r}, word_type={self.word_type!r}, "
            f"sentence={self.sentence!r}, target={self.target!r}, "
            f"past={self.past!r}, v3={self.v3!r})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Word):
            return NotImplemented
        return (
            self.language == other.language
            and self.word_type == other.word_type
            and tuple(self.sentence) == tuple(other.sentence)
            and self.target == other.target
            and self.past == other.past
            and self.v3 == other.v3
        )
    

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
        "interval": word.interval,
        "rate": word.rate,
        "total_attempts": word.total_attempts,
        "correct_attempts": word.correct_attempts,
        "wrong_attempts": word.wrong_attempts,
        "blank_attempts": word.blank_attempts,
        "last_ten_attempts": word.last_ten_attempts
    }

    # Save the updated progress data back to the file
    with open(progress_file_path, 'w', encoding='utf-8') as file:
        json.dump(progress_data, file, ensure_ascii=False, indent=4)
        file.close()

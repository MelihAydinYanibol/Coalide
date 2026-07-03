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
    def __init__(self, language: str, word_type: str, source: list, sentence: tuple[str, str],target: str, past: str = "", v3: str = "", next_review_date: str | None = None, last_review_date: str | None = None):
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
        self.next_review_date = next_review_date
        self.last_review_date = last_review_date
        self.repetitions = 0
        self.ease_factor = 2.5
        self.interval = 0  # in days
        self.id = f"{self.language}_{self.target}"  # Unique identifier for the word


    @property
    def is_verb(self) -> bool:
        return self.word_type.lower() == "verb"

    @property
    def is_due(self) -> bool:
        if self.next_review_date is None:
            return True  # never reviewed = always eligible
        import datetime
        return datetime.date.fromisoformat(self.next_review_date) <= datetime.date.today()

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
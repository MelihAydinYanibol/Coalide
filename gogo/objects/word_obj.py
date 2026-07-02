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
    def __init__(self, language: str, word_type: str, source: list, sentence: tuple[str, str],target: str, past: str = "", v3: str = "", next_review_date: str | None = None):
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
        self.repetitions = 0
        self.ease_factor = 2.5
        self.interval = 0  # in days


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
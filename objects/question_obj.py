"""
Question object will have the following attributes:
- word: Word
- is_target_wanted: bool
- is_source_wanted: bool
"""

from objects.word_obj import Word

class Question:
    """
    This object represents a question in the flashcard system. It contains a Word object and indicates whether the target or source word is being asked for.

    :param word: The Word object associated with this question.
    :param is_target_wanted: A boolean indicating whether the target word is being asked for
    """
    def __init__(self, word: Word, is_target_wanted: bool):
        self.word = word
        self.is_target_wanted = is_target_wanted

    @property
    def is_source_wanted(self) -> bool:
        return not self.is_target_wanted

    @property
    def prompt(self) -> str:
        return self.word.source if self.is_target_wanted else self.word.target

    @property
    def expected_answer(self) -> str:
        return self.word.target if self.is_target_wanted else self.word.source
    
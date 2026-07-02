"""
Question object will have the following attributes:
- word: Word
- is_target_wanted: bool
- is_source_wanted: bool
"""

from objects.word_obj import Word

class Question:
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
    
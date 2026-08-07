"""
Question object will have the following attributes:
- word: Word
- is_target_wanted: bool
- is_source_wanted: bool
- prompt_index: int
"""

from objects.word_obj import Word

class Question:
    """
    This object represents a question in the flashcard system. It contains a Word object and indicates whether the target or source word is being asked for.

    :param word: The Word object associated with this question.
    :param is_target_wanted: A boolean indicating whether the target word is being asked for
    :param prompt_index: Which alias to show when the prompt side has several (see prompt_text).
    """
    def __init__(self, word: Word, is_target_wanted: bool, prompt_index: int = 0):
        self.word = word
        self.is_target_wanted = is_target_wanted
        self.prompt_index = prompt_index

    @property
    def is_source_wanted(self) -> bool:
        return not self.is_target_wanted

    @property
    def prompt(self) -> str:
        return self.word.source if self.is_target_wanted else self.word.target

    @property
    def prompt_text(self) -> str:
        """
        The single prompt actually put on screen. The prompt side often has
        several aliases ("almak" / "elde etmek" for "get"); prompt_index picks
        which one, and is held fixed until the question is answered so leaving
        and re-entering the quiz can't re-roll it into a different hint
        (see sm2.PENDING_FILE).
        """
        prompt = self.prompt
        if isinstance(prompt, list):
            return prompt[self.prompt_index % len(prompt)] if prompt else ""
        return prompt

    @property
    def expected_answer(self) -> str:
        return self.word.target if self.is_target_wanted else self.word.source
    
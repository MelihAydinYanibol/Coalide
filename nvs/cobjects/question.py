"""
question.py — Question class for Coalide's quiz logic.

A Question pairs one Word with a direction (is the learner answering
in the target language or the source language?) plus a unique id.
It knows how to grade an answer and append the result to
statistics.csv in the exact format main.py's existing save_stat()
already writes, so the rest of the app (daily_stat, analytics, etc.)
keeps working unchanged.

Depends on word.py.
"""

from __future__ import annotations

import datetime
import itertools
import random

from cobjects.word import Word, _tr_lower


class Question:
    """One asked instance of a Word, in one specific direction."""

    # Class variable: shared by every Question, used to hand out the
    # next id. Each instance still gets its own `self.id` (an int),
    # but the counter itself lives on the class, not on any one object.
    _id_counter = itertools.count(1)

    def __init__(self, word: Word, is_target: bool, question_id: int | None = None):
        self.id = question_id if question_id is not None else next(Question._id_counter)
        self.word = word
        self._is_target = is_target

    @classmethod
    def random(cls, word: Word) -> "Question":
        """
        Build a Question with a random direction — the OOP version of
        the `random.randint(1, 2)` coin-flip already in quest().
        """
        return cls(word, is_target=random.choice([True, False]))

    @property
    def is_target(self) -> bool:
        """True if the learner must answer in the target language (English)."""
        return self._is_target

    @property
    def is_source(self) -> bool:
        """True if the learner must answer in the source language (Turkish). Always the opposite of is_target."""
        return not self._is_target

    @property
    def prompt(self) -> str:
        """The word/phrase shown to the learner."""
        return self.word.source if self.is_target else self.word.target

    @property
    def expected_answer(self) -> str:
        """The single 'canonical' answer to show the learner when revealing a correct answer."""
        return self.word.target if self.is_target else self.word.source

    @property
    def expected_word_alternatives(self) -> list[str]:
        """
        This word's other acceptable translations, if any were defined
        in words.csv. Purely informational — evaluate() ignores this
        entirely. What to do with it (accept it as also-correct, show
        it as a hint, log it differently, etc.) is up to whoever calls
        this, not this class.
        """
        return self.word.expected_word_alternatives if self.is_source else []

    def evaluate(self, answer: str):
        """
        Classify an answer as True (correct), False (wrong), or the
        string "blank" — the same three categories save_stat()
        already writes to statistics.csv. Only matched against the
        single canonical expected_answer; expected_word_alternatives
        are not considered here.
        """
        if answer == "" or answer == "!TimedOut!":
            return "blank"
        return _tr_lower(answer.strip()) == _tr_lower(self.expected_answer.strip())

    def save_to_stats(self, answer: str, level: int, file_path: str = "statistics.csv"):
        """
        Grade `answer`, record it into this question's Word's rolling
        rates, and append a row to statistics.csv matching the
        existing format:
            timestamp, target_word, source_word, given_answer, result, level

        A blank/timed-out answer counts as incorrect for the word's
        rolling accuracy, same as a wrong answer would.

        Returns the same True / False / "blank" result evaluate() does.
        """
        result = self.evaluate(answer)
        self.word.rates.record(result is True)

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        line = f"{timestamp},{self.word.target},{self.word.source},{answer},{result},{level}\n"
        with open(file_path, "a", encoding="UTF-8") as f:
            f.write(line)

        return result

    def __repr__(self) -> str:
        direction = "source\u2192target" if self.is_target else "target\u2192source"
        return f"Question(id={self.id}, word={self.word.target!r}, direction={direction!r})"
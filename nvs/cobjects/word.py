"""
word.py — OOP foundation for Coalide's vocabulary data.

Defines a Word class that wraps a single vocabulary entry, plus a CSV
loader that builds Word objects from words.csv. This module is
intentionally standalone: it does not modify main.py or change any
existing behavior. Wire it in wherever (and whenever) you like.

Naming convention (language-learning standard):
    target = the word in the language you are learning  (English)
    source = its meaning in your native language          (Turkish)
If you meant it the other way around, swap the two assignments in
Word.from_csv_row().

CSV format:
    Existing 5 columns (unchanged):
        target, source, word_type, sentence_half1, sentence_half2
    Optional columns appended at the end:
        past, v3                     (verb forms)
        expected_word_alternatives   (other acceptable translations,
                                       semicolon-separated)
    Rows without the new columns still parse fine — missing fields
    default to "" / an empty list. Because these are positional
    columns, to reach column 8 (alternatives) a row also needs columns
    6-7 (past, v3) present, even if left blank for non-verbs.
    Example:
        go,gitmek,verb,He can,to school every day,went,gone
        be,olmak,verb,He can,a teacher,was,been
        fast,hızlı,adjective,He runs very,every day,,,çabuk
        big,büyük,adjective,That's a,house,,,koca;iri
"""

from __future__ import annotations

from collections import deque


def _tr_lower(text: str) -> str:
    """
    Lowercase a string the way Turkish expects, not the way Python's
    default .lower() does.

    Turkish has two distinct letters Python conflates: dotted İ/i and
    dotless I/ı. Python's .lower() uses generic Unicode rules, so
    "İRİ".lower() comes out as "i̇ri̇" (an i plus an invisible combining
    dot), not "iri" — silently breaking any case-insensitive comparison
    against a learner-typed Turkish answer. Replacing the two I
    variants before lowering avoids that.
    """
    return text.replace("İ", "i").replace("I", "ı").lower()


class WordStats:
    """
    Tracks a learner's accuracy on a single word using a rolling
    window of their last N answers (10 by default).

    Older results automatically fall off as new ones come in, so a
    word the learner has since improved on isn't dragged down by
    mistakes from weeks ago. `correct` and `total` are still readable
    as before — they're just computed from the window now instead of
    being incremented forever.
    """

    DEFAULT_WINDOW = 10
    __slots__ = ("window", "_history")

    def __init__(self, history: list[bool] | None = None, window: int = DEFAULT_WINDOW):
        self.window = window
        self._history: deque[bool] = deque(history or [], maxlen=window)

    @property
    def total(self) -> int:
        return len(self._history)

    @property
    def correct(self) -> int:
        return sum(self._history)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def record(self, is_correct: bool) -> None:
        """Register one more answer. If already at `window` entries, the oldest one is dropped automatically."""
        self._history.append(bool(is_correct))

    def __repr__(self) -> str:
        return f"WordStats(correct={self.correct}, total={self.total}, accuracy={self.accuracy:.0%})"


class Word:
    """One vocabulary entry from words.csv."""

    def __init__(
        self,
        target: str,
        source: str,
        word_type: str = "",
        sentence: tuple[str, str] = ("", ""),
        past: str = "",
        v3: str = "",
        expected_word_alternatives: list[str] | None = None,
        rates: WordStats | None = None,
    ):
        self.target = target
        self.source = source
        self.word_type = word_type
        self.sentence = tuple(sentence) if sentence else ("", "")
        self.past = past
        self.v3 = v3
        # Defaulting to [] here, not in the signature, deliberately --
        # a mutable default argument (def __init__(..., alts=[])) would
        # be the SAME list object reused by every Word that didn't pass
        # one, so appending to one word's alternatives would silently
        # leak into every other word's. Building a fresh list per call
        # avoids that trap.
        self.expected_word_alternatives = list(expected_word_alternatives) if expected_word_alternatives else []
        self.rates = rates if rates is not None else WordStats()

    @property
    def is_verb(self) -> bool:
        return self.word_type.strip().lower() == "verb"

    @classmethod
    def from_csv_row(cls, parts: list[str]) -> "Word":
        """Build a Word from an already-split, already-stripped CSV row."""
        if len(parts) < 5:
            raise ValueError(f"Row has fewer than 5 fields: {parts}")

        target, source, word_type, half1, half2 = parts[0], parts[1], parts[2], parts[3], parts[4]
        past = parts[5] if len(parts) > 5 else ""
        v3 = parts[6] if len(parts) > 6 else ""
        alt_field = parts[7] if len(parts) > 7 else ""
        alternatives = [a.strip() for a in alt_field.split(";") if a.strip()]

        return cls(
            target=target,
            source=source,
            word_type=word_type,
            sentence=(half1, half2),
            past=past,
            v3=v3,
            expected_word_alternatives=alternatives,
        )

    def to_csv_row(self) -> list[str]:
        """Inverse of from_csv_row, useful for re-saving words.csv."""
        return [
            self.target,
            self.source,
            self.word_type,
            self.sentence[0],
            self.sentence[1],
            self.past,
            self.v3,
            ";".join(self.expected_word_alternatives),
        ]

    def example_sentence(self, fill: str | None = None) -> str:
        """Fill-in-the-blank sentence, e.g. 'He can _ to school every day'."""
        blank = fill if fill is not None else self.target
        first, second = self.sentence
        return f"{first} {blank} {second}".strip()

    def record_answer(self, is_correct: bool) -> None:
        """Convenience passthrough to self.rates.record()."""
        self.rates.record(is_correct)

    def __repr__(self) -> str:
        return f"Word(target={self.target!r}, source={self.source!r}, type={self.word_type!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Word):
            return NotImplemented
        return _tr_lower(self.target) == _tr_lower(other.target)

    def __hash__(self) -> int:
        return hash(_tr_lower(self.target))


def load_words(file_path: str = "words.csv") -> list[Word]:
    """
    Parse words.csv into a list of Word objects.

    Backward compatible: rows with the original 5 columns parse fine
    (optional fields default to "" / []); rows with 6, 7, or 8 columns
    also populate past/v3/expected_word_alternatives. Malformed rows
    (<5 columns) are skipped, matching the existing load_words()
    behavior in main.py.
    """
    words: list[Word] = []
    with open(file_path, "r", encoding="UTF-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            words.append(Word.from_csv_row(parts))
    return words


def to_legacy_tuple(words: list[Word]):
    """
    Optional bridge for gradual migration.

    Converts a list of Word objects back into the exact (final_words,
    f_words) structure main.py's own load_words() currently returns,
    so existing functions (quest(), get_audio(), etc.) keep working
    untouched if you decide to swap the loader before refactoring them.

        final_words = [{target: source}, ...]
        f_words     = [{target: [source, word_type, [half1, half2]]}, ...]
    """
    final_words = [{w.target: w.source} for w in words]
    f_words = [{w.target: [w.source, w.word_type, list(w.sentence)]} for w in words]
    return final_words, f_words
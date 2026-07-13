"""
This module contains practice mode.
"""

import msvcrt
from objects.word_obj import Word
from word_engine import get_words
from audio_engine import pronounce
from utils import cls
from random import shuffle
from time import sleep, monotonic


def _flush_input():
    """Discard any keystrokes buffered before practice starts."""
    while msvcrt.kbhit():
        msvcrt.getch()


def _interruptible_sleep(seconds):
    """Sleep up to `seconds`, returning True early if a key is pressed."""
    end = monotonic() + seconds
    while monotonic() < end:
        if msvcrt.kbhit():
            msvcrt.getch()
            return True
        sleep(0.05)
    return False


def main():
    try:
        words = get_words()
        shuffle(words)
        _flush_input()
        for word in words:
            cls(); print(f"Çıkmak için herhangi bir tuşa basınız.\n\n{word.target}")
            pronounce(word)
            if msvcrt.kbhit(): msvcrt.getch(); break
            cls(); print(f"{word.target} -> {word.source}\n\n{word.sentence[0]} {word.target} {word.sentence[1]}\n\n")
            pronounce(word, True)
            if _interruptible_sleep(3): break
        else:
            print("Pratik modu tamamlandı. Ana sayfaya dönmek için bir tuşa basın.")
            return input()
        print("\nPratik modu iptal edildi. Ana sayfaya dönmek için bir tuşa basın.")
        _flush_input()
        return input()
    except KeyboardInterrupt:
        print("\nPratik modu iptal edildi. Ana sayfaya dönmek için bir tuşa basın.")
        return input()

if __name__ == "__main__": main()

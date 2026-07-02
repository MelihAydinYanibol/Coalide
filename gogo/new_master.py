"""
This is for the main program, which is the main entry point for the application. It handles the core logic and flow of the program, including user interactions, data processing, and overall management of the application's functionality.
"""

from word_engine import save_words, get_words
from objects.word_obj import Word

words = get_words("words.json")

import random

random.shuffle(words)

for word in words:
    print(f"Language: {word.language}\nWord Type: {word.word_type}\nSentence: {word.sentence}\nTarget: {word.target}\nPast: {word.past}\nV3: {word.v3}\n")
from objects.word_obj import Word
from word_engine import save_words

Example_words = [Word(language="en", word_type="verb",source=["yürümek"], sentence=("He can", "to school every day"), target="walk", past="walked", v3="walked"),
                 Word(language="en", word_type="noun",source=["kitap"], sentence=("The", "is on the table"), target="book"),
                 Word(language="en", word_type="adjective",source=["güzel"], sentence=("you are", ""), target="beautiful")]



save_words(Example_words, "words.json")
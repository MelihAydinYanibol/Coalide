"""
This is for the main program, which is the main entry point for the application. It handles the core logic and flow of the program, including user interactions, data processing, and overall management of the application's functionality.

TO-DO:
- NO REPEAT WINDOW AND DAILY_NEW_WORD_CAP LOGIC WILL BE ADDED TO SM2.PY.
- Also infinite question support will be added.
"""


from word_engine import save_words, get_words
from objects.word_obj import Word
from objects.question_obj import Question
from sm2 import get_next_question, calculate_quality, update_sm2, save_progress


""" Example_words = [Word(language="en", word_type="verb", sentence=("He can", "to school every day"), target="walk", past="walked", v3="walked"),
                 Word(language="en", word_type="noun", sentence=("The", "is on the table"), target="book"),
                 Word(language="en", word_type="adjective", sentence=("The", "is very"), target="beautiful")]

save_words(Example_words, "words.json") """


# will make this a loop instead of a recursive function, but for now, this is fine. I will also add a way to exit the loop gracefully. 
def quest(current_question: Question = None):
    import time
    current_question = get_next_question() if current_question is None else current_question
    if current_question is None:
        print("No more questions due for review. Come back later!")
        import os
        os._exit(1)
    if type(current_question.prompt) == list: 
        import random
        prompt = random.choice(current_question.prompt)
    else: prompt = current_question.prompt
    print(f"Current question: {prompt}")
    start_time = time.time()
    answer = input("Your answer: ")
    if answer == current_question.expected_answer:
        print("Correct!")
        stat = True
    elif type(current_question.expected_answer) == list and answer in current_question.expected_answer:
        if current_question.expected_answer[0] == answer:
            print("Correct!")
            stat = True
        else:
            print(f"Correct, but not the answer wanted, try again...")
            quest(current_question)
    elif answer == "":
        print(f"Blank answer. The correct answer is: {current_question.expected_answer}")
        stat = None
    else:
        print(f"Incorrect. The correct answer is: {current_question.expected_answer}")
        stat = False
    end_time = time.time()
    time_taken = end_time - start_time
    if type(current_question.expected_answer) == list:
        _length = max(len(s) for s in current_question.expected_answer)
    else:
        _length = len(current_question.expected_answer)
    quality = calculate_quality(stat,_length, time_taken)
    update_sm2(current_question.word, quality)





    quest()  # Call quest again to get the next question

quest()
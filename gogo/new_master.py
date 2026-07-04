"""
This is for the main program, which is the main entry point for the application. It handles the core logic and flow of the program, including user interactions, data processing, and overall management of the application's functionality.

TO-DO:
- UI stuff, Telegram reporting, saving and reading stats will be added.
"""


from word_engine import save_words, get_words
from objects.word_obj import Word
from objects.question_obj import Question
from objects.balance_obj import load_data
from sm2 import get_next_question, calculate_quality, update_sm2

""" Example_words = [Word(language="en", word_type="verb", sentence=("He can", "to school every day"), target="walk", past="walked", v3="walked"),
                 Word(language="en", word_type="noun", sentence=("The", "is on the table"), target="book"),
                 Word(language="en", word_type="adjective", sentence=("The", "is very"), target="beautiful")]

save_words(Example_words, "words.json") """

# will make this a loop instead of a recursive function, but for now, this is fine. I will also add a way to exit the loop gracefully. 
def quest(user, current_question: Question = None):
    import time
    feed = []
    passthrough = False
    while True:
        if not passthrough:current_question = get_next_question(feed)
        else: passthrough = False
        if current_question is None:
            print("No more questions due for review. Come back later!")
            import sys
            sys.exit(0)
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
                passthrough = True
                continue
        elif answer == "":
            print(f"Blank answer. The correct answer is:")
            stat = None
        elif answer == "exit":
            break
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
        if stat:
            user.add_credits(50)
        update_sm2(current_question.word, quality)
        feed.append(current_question.word.id)

def redeem_flow(user):
    print(f"Your current balance is: {user.get_balance()} credits.")
 
    while True:
        raw_minutes = input("How many minutes would you like to redeem? (or 'cancel') ")
        if raw_minutes.strip().lower() == "cancel": return
        try:
            minutes = int(raw_minutes)
            if minutes <= 0:
                print("Please enter a positive number of minutes.")
                continue
            break
        except ValueError:
            print("That's not a valid number, try again.")
 
    print("When do you want this screentime for?")
    print("1: Today\n2: Tomorrow\n3: A specific date")
    while True:
        date_choice = input("Choose 1, 2, or 3: ")
        if date_choice == "1":
            target_date = date.today().isoformat()
            break
        elif date_choice == "2":
            target_date = (date.today() + timedelta(days=1)).isoformat()
            break
        elif date_choice == "3":
            raw_date = input("Enter date (YYYY-MM-DD): ")
            try:
                parsed = date.fromisoformat(raw_date)
                if parsed < date.today():
                    print("That date has already passed, pick another.")
                    continue
                target_date = raw_date
                break
            except ValueError:
                print("That doesn't look like a valid date (use YYYY-MM-DD), try again.")
        else:
            print("Please choose 1, 2, or 3.")
 
    cost = user.cost_for_minutes(minutes, target_date)
    print(f"Redeeming {minutes} minutes for {target_date} will cost {cost} credits.")
    confirm = input("Confirm? (y/n): ")
    if confirm.strip().lower() != "y":
        print("Cancelled -- no credits spent.")
        return
 
    pre_balance = user.get_balance()
    success = user.redeem_screentime(minutes, target_date)
 
    if success:
        print(f"Success! {minutes} minutes granted for {target_date}. Remaining balance: {user.get_balance()}")
    else:
        if pre_balance < cost:
            print(f"Not enough credits -- you have {pre_balance}, this costs {cost}.")
        else:
            print("Couldn't reach the screentime server right now -- your credits were NOT charged. Try again shortly.")



user = load_data("melih")

from datetime import date, timedelta
 
while True:
    print("Welcome to the COALIDE learning program!")
    opt = {1: "Start learning",2:"Redeem Credits", 3: "Exit"}
    for k,v in opt.items():
        print(f"{k}: {v}")
    choice = input("Please select an option: ")
    if choice == "1":
        quest(user)
    elif choice == "2":
        redeem_flow(user)
    elif choice == "3":
        print("Goodbye!")
        break
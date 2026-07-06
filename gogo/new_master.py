"""
This is for the main program, which is the main entry point for the application. It handles the core logic and flow of the program, including user interactions, data processing, and overall management of the application's functionality.

TO-DO:
- UI stuff, Telegram reporting, saving and reading stats will be added.
- All of the functions of the previous main.py will be moved here, and the old main.py will be deleted.
- LOWERCASE, upercase support.
"""

# Custom modules
from objects.word_obj import Word
from objects.question_obj import Question
from objects.balance_obj import load_data,User
from sm2 import get_next_question, calculate_quality, update_sm2

# Public Modules
from colorama import Fore, Style
import os
import sys
from datetime import date, timedelta
import requests

SOURCE="Türkçe"
TARGET="İngilizce"

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Environment variables may not load from .env file.")

if not os.path.exists(".env"):
    with open(".env","w",encoding="UTF-8") as f:
        f.write("ADMIN_PASSWORD=0000\nBOT_TOKEN=ENTER_YOUR_TOKEN_HERE\nCHAT_ID=YOUR_CHAT_ID_HERE\nPARENTAL_CONTROL_URL=http://IP-TO-YOUR-PCV2-SERVER:5005\nELEVENLABS_API_KEY=[]")
        f.close()
else:
    with open(".env", "r+", encoding="UTF-8") as f:
        content = f.read() # Read as one big string for easier searching
        
        if "ELEVENLABS_API_KEY" not in content:
            # Ensure we are at the end of the file
            f.seek(0, 2) 
            # Add a newline if the file doesn't end with one, then the key
            if content and not content.endswith('\n'):
                f.write('\n')
            f.write("ELEVENLABS_API_KEY=[]")

def lg(a="",b="",c="",d="",e="",f="",g="",h="",i="",j="",k="",l="",m="",n="",o="",p="",q="",r="",s="",t="",u="",v="",w="",x="",y="",z=""):
    global DEBUG
    DEBUG = False
    if len(sys.argv)>1:
        if sys.argv[1]=="-debug":
            DEBUG = True
            print(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z)

    return DEBUG

def cls():
    lg("cls()")
    if lg() != True:
        os.system('cls')

# will make this a loop instead of a recursive function, but for now, this is fine. I will also add a way to exit the loop gracefully. 
def quest(user, current_question: Question = None):
    import time
    feed = []
    passthrough = False
    question_number = 0
    while True:
        question_number += 1

        # Getting the question ready

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

        # Providing information

        example_sentence = f"{current_question.word.sentence[0]} {(len(current_question.word.target)*2)*'_'} {current_question.word.sentence[1]}"
        if current_question.word.total_attempts == 0:
            print(f"{prompt} kelimesi ilk kez soruluyor.")
            cc = Style.RESET_ALL
        else:
            cc = Fore.GREEN if current_question.word.rate >= 8 else Fore.YELLOW if current_question.word.rate >= 5 else Fore.LIGHTRED_EX if current_question.word.rate > 2 else Fore.RED
        print(f"{current_question.prompt[0] if type(current_question.prompt) == list else current_question.prompt} kelimesi için başarı oranınız: {cc}%{current_question.word.rate:.2f}{Style.RESET_ALL} ({current_question.word.correct_attempts}/{current_question.word.total_attempts})\n")
        print(f"Örnek Cümle: {example_sentence}")
        if current_question.is_source_wanted: filler = f"kelimesinin {SOURCE} karşılığı nedir?"
        else: filler = f"'kelimesinin {TARGET} karşılığı nedir?"
        print(f"{question_number}. '{prompt}' ({current_question.word.word_type}) {filler}\n")

        # Starting timer and asking for the answer

        start_time = time.time()
        answer = input("> ")

        # Evaluating the answer

        if answer == current_question.expected_answer:
            print(Fore.GREEN + f"Doğru!" + Style.RESET_ALL)
            stat = True
        elif type(current_question.expected_answer) == list and answer in current_question.expected_answer:
            if current_question.expected_answer[0] == answer:
                print(Fore.GREEN + f"Doğru!" + Style.RESET_ALL)
                stat = True
            else:
                print(Fore.LIGHTBLUE_EX + f"Doğru ama istenilen cevap bu değil. Tekrar dene. " + Style.RESET_ALL)
                passthrough = True
                continue
        elif answer == "":
            print(Fore.LIGHTRED_EX + f"Boş bırakıldı! Doğru cevap {current_question.expected_answer}" + Style.RESET_ALL)
            stat = None
        elif answer == "exit": break
        else:
            if type(current_question.expected_answer) == list:
                print(Fore.RED + f"Yanlış! Doğru cevap: {current_question.expected_answer[0]}" + Style.RESET_ALL)
            else:print(Fore.RED + f"Yanlış! Doğru cevap: {current_question.expected_answer}" + Style.RESET_ALL)
            stat = False
        end_time = time.time()


        # Calculating quality and updating the SM2 algorithm, also crediting

        time_taken = end_time - start_time
        if type(current_question.expected_answer) == list:
            _length = max(len(s) for s in current_question.expected_answer)
        else:
            _length = len(current_question.expected_answer)
        quality = calculate_quality(stat,_length, time_taken)
        if stat:
            user.add_credits(50)
        current_question.word.add_result((True if stat == True else False), is_blank=(stat is None))
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
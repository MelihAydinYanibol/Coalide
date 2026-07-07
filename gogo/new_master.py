"""
This is for the main program, which is the main entry point for the application. It handles the core logic and flow of the program, including user interactions, data processing, and overall management of the application's functionality.

TO-DO:
- UI stuff, Telegram reporting, saving and reading stats will be added.
- All of the functions of the previous main.py will be moved here, and the old main.py will be deleted.
- add credit resetting every week/add config for it
- backup data
- add cls's
"""

# Custom modules
from objects.word_obj import Word
from objects.question_obj import Question
from objects.balance_obj import load_data,User
from sm2 import get_next_question, calculate_quality, update_sm2, reload_words
from logger import lg


# Public Modules
from colorama import Fore, Style
import os
from datetime import date, timedelta
import copy
import json
import hashlib
import sys

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

def cls():
    lg("cls()")
    if lg() != True:
        os.system('cls')


def normalize_answer(s: str) -> str:
    # Python's default .lower() mishandles Turkish "İ"/"I" (produces "i̇"/"i"
    # instead of "i"/"ı"), so map those explicitly before lowercasing the rest.
    return s.strip().replace("İ", "i").replace("I", "ı").lower()

def _merge_missing_config_keys(current_config, default_config):
    """
    Add missing keys from default_config into current_config recursively.
    Returns True if any key was added.
    """
    changed = False
    for key, default_value in default_config.items():
        if key not in current_config:
            current_config[key] = copy.deepcopy(default_value)
            changed = True
        elif isinstance(default_value, dict):
            if not isinstance(current_config.get(key), dict):
                current_config[key] = copy.deepcopy(default_value)
                changed = True
            elif _merge_missing_config_keys(current_config[key], default_value):
                changed = True
    return changed

def get_config(default=False):
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    default_config = {
        "Daily_New_Word_Cap":15,
        "No_Repeat_Window":8,
        "Repo_Owner":"MelihAydinYanibol",
        "Repo_Name":"Coalide",
        "Update_Prereleases":False,
        "Source_Language":"Türkçe",
        "Target_Language":"İngilizce",
        "ElevenLabs_API_Key":[],
        "Parental_Control_URL":"http://IP-TO-YOUR-PCV2-SERVER:5005",
        "BASE_RATE_PER_MINUTE":5,
        "ESCALATION_PER_HOUR":0.5,
        "SPAM_PROTECTION":True,
        "INPUT_TIMEOUT":0,
        "Credit_Reset_Weekly":True
        
    }
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="utf-8") as f:
            import json
            json.dump(default_config, f, indent=4)
        config = default_config if default else None
    if default:
        return default_config
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            try: config = json.load(f)
            except: config = default_config # Fallback if file is corrupted
    if not isinstance(config, dict):
        config = copy.deepcopy(default_config)

    # Repair missing keys/sections and persist the updated config
    config_updated = _merge_missing_config_keys(config, default_config)
    if config_updated:
        with open(config_path, "w", encoding="UTF-8") as file:
            json.dump(config, file, indent=4)
    return config

def repair_config():
    lg("repair_config()")
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
    default_config = get_config(default=True)  # This will create the file if it doesn't exist
    current_config = get_config()  # Load current config (or default if file was missing/corrupted)
    if default_config != current_config:
        print(f"{Fore.YELLOW}Config file is different from the default. Checking for repair...{Style.RESET_ALL}")

    # get_config() already adds missing keys; this function is a manual trigger.
    changed = _merge_missing_config_keys(current_config, default_config)
    if changed:
        with open(config_path, "w", encoding="UTF-8") as file:
            json.dump(current_config, file, indent=4)
        print(f"{Fore.GREEN}Missing config keys were added successfully.{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Config is already complete. No missing keys found.{Style.RESET_ALL}")

def check_and_update_words(github_repo, github_token=None, local_file="words.json"):
    """
    Check GitHub for updated words.json and download if a newer version exists.
    
    Args:
        github_repo: Format: "username/repo" (e.g., "your-username/your-repo")
        github_token: Optional GitHub token for higher API rate limits
        local_file: Local path to words.json
    
    Returns:
        True if file was updated, False otherwise
    """
    lg(f"check_and_update_words_json({github_repo})")
    
    try:
        import requests
        
        # GitHub raw content URL
        raw_url = f"https://raw.githubusercontent.com/{github_repo}/main/words.json"
        
        # Optional: Use GitHub API to get file info with headers
        api_url = f"https://api.github.com/repos/{github_repo}/contents/words.json"
        headers = {}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Get remote file
        response = requests.get(raw_url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Could not fetch words.json from GitHub: {response.status_code}")
            return False
        
        remote_content = response.text
        
        # Check if local file exists
        if os.path.exists(local_file):
            with open(local_file, 'r', encoding="UTF-8") as f:
                local_content = f.read()
            
            # Compare file hashes
            local_hash = hashlib.md5(local_content.encode()).hexdigest()
            remote_hash = hashlib.md5(remote_content.encode()).hexdigest()
            
            if local_hash == remote_hash:
                lg("✓ words.json is up to date")
                return False
            else:
                lg("⚠ Newer version of words.json found on GitHub")
        
        # Write updated file
        with open(local_file, 'w', encoding="UTF-8") as f:
            f.write(remote_content)
            f.close()
        
        lg(f"✓ Updated words.json from GitHub")
        return True
        
    except Exception as e:
        lg(f"⚠ Error checking GitHub for updates: {e}")
        return False

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

        if get_config()["INPUT_TIMEOUT"] > 0:
            from inputimeout import inputimeout, TimeoutOccurred
            try:
                response = inputimeout(prompt="> ", timeout=get_config()["INPUT_TIMEOUT"])
            except TimeoutOccurred:
                print(Fore.LIGHTRED_EX + f"⚠ Süre doldu! Lütfen daha hızlı cevap verin." + Style.RESET_ALL)
                stat = None
                time_taken = get_config()["INPUT_TIMEOUT"]
        else:
            answer = input("> ")
        
        end_time = time.time()

        # Checking for spam.
        if get_config()["SPAM_PROTECTION"] and (end_time - start_time < 2):
            print(Fore.LIGHTRED_EX + "⚠ Çok hızlı cevap veriyorsun! Lütfen cevap vermeden önce düşün." + Style.RESET_ALL)
            passthrough = True
            continue

        # Evaluating the answer

        normalized_answer = normalize_answer(answer)
        if type(current_question.expected_answer) == list:
            normalized_expected = [normalize_answer(e) for e in current_question.expected_answer]
        else:
            normalized_expected = normalize_answer(current_question.expected_answer)

        if type(current_question.expected_answer) != list and normalized_answer == normalized_expected:
            print(Fore.GREEN + f"Doğru!" + Style.RESET_ALL)
            stat = True
        elif type(current_question.expected_answer) == list and normalized_answer in normalized_expected:
            if normalized_expected[0] == normalized_answer:
                print(Fore.GREEN + f"Doğru!" + Style.RESET_ALL)
                stat = True
            else:
                print(Fore.LIGHTBLUE_EX + f"Doğru ama istenilen cevap bu değil. Tekrar dene. " + Style.RESET_ALL)
                passthrough = True
                continue
        elif answer == "":
            correct_display = current_question.expected_answer[0] if type(current_question.expected_answer) == list else current_question.expected_answer
            print(Fore.LIGHTRED_EX + f"Boş bırakıldı! Doğru cevap {correct_display}" + Style.RESET_ALL)
            stat = None
        elif normalized_answer == "exit": break
        else:
            if type(current_question.expected_answer) == list:
                print(Fore.RED + f"Yanlış! Doğru cevap: {current_question.expected_answer[0]}" + Style.RESET_ALL)
            else:print(Fore.RED + f"Yanlış! Doğru cevap: {current_question.expected_answer}" + Style.RESET_ALL)
            stat = False

        # Pronuncing the word and the sentence
        from audio_engine import pronounce
        pronounce(current_question.word, False);time.sleep(.3) ;pronounce(current_question.word, True)

        print("[Enter] Devam Et\n[P] Kelimeyi Tekrar Dinle\n[S] Cümleyi Tekrar Dinle\n")
        while True:
            holder = str(input("> "))
            sys.stdout.write("\033[A\033[K")
            sys.stdout.flush()
            if holder.lower() in ["p","s"]: pronounce(current_question.word, True if holder.lower() == "s" else False)
            else: break

        # Calculating quality and updating the SM2 algorithm, also crediting

        time_taken = end_time - start_time
        if type(current_question.expected_answer) == list:
            _length = max(len(s) for s in current_question.expected_answer)
        else:
            _length = len(current_question.expected_answer)
        quality = calculate_quality(stat,_length, time_taken)
        if stat:
            user.add_credits(7)
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


def main():
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

def starter():
    lg(f"sys.argv: {sys.argv}\nPython version: {sys.version}\nOS: {os.name}\nPlatform: {sys.platform}\n")
    # backup_data()  # Backup data at the start of each loop iteration
    lg("Checking Config file"); repair_config()
    lg("Checking Words.json")
    if check_and_update_words(f"{get_config()['Repo_Owner']}/{get_config()['Repo_Name']}"):
        reload_words()
    main()

if __name__ == "__main__": starter()
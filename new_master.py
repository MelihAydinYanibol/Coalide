"""
This is for the main program, which is the main entry point for the application. It handles the core logic and flow of the program, including user interactions, data processing, and overall management of the application's functionality.

TO-DO:
- UI stuff, Telegram reporting, saving and reading stats will be added.
- All of the functions of the previous main.py will be moved here, and the old main.py will be deleted.
- backup data
"""

# Custom modules
from objects.word_obj import Word
from objects.question_obj import Question
from objects.balance_obj import load_data,User,check_weekly_reset,MINUTES_PER_DAY,is_within_credit_window
from sm2 import get_next_question, calculate_quality, update_sm2, reload_words
from utils import lg,get_config,repair_config,get_current_user,cls
try:
    from stats_menu import record_answer
except Exception:
    def record_answer(word, result): pass  # stats logging must never block the quiz


# Public Modules
from colorama import Fore, Style
import os
import shutil
import datetime
from datetime import date, timedelta
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


def has_internet(host="8.8.8.8", port=53, timeout=3) -> bool:
    """
    Returns True if the machine can reach the internet, by opening a quick TCP
    socket to Google's public DNS server (8.8.8.8:53). This is more reliable
    and faster than shelling out to `ping`, and works the same on every OS.
    """
    import socket
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
        return True
    except OSError:
        return False


def normalize_answer(s: str) -> str:
    # Drop a trailing comma the user may have typed by accident ("," sits right
    # next to Enter on the keyboard), then strip again in case of "word , ".
    s = s.strip().rstrip(",").strip()
    # Python's default .lower() mishandles Turkish "İ"/"I" (produces "i̇"/"i"
    # instead of "i"/"ı"), so map those explicitly before lowercasing the rest.
    return s.replace("İ", "i").replace("I", "ı").lower()


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
        cls() if not passthrough else None
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
            cc = Fore.GREEN if current_question.word.rate >= 80 else Fore.YELLOW if current_question.word.rate >= 50 else Fore.LIGHTRED_EX if current_question.word.rate > 20 else Fore.RED
        print(f"{current_question.prompt[0] if type(current_question.prompt) == list else current_question.prompt} kelimesi için başarı oranınız: {cc}%{current_question.word.rate:.2f}{Style.RESET_ALL} ({current_question.word.correct_attempts}/{current_question.word.total_attempts})\n")
        print(f"Örnek Cümle: {example_sentence}")
        if current_question.is_source_wanted: filler = f"kelimesinin {SOURCE} karşılığı nedir?"
        else: filler = f"kelimesinin {TARGET} karşılığı nedir?"
        print(f"{question_number}. '{prompt}' ({current_question.word.word_type}) {filler}\n")

        # Starting timer and asking for the answer
        start_time = time.time()

        if get_config()["INPUT_TIMEOUT"] > 0:
            from inputimeout import inputimeout, TimeoutOccurred
            try:
                answer = inputimeout(prompt="> ", timeout=get_config()["INPUT_TIMEOUT"])
            except TimeoutOccurred:
                print(Fore.LIGHTRED_EX + f"⚠ Süre doldu! Lütfen daha hızlı cevap verin." + Style.RESET_ALL)
                answer = ""
                stat = None
                time_taken = get_config()["INPUT_TIMEOUT"]
        else:
            answer = input("> ")
        
        end_time = time.time()

        # Checking for spam.
        if get_config()["SPAM_PROTECTION"] and (end_time - start_time < 2) and answer != "exit":
            print(Fore.LIGHTRED_EX + "⚠  Çok hızlı cevap veriyorsun! Lütfen cevap vermeden önce düşün." + Style.RESET_ALL)
            passthrough = True
            question_number -= 1
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

        print("[Enter] Devam Et\n[P] Kelimeyi Tekrar Dinle\n[S] Cümleyi Tekrar Dinle\n[Q] Çıkış Yap")
        while True:
            ex = False
            holder = str(input("> "))
            sys.stdout.write("\033[A\033[K")
            sys.stdout.flush()
            if holder.lower() in ["p","s"]: pronounce(current_question.word, True if holder.lower() == "s" else False)
            elif holder.lower() in ["exit","e","q"]: ex=True;break
            else: break
        # Calculating quality and updating the SM2 algorithm, also crediting

        time_taken = end_time - start_time
        if type(current_question.expected_answer) == list:
            _length = max(len(s) for s in current_question.expected_answer)
        else:
            _length = len(current_question.expected_answer)
        quality = calculate_quality(stat,_length, time_taken)
        if stat:
            if is_within_credit_window():
                user.add_credits(7)
            else:
                cfg = get_config()
                window_start = cfg.get("Credit_Window_Start", "07:00")
                window_end = cfg.get("Credit_Window_End", "22:00")
                print(Fore.YELLOW + f"Doğru cevap için kredi kazanılmadı: kredi kazanma saatleri {window_start}-{window_end} arası." + Style.RESET_ALL)
        record_answer(current_question.word.target, stat)
        current_question.word.add_result((True if stat == True else False), is_blank=(stat is None))
        update_sm2(current_question.word, quality)
        feed.append(current_question.word.id)
        if ex: ex=False; break

def redeem_flow(user):
    cls()
    print(f"Mevcut bakiyeniz: {user.get_balance()} kredi.")
 
    while True:
        raw_minutes = input("Kaç dakika almak istiyorsunuz? (veya 'iptal') \n\n")
        if raw_minutes.strip().lower() == "iptal": return
        try:
            minutes = int(raw_minutes)
            if minutes <= 0:
                print("Lütfen pozitif bir dakika sayısı girin.")
                continue
            if minutes > MINUTES_PER_DAY:
                print(f"Bir günde en fazla {MINUTES_PER_DAY} dakika (24 saat) vardır, daha fazlasını alamazsınız.")
                continue
            break
        except ValueError:
            print("Bu geçerli bir sayı değil, tekrar deneyin.")
 
    if get_config()["Credit_Reset_Weekly"]:
        week_end = date.today() + timedelta(days=6 - date.today().weekday())  # this week's Sunday -- credits reset Monday, so no redeeming past it
    else:
        week_end = date.max  # no weekly reset, so banking time ahead is allowed
    print("Bu ekran süresini ne zaman kullanmak istiyorsunuz?")
    print("1: Bugün\n2: Yarın\n3: Belirli bir tarih")
    while True:
        date_choice = input("1, 2 veya 3 seçin: ")
        if date_choice == "1":
            target_date = date.today().isoformat()
        elif date_choice == "2":
            target_date = (date.today() + timedelta(days=1)).isoformat()
        elif date_choice == "3":
            raw_date = input("Tarihi girin (YYYY-AA-GG): ")
            try:
                parsed = date.fromisoformat(raw_date)
                if parsed < date.today():
                    print("Bu tarih geçmişte kaldı, lütfen başka bir tarih seçin.")
                    continue
                target_date = raw_date
            except ValueError:
                if raw_date.strip().lower() in ["iptal","cancel","h","n"]: return
                print("Bu geçerli bir tarih gibi görünmüyor (YYYY-AA-GG biçimini kullanın), tekrar deneyin.")
                continue
        else:
            print("Lütfen 1, 2 veya 3 seçin.")
            continue
        if date.fromisoformat(target_date) > week_end:
            print(f"Krediler her pazartesi sıfırlanır, bu yüzden en geç bu haftanın sonu ({week_end.isoformat()}) için süre alabilirsiniz.")
            continue
        already_redeemed = user.redeemed_minutes_by_date.get(target_date, 0)
        if already_redeemed + minutes > MINUTES_PER_DAY:
            print(f"{target_date} için zaten {already_redeemed} dakika alınmış; bir gün {MINUTES_PER_DAY} dakikadan uzun olamaz (bu tarih için en fazla {MINUTES_PER_DAY - already_redeemed} dakika daha alabilirsiniz). Başka bir tarih seçin.")
            continue
        break
 
    cost = user.cost_for_minutes(minutes, target_date)
    print(f"{target_date} için {minutes} dakikayı kullanmak {cost} krediye mal olacak.")
    confirm = input("Onaylıyor musunuz? (e/h): ")
    if confirm.strip().lower() not in ("y", "e"):
        print("İptal edildi -- kredi harcanmadı.")
        return
 
    pre_balance = user.get_balance()
    success = user.redeem_screentime(minutes, target_date)
 
    if success:
        print(f"Başarılı! {target_date} için {minutes} dakika tanımlandı. Kalan bakiye: {user.get_balance()}")
    else:
        if pre_balance < cost:
            print(f"Yeterli krediniz yok -- sizde {pre_balance} kredi var, bunun maliyeti {cost} kredi.")
        else:
            print("Şu anda ekran süresi sunucusuna ulaşılamadı -- kredileriniz HARCANMADI. Lütfen biraz sonra tekrar deneyin.")


def backup_data():
    """
    Backs up important data files to a folder in the user's home directory.
    Creates a timestamped backup folder under ~/ProjectEnglish_Backups/.
    """
    lg("backup_data()")

    backup_files = [
        "words.json",
        "config.json",
        "progress.json",
        "current_user.json",
    ]

    user_home = os.path.expanduser("~")
    backup_root = os.path.join(user_home, ".ProjectEnglish_Backups")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder = os.path.join(backup_root, timestamp)

    project_dir = os.path.dirname(os.path.abspath(__file__))

    # Any file ending with "_data" (before the extension), e.g. melih_data.json
    for f in os.listdir(project_dir):
        full_path = os.path.join(project_dir, f)
        if os.path.isfile(full_path) and os.path.splitext(f)[0].endswith("_data") and f not in backup_files:
            backup_files.append(f)

    files_to_copy = [f for f in backup_files if os.path.exists(os.path.join(project_dir, f))]

    pronunciations_dir = os.path.join(project_dir, "pronunciations")
    has_pronunciations = get_config()["BACKUP_PRONUNCIATIONS"] and os.path.isdir(pronunciations_dir)

    if not files_to_copy and not has_pronunciations:
        lg("No data files found to back up.")
        return

    os.makedirs(backup_folder, exist_ok=True)

    copied = 0
    for filename in files_to_copy:
        src = os.path.join(project_dir, filename)
        dst = os.path.join(backup_folder, filename)
        try:
            shutil.copy2(src, dst)
            copied += 1
            lg(f"  Backed up: {filename}")
        except Exception as e:
            lg(f"  Failed to back up {filename}: {e}")

    if has_pronunciations:
        try:
            shutil.copytree(pronunciations_dir, os.path.join(backup_folder, "pronunciations"))
            copied += 1
            lg("  Backed up: pronunciations/")
        except Exception as e:
            lg(f"  Failed to back up pronunciations/: {e}")

    # Keep only the last 10 backups to avoid filling disk
    try:
        all_backups = sorted(
            [d for d in os.listdir(backup_root) if os.path.isdir(os.path.join(backup_root, d))]
        )
        while len(all_backups) > 10:
            oldest = os.path.join(backup_root, all_backups.pop(0))
            shutil.rmtree(oldest)
            lg(f"  Removed old backup: {oldest}")
    except Exception as e:
        lg(f"  Error cleaning old backups: {e}")

    print(f"{Fore.GREEN}Backed up {copied} item(s) to {backup_folder}{Style.RESET_ALL}")


def main():
    # If REQUIRE_INTERNET is enabled, refuse to start the quiz while offline.
    # This only blocks the question-asking (credit-earning) flow -- the menu,
    # redeem, practice and stats screens all remain usable offline.
    if get_config().get("REQUIRE_INTERNET", False) and not has_internet():
        print(Fore.RED + "İnternet bağlantısı yok. Soru sorma özelliği devre dışı (REQUIRE_INTERNET etkin)." + Style.RESET_ALL)
        lg("REQUIRE_INTERNET is enabled but no internet connection was detected. Aborting quiz start.")
        input("\nAna menüye dönmek için Enter'a basın...")
        return
    user = load_data(get_current_user())
    if get_config()["Credit_Reset_Weekly"]:
        if check_weekly_reset(user):
            print(f"{Fore.YELLOW}A new week has started, your balance has been reset to 0.{Style.RESET_ALL}")
    quest(user)
    """  while True:
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
                break """

def starter(get_ready:bool=False):
    global SOURCE, TARGET
    lg(f"sys.argv: {sys.argv}\nPython version: {sys.version}\nOS: {os.name}\nPlatform: {sys.platform}\n")
    # Check for cli commands first
    import cli
    backup_data()  # Backup data at the start of each loop iteration
    lg("Checking Config file"); repair_config()
    lg("Checking Words.json")
    if check_and_update_words(f"{get_config()['Repo_Owner']}/{get_config()['Repo_Name']}"):
        reload_words()
    # Loading the config
    config = get_config()  # Ensure config is loaded and repaired if needed
    SOURCE = config.get("Source_Language", "Türkçe")
    TARGET = config.get("Target_Language", "İngilizce")
    cls()
    if not get_ready:
        main()
    else: return True

if __name__ == "__main__": starter()
import os
import time
import json
import ast
import random
import datetime
import shutil
import subprocess
import ASCII.Animations.video
import ASCII.ASCII_LevelUp
import ASCII.ASCII_selection_menu
import ASCII.ASCII_start_menu
""" from googletrans import Translator """
from gtts import gTTS
import pyaudio
from pydub import AudioSegment
import sys
import copy
from colorama import Fore, Back, Style, init
import hashlib
import re
init(autoreset=True)

# Load .env file variables into os.environ before any function uses them
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
         
def restart_application():
    """
    Restarts the application using Windows subprocess.
    Compatible with Windows systems.
    """
    import subprocess
    try:
        # Get the current Python executable and script path
        python_executable = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Restart with the same arguments
        args = [python_executable, script_path] + sys.argv[1:]
        
        # On Windows, use CREATE_NEW_CONSOLE to spawn in new window
        if sys.platform.startswith('win'):
            subprocess.Popen(args, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(args)
        
        # Exit current process
        sys.exit(0)
    except Exception as e:
        print(f"Failed to restart application: {e}")
        sys.exit(1)

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

def backup_data():
    """
    Backs up important data files to a folder in the user's home directory.
    Creates a timestamped backup folder under ~/ProjectEnglish_Backups/.
    """
    lg("backup_data()")
    
    backup_files = [
        "statistics.csv",
        "daily_stats.csv",
        "analytics.csv",
        "words.csv",
        "config.json",
        "sent_tg_messages.json",
        ".env",
    ]
    
    user_home = os.path.expanduser("~")
    backup_root = os.path.join(user_home, ".ProjectEnglish_Backups")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_folder = os.path.join(backup_root, timestamp)
    
    # Check if there's anything to back up
    project_dir = os.path.dirname(os.path.abspath(__file__))
    files_to_copy = [f for f in backup_files if os.path.exists(os.path.join(project_dir, f))]
    
    if not files_to_copy:
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
    
    print(f"{Fore.GREEN}✓ Backed up {copied} file(s) to {backup_folder}{Style.RESET_ALL}")

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

def get_config(keys=None,default=False):
    lg(f"get_config({keys})")
    if keys is None:
        keys = []
        
    config_path = "config.json"
    
    # 1. Default config
    default_config = {
        "default_quiz_config": {
            "level_1_question_count": 20,
            "level_2_question_count": 50,
            "random_order": True,
            "pronounce_words": True,
            "send_telegram_message": True,
            "save_statistics": True,
        },
        "dummy_mode": {
            "dummy_mode": False,
            "dummy_question_count": 100,
            "send_telegram_message": True,
            "pronounce_words": True
        },
        "general": {
            "spam_answer_proof": True,
            "set_time_for_pc": True,
            "set_time_for_tomorrow": False,
            "answer_timeout": -1,
            "read_example_sentences": True,
            "elevenlabs_voice_id": "JBFqnCBsd6RMkjVDRZzb"
        }
    }
    if default:return default_config
    # 2. Handle File Loading/Creation
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="UTF-8") as file:
            json.dump(default_config, file, indent=4)
        config = default_config
    else:
        with open(config_path, "r", encoding="UTF-8") as file:
            try:
                config = json.load(file)
            except json.JSONDecodeError:
                config = default_config # Fallback if file is corrupted

    if not isinstance(config, dict):
        config = copy.deepcopy(default_config)

    # 2.5 Repair missing keys/sections and persist the updated config
    config_updated = _merge_missing_config_keys(config, default_config)
    if config_updated:
        with open(config_path, "w", encoding="UTF-8") as file:
            json.dump(config, file, indent=4)

    # 3. Return Logic
    if not keys:
        # Returns the DICTIONARY if no keys requested
        return config
    
    # Returns a LIST of values if specific keys are requested
    output = []
    for key in keys:
        if key in config:
            output.append(config[key])
            
    return output

def repair_config():
    lg("repair_config()")
    config_path = "config.json"
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
    

def check_and_update_words_csv(github_repo, github_token=None, local_file="words.csv"):
    """
    Check GitHub for updated words.csv and download if a newer version exists.
    
    Args:
        github_repo: Format: "username/repo" (e.g., "your-username/your-repo")
        github_token: Optional GitHub token for higher API rate limits
        local_file: Local path to words.csv
    
    Returns:
        True if file was updated, False otherwise
    """
    lg(f"check_and_update_words_csv({github_repo})")
    
    try:
        import requests
        
        # GitHub raw content URL
        raw_url = f"https://raw.githubusercontent.com/{github_repo}/main/words.csv"
        
        # Optional: Use GitHub API to get file info with headers
        api_url = f"https://api.github.com/repos/{github_repo}/contents/words.csv"
        headers = {}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Get remote file
        response = requests.get(raw_url, timeout=10)
        if response.status_code != 200:
            print(f"❌ Could not fetch words.csv from GitHub: {response.status_code}")
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
                lg("✓ words.csv is up to date")
                return False
            else:
                lg("⚠ Newer version of words.csv found on GitHub")
        
        # Write updated file
        with open(local_file, 'w', encoding="UTF-8") as f:
            f.write(remote_content)
            f.close()
        
        lg(f"✓ Updated words.csv from GitHub")
        return True
        
    except Exception as e:
        lg(f"⚠ Error checking GitHub for updates: {e}")
        return False

def set_config(ukey, key, value):
    lg(f"set_config({ukey},{key},{value})")
    config = get_config()
    if ukey in config:
        config[ukey][key] = value
        with open("config.json", "w", encoding="UTF-8") as file:
            json.dump(config, file, indent=4)
            file.close()
def analytics(get_set,time_finish,time_start,type):
    lg(f"analytics({get_set},{time_finish},{time_start},{type})")
    if get_set == "set":
        if not os.path.exists("analytics.csv"):
            with open("analytics.csv", "w", encoding="UTF-8") as file:
                file.close()
        with open("analytics.csv", "r", encoding="UTF-8") as file:
            lines = file.readlines()
            for line in lines[::-1]:
                if line.startswith(datetime.datetime.now().strftime("%Y-%m-%d")) and type in line:
                    return
            else:
                with open("analytics.csv", "a", encoding="UTF-8") as file:
                    file.write(f"{time_finish},{type},{time_start}\n")
                    file.close()
    elif get_set == "get":
        analytics_data = []
        if not os.path.exists("analytics.csv"):
            with open("analytics.csv", "w", encoding="UTF-8") as file:
                file.close()
        with open("analytics.csv", "r", encoding="UTF-8") as file:
            lines = file.readlines()
            for line in lines[::-1]:
                data = line.strip().split(",")
                if len(data) >= 3:
                    if data[0].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        analytics_data.append({
                            "time_finish": data[0],
                            "type": data[1],
                            "time_start": data[2]
                        })
        return analytics_data

def daily_stat(get_set, correct, wrong, blank, total,level,time_elapsed):
    lg(f"daily_stat({get_set},{correct},{wrong},{blank},{total},{level})")
    if get_set == "get":
        if not os.path.exists("daily_stats.csv"):
            return []
        with open("daily_stats.csv", "r", encoding="UTF-8") as f:
            return f.readlines()
    elif get_set == "set":
        if not os.path.exists("daily_stats.csv"):
            permission = "w"
        else: permission = "a"
        with open("daily_stats.csv",permission,encoding="UTF-8") as f:
            f.write(f"{datetime.datetime.now().strftime("%Y-%m-%d")},{correct},{wrong},{blank},{total},{level},{time_elapsed}\n")
            f.close()
            return f"{datetime.datetime.now().strftime("%Y-%m-%d")},{correct},{wrong},{blank},{total},{level},{time_elapsed}"


def safe_filename(name: str) -> str:
    # Windows-forbidden chars: <>:"/\|?*
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")


def load_words(file_path):
    lg(f"load_words({file_path})")
    final_words = []
    f_words = []
    with open(file_path, 'r', encoding="UTF-8") as file:
        for line in file:
            # Strip the whole line, then split, then strip each part
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5: continue 
            
            eng, tr, w_type, first_half_exsentence, second_half_exsentence  = parts[0], parts[1], parts[2], parts[3], parts[4]
            
            final_words.append({eng: tr})
            f_words.append({eng: [tr, w_type, [first_half_exsentence, second_half_exsentence]]})
    return final_words, f_words

def elabs_check_for_quota(api_key,word=""):
    from elevenlabs.client import ElevenLabs
    client = ElevenLabs(api_key=api_key)
    try:
        user = client.get_user()
        quota = user.subscription.character_limit - user.subscription.characters_used
        if quota <= len(word)*2:  # Assuming 1 character --(aprox)> 2 bytes of audio, adjustable if needed.
            return False
        else:   return True
    except Exception as e:
        lg(f"Error checking ElevenLabs quota: {e}")
        return True

def elabs_get_audio(word,language="en",t=1):
    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings
    api_keys_str = str(os.getenv("ELEVENLABS_API_KEY", "[]")).strip()
    lg(f"elabs_get_audio({word},{language},{t})")
    
    # Handle bracket notation: [key1, key2] or [single_key]
    if api_keys_str.startswith("[") and api_keys_str.endswith("]"):
        api_keys_str = api_keys_str[1:-1]  # Remove brackets
        # Split by comma for multiple keys
        api_keys = [k.strip().strip("'\"") for k in api_keys_str.split(",")]
        api_keys = [k for k in api_keys if k]  # Remove empty strings
    else:
        # Single key without brackets
        api_keys = [api_keys_str] if api_keys_str else []
    
    if len(api_keys) == 0:
        raise ValueError("ELEVENLABS_API_KEY is not set or empty.")

    lg(f"Found {len(api_keys)} ElevenLabs API key(s) in environment.")
    
    if len(api_keys) == 1:
        api_key = api_keys[0]
    else:
        for _api_key in api_keys:
            if elabs_check_for_quota(_api_key,word):
                api_key = _api_key
                break
        else:
            raise ValueError("All provided ElevenLabs API keys have insufficient quota. Falling back to gTTS.")
    
    
    voice_id = get_config()["general"].get("elevenlabs_voice_id", "JBFqnCBsd6RMkjVDRZzb")
    
    client = ElevenLabs(api_key=api_key)

    # Generate the audio
    audio_generator = client.text_to_speech.convert(
        voice_id=voice_id,
        output_format="mp3_44100_128",
        text=word,
        model_id="eleven_multilingual_v2",
        language_code=language,
        voice_settings=VoiceSettings(
            stability=0.85,
            similarity_boost=0.75,
            speed=0.82
        )
    )

    if not os.path.exists(f"pronunciations"):
        os.makedirs(f"pronunciations")

    # Save the stream to a file (lowercase for consistent cache lookup)
    filename = os.path.join("pronunciations", f"{safe_filename(word.lower())}.mp3")
    with open(filename, "wb") as f:
        for chunk in audio_generator:
            if chunk:
                f.write(chunk)
        f.close()
    return filename



def get_audio(word,lang_="en",t=1,server="11",sentence=False):
    lg(f"get_audio({word},{lang_},{t})")
    if sentence:
        # Sentences are not expected to exist in words.csv; trust provided target language.
        language = lang_
    else:
        words,typer = load_words('words.csv')
        normalized_word = word.lower()
        english_words = set()
        turkish_words = set()

        for word_ in words:
            key = next(iter(word_.keys()))
            val = next(iter(word_.values()))
            lg(key, word)
            english_words.add(key.lower())
            turkish_words.add(val.lower())

        if normalized_word in english_words:
            language = "en"
        elif normalized_word in turkish_words:
            language = "tr"
        else:
            lg("This word is not in the database.")
            return None

    if lang_ == language or sentence == True:
        lg(f"Detected language: {language}")
        filename = None
        if os.environ.get("ELEVENLABS_API_KEY") and server == "11":
            try:
                filename = (elabs_get_audio(word, language, t))
            except Exception as e:
                lg(f"Error generating audio with ElevenLabs: {e}")
                if t != 3:
                    lg("Falling back to gTTS...")
                    return get_audio(word, lang_, t+1,server="gTTS")
                else:
                    lg("Failed to generate audio after 3 attempts.")
                    return None
        else:
        # Generate audio using gTTS
            tts = gTTS(text=word, lang=language)
            os.makedirs("pronunciations", exist_ok=True)
            filename = f"pronunciations/{safe_filename(word.lower())}.mp3"
            tts.save(filename)
        if not filename:
            return None
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            if file_size == 0:
                if t != 3:
                    lg(f"Hata: {filename} boş (0 byte) oluşturuldu. Siliniyor...")
                    os.remove(filename)
                    if os.environ.get("ELEVENLABS_API_KEY") and server == "11":
                        try:
                            return elabs_get_audio(word, language, t+1)
                        except Exception as e:
                            lg(f"Error generating audio with ElevenLabs: {e}")
                            lg("Falling back to gTTS...")
                            return get_audio(word, lang_, t+1,server="gTTS")
                    else:
                        return get_audio(word,lang_,t+1)
                else:
                    lg(f"Hata: {filename} 3 defa indirildi ama başarısız olundu.")
            else:
                lg(f"Pronunciation audio saved as {filename}")
                return filename
    else:
        lg(f"Language mismatch: word is in {language}, but lang_ is {lang_}. No audio generated.")
        return None
    
def play_audio(filename):
    lg(f"play_audio({filename})")
    # Backwards-compatible wrapper that uses the resilient player below
    return play_audio_with_unplug_handling(filename)


def is_output_device_available():
    """Return True if a default output device appears available to PyAudio."""
    pa = None
    try:
        pa = pyaudio.PyAudio()
        # This will raise if no default output device exists
        pa.get_default_output_device_info()
        return True
    except Exception:
        return False
    finally:
        try:
            if pa is not None:
                pa.terminate()
        except Exception:
            pass


def play_audio_with_unplug_handling(filename, wait_seconds=5, poll_interval=0.5):
    """Play `filename` with basic handling for unplugged audio devices.

    Behavior:
    - If no output device is present, poll for up to `wait_seconds` for it to reappear.
    - Attempt playback; on error try one quick recovery if device comes back.
    - If recovery fails, skip playback and log to stdout.
    """
    lg(f"play_audio_with_unplug_handling({filename})")

    # If no device right now, wait briefly for it to come back
    if not is_output_device_available():
        start = time.time()
        while time.time() - start < wait_seconds:
            time.sleep(poll_interval)
            if is_output_device_available():
                break
        else:
            print(f"Audio device unavailable — skipping playback: {filename}")
            return

    # Try playback; catch runtime errors (e.g., device removed mid-play)
    try:
        import pyglet
        from time import sleep
        from mutagen.mp3 import MP3

        music = pyglet.media.load(filename, streaming=False)
        try:
            audio = MP3(filename)
            duration = audio.info.length
        except Exception:
            duration = music.duration

        music.play()
        sleep(duration)
    except Exception as e:
        print(f"Playback error: {e}. Attempting quick recovery...")
        # If device reappears, try once more
        if is_output_device_available():
            try:
                import pyglet
                from time import sleep
                from mutagen.mp3 import MP3

                music = pyglet.media.load(filename, streaming=False)
                try:
                    audio = MP3(filename)
                    duration = audio.info.length
                except Exception:
                    duration = music.duration

                music.play()
                sleep(duration)
            except Exception as e2:
                print(f"Recovery failed: {e2}. Skipping playback.")
        else:
            print("No output device found after error. Skipping playback.")

def get_folder(folder="pronunciations"):
    lg(f"get_folder({folder})")
    try:
        # Check if the folder exists
        if not os.path.exists(folder):
            lg(f"Folder '{folder}' does not exist.")
            return []
        # List all files in the folder
        files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        lg(f"Files in '{folder}': {files}")
        return files
    except Exception as e:
        lg(f"An error occurred while listing files: {e}")
        return []

def pronounce_word(word, lang_="en",sentence=False):
    lg(f"pronounce_word({word},{lang_})")
    files = get_folder("pronunciations")
    for file in files:
        file = safe_filename(file)
        if file.lower() == f"{safe_filename(word.lower())}.mp3":
            lg(f"Playing existing pronunciation for '{word}'.")
            play_audio(os.path.join("pronunciations", file))
            return
    else:
        audio_file = get_audio(word, lang_, sentence=sentence)
        if audio_file:
            play_audio(audio_file)

def detect_language(text):
    lg(f"detect_language({text})")
    words,typer = load_words('words.csv')
    for word in words:
        key = next(iter(word.keys()))
        val = next(iter(word.values()))
        if text.lower() == key.lower():
            return "en"
        elif text.lower() == val.lower():
            return "tr"

""" def admin_interface(buffer=True):
    print("heia")
    main() """

def admin_login_interface(just_auth=False,legacy_selection_menu=False):
    lg(f"admin_login_interface({just_auth},{legacy_selection_menu})")
    cls()
    import getpass
    
    admin_password = os.getenv("ADMIN_PASSWORD")
    password = getpass.getpass("Admin Şifresini giriniz: ")
    if password == admin_password:
        if just_auth == False:
            """ admin_ = admin_console() """
        else:
            return True
    else:
        for i in range(3):
            cls()
            print("Geçersiz şifre! {} saniye içinde ana menüye dönülüyor...".format(3-i))
            time.sleep(i)
        main()

def save_stat(time_,word,translation,answer,correct,level):
    lg(f"save_stat({time_},{word},{translation},{answer},{correct},{level})")
    stat_line = f"{time_},{word},{translation},{answer},{correct},{level}\n"
    with open("statistics.csv", "a", encoding="UTF-8") as file:
        file.write(stat_line)
        file.close()

def get_question_answer(text, timeout_time):
    if timeout_time == -1:
        response = str(input(text))
    else:
        from inputimeout import inputimeout, TimeoutOccurred
        try:
            response = inputimeout(prompt=text, timeout=timeout_time)
        except TimeoutOccurred:
            response = "!TimedOut!"
    return response

def quest(question_amount, wordlist, word_progression, dd, typer, quiz_config, current_level,exsentences=[]):
    lg(f"{question_amount},{wordlist},{word_progression},{dd},{typer},{quiz_config},{current_level},{exsentences}")
    if question_amount > len(wordlist):
        question_amount = len(wordlist)

    timeout_time = get_config(["general"])[0].get("answer_timeout")
    selected_words = random.sample(wordlist, question_amount)

    for i, word in enumerate(selected_words):
        try:
            cls()
            
            time_ = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            type_of_word = next((d[word][1] for d in typer if word in d), "Not found")
            ex_sent = next((d[word][2] for d in typer if word in d), ["", ""])
            first_half_exsentence, second_half_exsentence = ex_sent
            print(f"Örnek Cümle : {first_half_exsentence} {(len(word)*2-1)*'_'} {second_half_exsentence}")
            if random.randint(1,2) == 1:
                # --- Logic for Turkish -> English ---
                if word in word_progression:
                    basari = word_progression[word][2]*100
                    if basari >= 80: cc = Fore.GREEN
                    elif basari >= 50: cc = Fore.YELLOW
                    elif basari > 20: cc = Fore.LIGHTRED_EX
                    else: cc = Fore.RED
                try:
                    if word in word_progression:
                        basari = int(basari)
                        print(f"{word} kelimesi için başarı oranınız: ",end="")
                        print(f"{cc}%{basari:.2f}{Style.RESET_ALL}",end="")
                        print(f" ({word_progression[word][0]}/{word_progression[word][1]})\n")      
                    else: print(f"{word} kelimesi ilk kez soruluyor.\n")
                except Exception as e: 
                    if word in word_progression:
                        print(f"Hata : {e}")
                if get_config(["general"])[0].get("spam_answer_proof"):
                    ss_time = time.time()
                    diff = 0
                else: ss_time = None; diff = None
                if ss_time == None and diff == None:
                    answer = get_question_answer(f"{i+1}. '{word}' ({type_of_word}) kelimesinin Türkçe karşılığı nedir? ",timeout_time)
                while ss_time != None and diff != None and diff < 2:
                    answer = get_question_answer(f"{i+1}. '{word}' ({type_of_word}) kelimesinin Türkçe karşılığı nedir? ",timeout_time)
                    diff = time.time() - ss_time
                
                if answer.lower() == dd[word].lower():
                    print(Fore.GREEN+"\nDoğru!"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,True,current_level)
                elif answer == "":
                    print(Fore.LIGHTRED_EX+f"Boş bırakıldı! Doğru cevap: {dd[word]}"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,"blank",current_level)
                elif answer.lower() == "exit":
                    os._exit(1)
                elif answer == "!TimedOut!":
                    print(Fore.RED+f"Süre doldu! ({timeout_time} sn) Cevap: {dd[word]}"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,"blank",current_level)
                else:
                    print(Fore.RED+f"Yanlış! Doğru cevap: {dd[word]}"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,False,current_level)
            else:
                # --- Logic for English -> Turkish ---
                if word in word_progression:
                    basari = word_progression[word][2]*100
                    if basari >= 80: cc = Fore.GREEN
                    elif basari >= 50: cc = Fore.YELLOW
                    elif basari > 20: cc = Fore.LIGHTRED_EX
                    else: cc = Fore.RED
                try:
                    if word in word_progression:
                        basari = int(basari)
                        print(f"{dd[word]} kelimesi için başarı oranınız: ",end="")
                        print(f"{cc}%{basari:.2f}{Style.RESET_ALL}",end="")
                        print(f" ({word_progression[word][0]}/{word_progression[word][1]})\n")      
                    else: print(f"{dd[word]} kelimesi ilk kez soruluyor.\n")
                except Exception as e: 
                    if word in word_progression:
                        print(f"Hata : {e}")

                if get_config(["general"])[0].get("spam_answer_proof"):
                    ss_time = time.time()
                    diff = 0
                else: ss_time = None; diff = None
                if ss_time == None and diff == None:
                    answer = get_question_answer(f"{i+1}. '{dd[word]}' ({type_of_word}) kelimesinin İngilizce karşılığı nedir? ",timeout_time)
                while ss_time != None and diff != None and diff < 2:
                    answer = get_question_answer(f"{i+1}. '{dd[word]}' ({type_of_word}) kelimesinin İngilizce karşılığı nedir? ",timeout_time)
                    diff = time.time() - ss_time
                
                
                if answer.lower() == word.lower():
                    print(Fore.GREEN+"\nDoğru!"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,True,current_level)
                elif answer == "":
                    print(Fore.LIGHTRED_EX+f"Boş bırakıldı! Doğru cevap: {word}"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],"","blank",current_level)
                elif answer.lower() == "exit":
                    os._exit(1)
                elif answer == "!TimedOut!":
                    print(Fore.RED+f"Süre doldu! ({timeout_time} sn) Cevap: {word}"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,"blank",current_level)
                else:
                    print(Fore.RED+f"Yanlış! Doğru cevap: {word}"+Style.RESET_ALL)
                    save_stat(time_,word,dd[word],answer,False,current_level)  
            
            if quiz_config.get("pronounce_words") == True:
                print("\n\nOkunuyor...")
                pronounce_word(word)
            if get_config(["general"])[0].get("read_example_sentences") == True:
                pronounce_word(f"{first_half_exsentence.strip()} {word} {second_half_exsentence.strip()}", lang_="en",sentence=True)

            print("[Enter] Devam Et\n[P] Kelimeyi Tekrar Dinle\n[S] Cümleyi Tekrar Dinle\n")
            while True:
                holder = str(input("> "))
                sys.stdout.write("\033[A\033[K")
                sys.stdout.flush()
                if holder.lower() == "p":
                    pronounce_word(word)
                elif holder.lower() == "s":
                    pronounce_word(f"{first_half_exsentence.strip()} {word} {second_half_exsentence.strip()}", lang_="en",sentence=True)
                else: break
        except Exception as e:
            lg(f"Error in quest function for word '{word}': {e}")
            print(f"{Fore.RED}An error occurred while processing the word '{word}'. Skipping to the next word.{Style.RESET_ALL}")
            time.sleep(2)
            continue

### IN BETA ADMIN INTERFACE ###
""" loop = True
while loop:
    cls()
    tim = int(datetime.datetime.now().strftime("%H"))
    txt = ""
    if 6 > tim > 11: txt="Günaydın"
    elif 12 > tim > 18: txt="Tünaydın"
    elif 18 > tim > 1: txt="İyi Akşamlar"
    else:txt = "İyi Geceler"
    print(f"{txt} {username}!\n\n{Fore.LIGHTBLUE_EX}Admin Arayüzü{Style.RESET_ALL}")
    print("1-Çıkış") """
####################################


## MAIN ##


def main(quiz_config={}, legacy_start_menu=False,mode="play"):
    global LEVEL_1_PASSED,LEVEL_2_PASSED, DEBUG
    lg(f"main({quiz_config},{legacy_start_menu},{mode})")
    options = {"1": "Başla","2": "Admin Girişi"}
    if legacy_start_menu:
        print("Coalide'a hoş geldiniz!\n")
        try:
            if sys.argv[1] == "-debug":
                
                print(Fore.RED + "DEBUG MODU AKTİF" + Style.RESET_ALL + "\n")
        
        except:pass
    
        
        print("Seçenekler:\n")
        for key, value in options.items():
            print(f"{key}. {value}")
        choice = input("\n\n> ")
    else:
        try:
            choice = c_
        except:choice = "play"

    if choice == list(options.keys())[1] or choice == "admin" or mode == "admin":
        admin_login_interface()
    elif choice == list(options.keys())[0] or choice == "play" or mode == "play":
        try:
            if not DEBUG:
                c__ = ASCII.ASCII_selection_menu.main()
                cls()
                legacy_selection_menu = False
            else: raise
        except:
            print("An error occurred in selection_menu. Falling back to legacy start menu.")
            legacy_selection_menu = True
        
        choices = {"1": "Varsayılan modda başlat", "2": "Admin kontrolü"}

        if legacy_selection_menu:
            print("Seçenekler:\n")
            for key, value in choices.items():
                print(f"{key}. {value}")
            choice_ = input("\n\n> ")
        else:
            choice_ = c__
            if choice_ == "exit":
                print("Çıkış yapılıyor...")
                os._exit(1)
        if choice_ == list(choices.keys())[1] or choice_ == "admin":
            auth = admin_login_interface(just_auth=True,legacy_selection_menu=legacy_selection_menu)
            cls()
            if auth:
                print("Admin kontrolüne hoş geldiniz!")
                default_config = get_config(["default_quiz_config"])
                if quiz_config == {}:
                    temp_config = copy.deepcopy(default_config)
                else:
                    temp_config = [quiz_config]
                print("Mevcut quiz yapılandırması:\n")
                for key, value in temp_config[0].items():
                    for key_, value_ in default_config[0].items():
                        if key == key_:
                            if value != value_:txt = f" (Varsayılan : {value_})"
                            else:txt = ""
                            
                            print(f"{key}: {value}{txt}")

                loop=True
                while loop == True:
                    command = input("\n\n> ")
                    if command.startswith("set "):
                        if "--help" in command:
                            print("set komutu, geçici quiz yapılandırmasını güncellemek için kullanılır. Kullanım: set <anahtar> <değer>")
                            print("Anahtarlar:")
                            for key in temp_config[0].keys():
                                print(f"- {key}")
                        else:
                            try:
                                _, key, value = command.split(" ", 2)
                                if key in temp_config[0]:
                                    if value.lower() in ["true", "false"]:
                                        value = value.lower() == "true"
                                    elif value.isdigit():
                                        value = int(value)
                                    temp_config[0][key] = value
                                    print(f"{key} başarıyla {value} olarak güncellendi.")
                                    print(temp_config)
                                else:
                                    print(f"Geçersiz anahtar: {key}")
                            except ValueError:
                                print("Geçersiz komut formatı. Kullanım: set <anahtar> <değer>")
                    elif command.startswith("dset "):
                        if "--help" in command:
                            print("dset komutu, varsayılan quiz yapılandırmasını güncellemek için kullanılır. Kullanım: dset <anahtar> <değer>")
                            print("Anahtarlar:")
                            for key in default_config[0].keys():
                                print(f"- {key}")
                        else:
                            try:
                                print("dset <anahtar> <değer>: Varsayılan quiz yapılandırmasını günceller.")
                                _, key, value = command.split(" ", 2)
                                if key in default_config[0]:
                                    if value.lower() in ["true", "false"]:
                                        value = value.lower() == "true"
                                    elif value.isdigit():
                                        value = int(value)
                                    default_config[0][key] = value
                                    temp_config[0][key] = value
                                    set_config("default_quiz_config", key, value)
                                    print(f"{key} başarıyla {value} olarak güncellendi.")
                                else:
                                    print(f"Geçersiz anahtar: {key}")
                            except ValueError:
                                print("Geçersiz komut formatı. Kullanım: dset <anahtar> <değer>")

                    elif command == "show":
                        if "--help" in command:
                            print("show komutu, mevcut quiz yapılandırmasını gösterir. Kullanım: show")
                        else:
                            print("Mevcut quiz yapılandırması:\n")
                            for key, value in temp_config[0].items():
                                for key_, value_ in default_config[0].items():
                                    if key == key_:
                                        if value != value_:txt = f" (Varsayılan : {value_})"
                                        else:txt = ""
                                        print(value,value_,txt,key,key_)
                                        print(f"{key}: {value}{txt}")
                    elif command == "exit":
                        if "--help" in command:
                            print("exit komutu, admin kontrolünden çıkar ve ana menüye döner. Kullanım: exit")
                        else:
                            loop = False
                            if temp_config:
                                main(quiz_config=temp_config[0])
                            else:
                                main(quiz_config=default_config[0])
                            return
                    elif command == "cls" or command == "clear":
                        if "--help" in command:
                            print("cls/clear komutu, ekranı temizler. Kullanım: cls/clear")
                        else:
                            cls()
                    elif command == "help":
                        print("Komutlar:")
                        print("- set <anahtar> <değer>: Geçici quiz yapılandırmasını günceller.")
                        print("- dset <anahtar> <değer>: Varsayılan quiz yapılandırmasını günceller.")
                        print("- show: Mevcut quiz yapılandırmasını gösterir.")
                        print("- cls/clear: Ekranı temizler.")
                        print("- help: Komut listesini gösterir.")
                        print("- exit: Admin kontrolünden çıkar ve ana menüye döner.")
                    else:
                        print("Geçersiz komut! Komutlar: set <anahtar> <değer>, dset <anahtar> <değer>, show, cls/clear, help, exit")   

                
        if choice_ == list(choices.keys())[0] or choice_ == "dstart":
            if quiz_config == {}:
                quiz_config = get_config(["default_quiz_config"])[0]
            
            question_amount = 0

            # GET PROGRESSION DATA TO CHOOSE WETHER TO START LEVEL 1 OR 2
            analytics_data = analytics("get",None,None,None)

            ### LEVEL 1 ###
            if analytics_data == []:
                """ known_words = ["give","go","have","make","say","see","take","want"] """
                known_words = []
                word_progression = {}
                if os.path.exists("statistics.csv"):
                    with open("statistics.csv", "r") as f:
                        lines = f.readlines()
                        words = []
                        for line in lines[::-1]:
                            data = line.strip().split(",")
                            if len(data) >= 5:
                                if data[1] not in words:
                                    words.append(data[1])
                        for word in words:
                            amount_counter = correct_counter = 0
                            for line in lines[::-1]:
                                data = line.strip().split(",")
                                if len(data) >= 5 and data[1] == word:
                                    if amount_counter > 5:
                                        break
                                    amount_counter += 1
                                    if data[4] == "True":
                                        correct_counter += 1
                                if amount_counter == correct_counter == 5:
                                    if word not in known_words:
                                        known_words.append(word)
                            
                            word_progression[word] = [correct_counter,amount_counter,correct_counter / amount_counter if amount_counter > 0 else 0]
                    f.close()

                all_words,typer = load_words("words.csv")
                start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                dd = {}
                for word_dict in all_words:
                    dd[list(word_dict)[0]] = word_dict.get(list(word_dict)[0])
                if len(known_words) < quiz_config["level_1_question_count"]:
                    question_amount = len(known_words)
                else:
                    question_amount = quiz_config["level_1_question_count"]
                lg(known_words)
                time_of_quiz_start_1 = time.time()
                quest(question_amount=question_amount,wordlist=known_words,word_progression=word_progression,dd=dd,typer=typer,quiz_config=quiz_config,current_level=1)
                analytics("set",datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),start_time,"level_1_passed")
                if not os.path.exists("statistics.csv"):
                    with open("statistics.csv","w",encoding="UTF-8") as f:f.close()
                with open("statistics.csv", "r", encoding="UTF-8") as f:
                    correct_counter_ = wrong_counter_ = blank_counter_ = total_counter_ = 0
                    lines = f.readlines()
                    todays=[]
                    for line in lines[::-1]:
                        if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                            if line.strip() not in todays:
                                todays.append(line.strip())
                    time.sleep(.3)
                    for line in todays:
                        if line.split(",")[5] == "1":
                            """ print(line)
                            print(line.split(","))
                            print(line.split(",")[4])
                            time.sleep(999) """
                            if line.split(",")[4] == "True":
                                correct_counter_ += 1
                            elif line.split(",")[4] == "False":
                                wrong_counter_ += 1
                            else: blank_counter_ += 1
                            total_counter_ += 1
                    f.close()
                analytics_data = analytics("get",None,None,None)
                daily_stat("set",correct_counter_,wrong_counter_,blank_counter_,total_counter_,level=1,time_elapsed=time.time()-time_of_quiz_start_1)
                if not DEBUG:
                    """ try: """
                    ASCII.ASCII_LevelUp.main(f"{correct_counter_/total_counter_*100:.2f}",correct_counter_,total_counter_) if total_counter_ != 0 else ASCII.ASCII_LevelUp.main(f"0",correct_counter_,total_counter_)
                    cls()
                    from random import randint
                    indx = randint(0,len(ASCII.Animations.video.get_files())+1)
                    if indx >= len(ASCII.Animations.video.get_files()):
                        """ chose_ani() """
                    else:
                        ASCII.Animations.video.play(ASCII.Animations.video.get_files()[indx])
                    """ except:print("HELP ME") """
            if analytics_data != []:
                for data in analytics_data:
                    if data["type"] == "level_1_passed" and data["time_finish"].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        LEVEL_1_PASSED = True
                        break
                else:
                    LEVEL_1_PASSED = False
                for data in analytics_data:
                    if LEVEL_1_PASSED == True and data["type"] == "level_2_passed" and data["time_finish"].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        LEVEL_2_PASSED = True
                        break
                else:
                    LEVEL_2_PASSED = False
            if analytics_data != [] or question_amount == 0:
                if question_amount == 0:
                    LEVEL_1_PASSED = True
                d = analytics("get",None,None,None)
                for data in d:
                    if data["type"] == "level_2_passed" and data["time_finish"].startswith(datetime.datetime.now().strftime("%Y-%m-%d")):
                        LEVEL_2_PASSED = True
                        break
                else:
                    LEVEL_2_PASSED = False
                if LEVEL_1_PASSED == True and LEVEL_2_PASSED == False:
                    if question_amount != 0: 
                        print("Seviye 1'i geçtiğiniz tespit edildi! Seviye 2'ye geçiliyor...")
                    else: 
                        print("Seviye 1'de yeterli veri bulunamadığı için Seviye 2'ye geçiliyor...")

                    time.sleep(3);  cls()

                    ### LEVEL 2 ###
                    unknown_words = []
                    word_progression = {}
                    if not os.path.exists("statistics.csv"):
                        with open("statistics.csv", "w") as f:
                            f.close()
                    stat_words = []
                    if os.path.exists("statistics.csv"):
                        with open("statistics.csv", "r") as f:
                            lines = f.readlines()
                            words = []
                            for line in lines[::-1]:
                                data = line.strip().split(",")
                                if len(data) >= 5:
                                    if data[1] not in words:
                                        words.append(data[1])
                            for word in words:
                                amount_counter = 0
                                correct_counter = 0
                                for line in lines[::-1]:
                                    data = line.strip().split(",")
                                    if len(data) >= 5 and data[1] == word:
                                        if amount_counter > 5:
                                            break
                                        amount_counter += 1
                                        if data[4] == "True":
                                            correct_counter += 1
                                    if amount_counter != correct_counter and correct_counter != 5:
                                        if word not in unknown_words:
                                            unknown_words.append(word)
                                    if word not in stat_words:
                                        stat_words.append(word)
                                
                                word_progression[word] = [correct_counter,amount_counter,correct_counter / amount_counter if amount_counter > 0 else 0]
                        f.close()
                    start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
                    all_words,typer = load_words("words.csv")
                    for word in all_words:
                        if list(word.keys())[0] not in stat_words:
                            if list(word.keys())[0] not in unknown_words:
                                unknown_words.append(list(word.keys())[0])
                    dd = {}
                    for word_dict in all_words:
                        dd[list(word_dict)[0]] = word_dict.get(list(word_dict)[0])
                    if len(unknown_words) < quiz_config["level_2_question_count"]:
                        question_amount = len(unknown_words)
                    else:
                        question_amount = quiz_config["level_2_question_count"]

                    lg(unknown_words)
                    time_of_quiz_start_2 = time.time()
                    quest(question_amount=question_amount,wordlist=unknown_words,word_progression=word_progression,dd=dd,typer=typer,quiz_config=quiz_config,current_level=2)
                    LEVEL_2_PASSED = True
                    analytics("set",datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),start_time,"level_2_passed")
                    """ daily_stat("set,") """
                    with open("statistics.csv", "r", encoding="UTF-8") as f:
                        correct_counter__ = wrong_counter__ = blank_counter__ = total_counter__ = 0
                        lines = f.readlines()
                        todays=[]
                        for line in lines[::-1]:
                            if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                                if line.strip() not in todays:
                                    todays.append(line.strip())
                        time.sleep(.3)
                        for line in todays:
                            lg(line.split(","))
                            if line.split(",")[5] == "2":
                                """ print(line)
                                print(line.split(","))
                                print(line.split(",")[4])
                                time.sleep(999) """
                                """ print(line.split(",")) """
                                if line.split(",")[4] == "True":
                                    
                                    correct_counter__ += 1
                                    lg(+1)
                                elif line.split(",")[4] == "False":
                                    wrong_counter__ += 1
                                    lg(-1)
                                else: blank_counter__ += 1
                                total_counter__ += 1
                        f.close()
                    lg(correct_counter__,wrong_counter__,blank_counter__,total_counter__)
                    daily_stat("set",correct_counter__,wrong_counter__,blank_counter__,total_counter__,2,time.time()-time_of_quiz_start_2)

                if LEVEL_1_PASSED == True and LEVEL_2_PASSED == True:
                    print("Tebrikler! Seviye 2'yi de geçtiğiniz tespit edildi! Tüm seviyeleri tamamladınız!")
                    if quiz_config.get("send_telegram_message"):
                        m_ = []
                        with open("daily_stats.csv", "r", encoding="UTF-8") as fg:
                            liness = fg.readlines()
                            for line in liness[::-1]:
                                if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                                    m_.append(line)
                            fg.close()
                        o_ = []
                        if len(m_) == 2:
                            for i in range(1,5):
                                ox = 0
                                for x in m_:
                                    ox += int(x.split(",")[i])
                                o_.append(ox)
                        else:
                            for i in range(1,5):
                                o_.append(int(m_[0].split(",")[i]))
                        lg(o_)
                        print("Sending Report.")
                        if o_[0] == 0: puan = 0; net=0
                        else:
                            net = o_[0]+(-o_[1]-o_[2])*.25
                            if o_[3] != 0:
                                puan = o_[0]/o_[3]*100
                            else: puan = 0
                        tdy = datetime.datetime.now().strftime("%Y-%m-%d")
                        tdy_stats = []
                        with open("statistics.csv","r",encoding="UTF-8") as ff:
                            lineies = ff.readlines()
                            for lime in lineies[::-1]:
                                if tdy in lime:
                                    tdy_stats.append(lime)
                            ff.close()
                        flb = {}
                        for stat in tdy_stats:
                            parts = stat.split(",")
                            key = parts[1]
                            is_success = parts[4] == "True"

                            current_true, current_total = flb.get(key, [0, 0])

                            new_true = current_true + 1 if is_success else current_true
                            new_total = current_total + 1
                            
                            flb[key] = [new_true, new_total]
                        for key,val in flb.items():
                            if val[1] != 0:
                                flb[key] = [val[0],val[1],(val[0]/val[1])*100]
                            else:
                                flb[key] = [val[0],val[1],0]
                        flb = dict(sorted(flb.items(), key=lambda item: item[1][2], reverse=True))
                        lb = ""
                        """ print("hiaa")
                        print(flb)
                        print("hi")
                        time.sleep(999) """
                        for key, a in list(flb.items())[:20]:
                            lb = f"{lb}{key} -> %{a[2]} ({a[0]}/{a[1]})\n"

                        lb2 = ""
                        for key, a in list(flb.items())[-20:]:
                            lb2 = f"{lb2}{key} -> %{a[2]} ({a[0]}/{a[1]})\n"
                        # Calculate total elapsed time (sum of time_elapsed values in daily_stats entries)
                        ttlist = []
                        for entry in m_:
                            try:
                                parts = entry.strip().split(",")
                                seconds = float(parts[6])
                            except Exception:
                                seconds = 0
                            ttlist.append(seconds)
                        total_seconds = int(sum(ttlist))
                        total_time = str(datetime.timedelta(seconds=total_seconds))
                        telegram_text = f"📅 Günlük Analiz 📅 ({datetime.datetime.now().strftime("%d.%m.%Y")})\n\nPuan : %{puan:.2f}\nNet : {net:.2f}\n\n✅ Doğru : {o_[0]}\n❌ Yanlış : {o_[1]}\n⚪ Boş : {o_[2]}\n📝 Total Soru Sayısı : {o_[3]}\nGeçen Toplam Süre : {total_time}\n\n🏆 Top 20 : \n\n{lb}\n📉 Worst 20 : \n\n{lb2}"
                        try:
                            with open("sent_tg_messages.json","r",encoding="UTF-8") as x:
                                ddt = json.load(x)
                                x.close()
                        except (json.JSONDecodeError, FileNotFoundError):
                            ddt = {}
                        # Use today's date as key to avoid comparing long message strings
                        date_key = datetime.datetime.now().strftime("%Y-%m-%d")
                        if ddt.get(date_key) != telegram_text:
                            import telegram_report
                            try:
                                telegram_report.send_telegram_report(telegram_text)
                                with open("sent_tg_messages.json","w",encoding="UTF-8") as h:
                                    ddt[date_key] = telegram_text
                                    json.dump(ddt,h,indent=4)
                            except Exception:
                                time.sleep(60)
                                telegram_report.send_telegram_report(telegram_text)
                                with open("sent_tg_messages.json","w",encoding="UTF-8") as h:
                                    ddt[date_key] = telegram_text
                                    json.dump(ddt,h,indent=4)
                        if DEBUG:
                            int(input(""))
                        
                    time.sleep(3)
                    cls()
                    main(quiz_config=quiz_config)


def dummy_main(quiz_config={}, legacy_start_menu=False,mode="play"):
    global DEBUG
    lg(f"dummy_main({quiz_config},{legacy_start_menu},{mode})")
    options = {"1": "Başla","2": "Admin Girişi"}
    if legacy_start_menu:
        print("Coalide'a hoş geldiniz!\n")
        try:
            if sys.argv[1] == "-debug":
                
                print(Fore.RED + "DEBUG MODU AKTİF" + Style.RESET_ALL + "\n")
        
        except:pass
    
        
        print("Seçenekler:\n")
        for key, value in options.items():
            print(f"{key}. {value}")
        choice = input("\n\n> ")
    else:
        try:
            choice = c_
        except:choice = "play"

    if choice == list(options.keys())[1] or choice == "admin" or mode == "admin":
        admin_login_interface()
    elif choice == list(options.keys())[0] or choice == "play" or mode == "play":
        try:
            if not DEBUG:
                c__ = ASCII.ASCII_selection_menu.main()
                cls()
                legacy_selection_menu = False
            else: raise
        except:
            print("An error occurred in selection_menu. Falling back to legacy start menu.")
            legacy_selection_menu = True
        
        choices = {"1": "Varsayılan modda başlat", "2": "Admin kontrolü"}

        if legacy_selection_menu:
            print("Seçenekler:\n")
            for key, value in choices.items():
                print(f"{key}. {value}")
            choice_ = input("\n\n> ")
        else:
            choice_ = c__
            if choice_ == "exit":
                print("Çıkış yapılıyor...")
                os._exit(1)
        if choice_ == list(choices.keys())[1] or choice_ == "admin":
            auth = admin_login_interface(just_auth=True,legacy_selection_menu=legacy_selection_menu)
            cls()
            if auth:
                print("Admin kontrolüne hoş geldiniz!")
                default_config = get_config(["default_quiz_config"])
                if quiz_config == {}:
                    temp_config = copy.deepcopy(default_config)
                else:
                    temp_config = [quiz_config]
                print("Mevcut quiz yapılandırması:\n")
                for key, value in temp_config[0].items():
                    for key_, value_ in default_config[0].items():
                        if key == key_:
                            if value != value_:txt = f" (Varsayılan : {value_})"
                            else:txt = ""
                            
                            print(f"{key}: {value}{txt}")

                loop=True
                while loop == True:
                    command = input("\n\n> ")
                    if command.startswith("set "):
                        if "--help" in command:
                            print("set komutu, geçici quiz yapılandırmasını güncellemek için kullanılır. Kullanım: set <anahtar> <değer>")
                            print("Anahtarlar:")
                            for key in temp_config[0].keys():
                                print(f"- {key}")
                        else:
                            try:
                                _, key, value = command.split(" ", 2)
                                if key in temp_config[0]:
                                    if value.lower() in ["true", "false"]:
                                        value = value.lower() == "true"
                                    elif value.isdigit():
                                        value = int(value)
                                    temp_config[0][key] = value
                                    print(f"{key} başarıyla {value} olarak güncellendi.")
                                    print(temp_config)
                                else:
                                    print(f"Geçersiz anahtar: {key}")
                            except ValueError:
                                print("Geçersiz komut formatı. Kullanım: set <anahtar> <değer>")
                    elif command.startswith("dset "):
                        if "--help" in command:
                            print("dset komutu, varsayılan quiz yapılandırmasını güncellemek için kullanılır. Kullanım: dset <anahtar> <değer>")
                            print("Anahtarlar:")
                            for key in default_config[0].keys():
                                print(f"- {key}")
                        else:
                            try:
                                print("dset <anahtar> <değer>: Varsayılan quiz yapılandırmasını günceller.")
                                _, key, value = command.split(" ", 2)
                                if key in default_config[0]:
                                    if value.lower() in ["true", "false"]:
                                        value = value.lower() == "true"
                                    elif value.isdigit():
                                        value = int(value)
                                    default_config[0][key] = value
                                    temp_config[0][key] = value
                                    set_config("default_quiz_config", key, value)
                                    print(f"{key} başarıyla {value} olarak güncellendi.")
                                else:
                                    print(f"Geçersiz anahtar: {key}")
                            except ValueError:
                                print("Geçersiz komut formatı. Kullanım: dset <anahtar> <değer>")

                    elif command == "show":
                        if "--help" in command:
                            print("show komutu, mevcut quiz yapılandırmasını gösterir. Kullanım: show")
                        else:
                            print("Mevcut quiz yapılandırması:\n")
                            for key, value in temp_config[0].items():
                                for key_, value_ in default_config[0].items():
                                    if key == key_:
                                        if value != value_:txt = f" (Varsayılan : {value_})"
                                        else:txt = ""
                                        print(value,value_,txt,key,key_)
                                        print(f"{key}: {value}{txt}")
                    elif command == "exit":
                        if "--help" in command:
                            print("exit komutu, admin kontrolünden çıkar ve ana menüye döner. Kullanım: exit")
                        else:
                            loop = False
                            if temp_config:
                                main(quiz_config=temp_config[0])
                            else:
                                main(quiz_config=default_config[0])
                            return
                    elif command == "cls" or command == "clear":
                        if "--help" in command:
                            print("cls/clear komutu, ekranı temizler. Kullanım: cls/clear")
                        else:
                            cls()
                    elif command == "help":
                        print("Komutlar:")
                        print("- set <anahtar> <değer>: Geçici quiz yapılandırmasını günceller.")
                        print("- dset <anahtar> <değer>: Varsayılan quiz yapılandırmasını günceller.")
                        print("- show: Mevcut quiz yapılandırmasını gösterir.")
                        print("- cls/clear: Ekranı temizler.")
                        print("- help: Komut listesini gösterir.")
                        print("- exit: Admin kontrolünden çıkar ve ana menüye döner.")
                    else:
                        print("Geçersiz komut! Komutlar: set <anahtar> <değer>, dset <anahtar> <değer>, show, cls/clear, help, exit")   

                
        if choice_ == list(choices.keys())[0] or choice_ == "dstart":
            if quiz_config == {}:
                quiz_config = get_config(["dummy_mode"])[0]
            
            question_amount = 0

            ### LEVEL 1 ###
            """ known_words = ["give","go","have","make","say","see","take","want"] """
            known_words = []
            word_progression = {}
            if os.path.exists("statistics.csv"):
                with open("statistics.csv", "r") as f:
                    lines = f.readlines()
                    words = []
                    for line in lines[::-1]:
                        data = line.strip().split(",")
                        if len(data) >= 5:
                            if data[1] not in words:
                                words.append(data[1])
                    for word in words:
                        amount_counter = correct_counter = 0
                        for line in lines[::-1]:
                            data = line.strip().split(",")
                            if len(data) >= 5 and data[1] == word:
                                if amount_counter > 5:
                                    break
                                amount_counter += 1
                                if data[4] == "True":
                                    correct_counter += 1
                            if amount_counter == correct_counter == 5:
                                if word not in known_words:
                                    known_words.append(word)
                        
                        word_progression[word] = [correct_counter,amount_counter,correct_counter / amount_counter if amount_counter > 0 else 0]
                f.close()

            all_words,typer = load_words("words.csv")
            start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            dd = {}
            for word_dict in all_words:
                dd[list(word_dict)[0]] = word_dict.get(list(word_dict)[0])
            if len(all_words) < quiz_config.get("dummy_question_count"):
                question_amount = len(all_words)
            else:
                question_amount = quiz_config.get("dummy_question_count")
            lg(known_words)
            time_of_quiz_start = time.time()
            quest(question_amount=question_amount,wordlist=list(dd.keys()),word_progression=word_progression,dd=dd,typer=typer,quiz_config=quiz_config,current_level=0)
            if not os.path.exists("statistics.csv"):
                with open("statistics.csv","w",encoding="UTF-8") as f:f.close()
            with open("statistics.csv", "r", encoding="UTF-8") as f:
                correct_counter_ = wrong_counter_ = blank_counter_ = total_counter_ = 0
                lines = f.readlines()
                todays=[]
                for line in lines[::-1]:
                    if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                        if line.strip() not in todays:
                            todays.append(line.strip())
                time.sleep(.3)
                for line in todays:
                    if line.split(",")[5] == "0":
                        """ print(line)
                        print(line.split(","))
                        print(line.split(",")[4])
                        time.sleep(999) """
                        if line.split(",")[4] == "True":
                            correct_counter_ += 1
                        elif line.split(",")[4] == "False":
                            wrong_counter_ += 1
                        else: blank_counter_ += 1
                        total_counter_ += 1
                f.close()
            daily_stat("set",correct_counter_,wrong_counter_,blank_counter_,total_counter_,level=0,time_elapsed=time.time()-time_of_quiz_start)
        
            for line in daily_stat("get",0,0,0,0,0,0)[::-1]:
                """ print(line)
                print(quiz_config.get("dummy_question_count"))
                print(int(line.split(",")[4])) """
                if line.split(",")[5].strip() == "0" and int(line.split(",")[4]) >= quiz_config.get("dummy_question_count"):
                    LEVEL_0_PASSED = True
                    break
            else:LEVEL_0_PASSED = False
                
            if LEVEL_0_PASSED:
                print("Tebrikler! Dummy modunu tamamladığınız tespit edildi!")

                m_ = []
                with open("daily_stats.csv", "r", encoding="UTF-8") as fg:
                    liness = fg.readlines()
                    for line in liness[::-1]:
                        if datetime.datetime.now().strftime("%Y-%m-%d") in line:
                            m_.append(line)
                    fg.close()
                o_ = []
                for i in range(1,5):
                    o_.append(int(m_[0].split(",")[i]))
                lg(o_)
                print("Sending Report.")
                if o_[0] == 0: puan = 0; net=0
                else:
                    net = o_[0]+(-o_[1]-o_[2])*.25
                    if o_[3] != 0:
                        puan = o_[0]/o_[3]*100
                    else: puan = 0
                tdy = datetime.datetime.now().strftime("%Y-%m-%d")
                tdy_stats = []
                with open("statistics.csv","r",encoding="UTF-8") as ff:
                    lineies = ff.readlines()
                    for lime in lineies[::-1]:
                        if tdy in lime:
                            tdy_stats.append(lime)
                    ff.close()
                flb = {}
                for stat in tdy_stats:
                    parts = stat.split(",")
                    key = parts[1]
                    is_success = parts[4] == "True"

                    current_true, current_total = flb.get(key, [0, 0])

                    new_true = current_true + 1 if is_success else current_true
                    new_total = current_total + 1
                    
                    flb[key] = [new_true, new_total]
                for key,val in flb.items():
                    if val[1] != 0:
                        flb[key] = [val[0],val[1],(val[0]/val[1])*100]
                    else:
                        flb[key] = [val[0],val[1],0]
                flb = dict(sorted(flb.items(), key=lambda item: item[1][2], reverse=True))
                lb = ""
                """ print("hiaa")
                print(flb)
                print("hi")
                time.sleep(999) """
                for key, a in list(flb.items())[:20]:
                    lb = f"{lb}{key} -> %{a[2]} ({a[0]}/{a[1]})\n"

                lb2 = ""
                for key, a in list(flb.items())[-20:]:
                    lb2 = f"{lb2}{key} -> %{a[2]} ({a[0]}/{a[1]})\n"
                # Compute total elapsed time from today's daily_stats entries
                ttlist = []
                for entry in m_:
                    try:
                        parts = entry.strip().split(",")
                        seconds = float(parts[6])
                    except Exception:
                        seconds = 0
                    ttlist.append(seconds)
                total_seconds = int(sum(ttlist))
                total_time = str(datetime.timedelta(seconds=total_seconds))
                telegram_text = f"📅 Günlük Analiz 📅 ({datetime.datetime.now().strftime("%Y/%m/%d")})\n\nPuan : %{puan:.2f}\nNet : {net:.2f}\n\n✅ Doğru : {o_[0]}\n❌ Yanlış : {o_[1]}\n⚪ Boş : {o_[2]}\n📝 Total Soru Sayısı : {o_[3]}\nGeçen Toplam Süre : {total_time}\n\n🏆 Top 20 : \n\n{lb}\n📉 Worst 20 : \n\n{lb2}"
                if quiz_config.get("send_telegram_message"):
                    try:
                        with open("sent_tg_messages.json","r",encoding="UTF-8") as x:
                            ddt = json.load(x)
                            x.close()
                    except (json.JSONDecodeError, FileNotFoundError):
                        ddt = {}
                    try:
                        date_key = datetime.datetime.now().strftime("%Y-%m-%d")
                        if ddt.get(date_key) != telegram_text:
                            import telegram_report
                            try:
                                telegram_report.send_telegram_report(telegram_text)
                                with open("sent_tg_messages.json","w",encoding="UTF-8") as h:
                                    ddt[date_key] = telegram_text
                                    json.dump(ddt,h,indent=4)
                            except Exception:
                                time.sleep(60)
                                telegram_report.send_telegram_report(telegram_text)
                                with open("sent_tg_messages.json","w",encoding="UTF-8") as h:
                                    ddt[date_key] = telegram_text
                                    json.dump(ddt,h,indent=4)
                        if DEBUG:
                            int(input(""))
                    except:print("Rapor gönderilirken bir hata oluştu!")
                if get_config(["general"])[0].get("set_time_for_pc"):
                    lg("set_time_for_pc is true")
                    ### Point, Minute Calculation and API post to parental control ###

                    ### Minute calculation
                    minutes_to_add = o_[0]*60

                    ### Give the user info ###
                    if get_config(["general"])[0].get("set_time_for_tomorrow"):
                        t = "yarın"
                        date_val = datetime.date.today() + datetime.timedelta(days=1)
                    else:t="bugün";date_val = datetime.date.today()
                    date = date_val.strftime("%Y-%m-%d")
                    try:
                        with open("used_exceptions.csv","r",encoding="UTF-8") as f:
                            lines = f.readlines()
                            for line in lines[::-1]:
                                print(line)
                                if line.strip() == f"{date},{o_[0]},{minutes_to_add}":
                                    already_registered = True
                                    break
                            else:raise
                    except:already_registered=False
                    if not already_registered:   
                        cls()
                        print("Lütfen bekleyiniz...")

                        ### Send api post to parental control api to add exceptional time ###
                        import parental_connection as pc
                        base_url = os.getenv("PARENTAL_CONTROL_URL","http://IP-TO-YOUR-PCV2-SERVER:5005")
                        ### example structure of resulting var : {"data":[[600,null],[600,null]],"status":"success"}
                        if base_url != None:
                            resulting = pc.get_exceptional_time(base_url, "OVERALL", date)
                            total_time_available = 0
                            for exception in resulting.get("data", []):
                                if "COALIDE" in str(exception[1]):
                                    total_time_available += int(exception[0])
                            if minutes_to_add > total_time_available:
                                minutes_to_add = minutes_to_add - total_time_available
                            else:minutes_to_add = 0
                        print(f"{o_[0]-minutes_to_add//60} Doğru yaptınız {t} için {minutes_to_add//60} dakika ekleniyor..")
                        try:
                            if base_url != None:
                                ifn = pc.add_exceptional_time(base_url, "OVERALL", minutes_to_add,date,f"{o_[0]} Doğru yaptığınız için - COALIDE")
                            else: ifn = None
                            if "Connection Error" in str(ifn):raise Exception("Connection Error")
                            if 1 == ifn or '"status":"queued"' in str(ifn):
                                print("Dakikalarınız eklendi.")
                                if not os.path.exists("used_exceptions.csv"):
                                    with open("used_exceptions.csv","w",encoding="UTF-8") as f:f.close()
                                with open("used_exceptions.csv","a",encoding="UTF-8") as file:
                                    file.write(f"{date},{o_[0]},{minutes_to_add}\n")
                                    file.close()
                            elif "Error" in str(ifn): print("Dakika eklenirken sorun oluştu!");print(str(ifn))
                            else: print("Muhtemelen Dakikanız eklendi")
                        except:
                            print("İkincil API'ye istek gönderilirken bir hata oluştu! Dakika eklenemedi!!!")
                        print(f"\n{telegram_text}\n")
                        s_time = time.time()
                        while time.time() - s_time < 30:
                            input(f"Ana menüye dönmek için herhangi bir butona basınız. ({int(time.time() - s_time)}/30 sn)")

                    else:
                        print("Zaten süreniz eklenmiş!")
                time.sleep(3)
                cls()
                ### Restarting the code to fix problems with memory ###
                restart_application()
                
                """ dummy_main(quiz_config=quiz_config) """


if sys.argv[1:]:
    if "-pack-data" in sys.argv[1:]:
        if "--help" in sys.argv[2:]:
            print("Usage: -pack-data\nThis command packages important data files into a 'packaged_data' folder for backup. It collects files such as 'statistics.csv', 'daily_stats.csv', 'analytics.csv', 'words.csv', 'config.json', and 'sent_tg_messages.json' and copies them into a new folder named 'packaged_data'. If the folder already exists, it will be cleared before copying the files. This is useful for creating a backup of your data or transferring it to another location.")
            sys.exit(0)
        static_files = [
            "statistics.csv",
            "daily_stats.csv",
            "analytics.csv",
            "words.csv",
            "config.json",
            "sent_tg_messages.json",
            ".env",
        ]
        if not os.path.exists("packaged_data"):
            os.makedirs("packaged_data")
        else:
            shutil.rmtree("packaged_data")
            os.makedirs("packaged_data")
        for file in static_files:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join("packaged_data", file))
        print("Data files have been packaged into the 'packaged_data' folder. Exiting...")
        sys.exit(0)
    elif "-create-tts-cache" in sys.argv[1:]:
        if "--help" in sys.argv[2:]:
            print("Usage: -create-tts-cache [options]\nThis command generates a TTS cache for words and sentences. It checks for existing audio files in the 'pronunciations' folder and generates missing ones based on the entries in 'words.csv'.\n\nOptions:\n-gtts : Use Google Text-to-Speech for audio generation (default is ElevenLabs)\n-all : Generate TTS for both words and sentences (default)\n-words : Generate TTS only for words\n-sentences : Generate TTS only for sentences\n-force : Force regeneration of all TTS files by clearing the existing cache")
            sys.exit(0)
        mode = "11"
        job = force = None
        if sys.argv[2:]:
            if "-gtts" in str(sys.argv[2:]).lower(): mode = "gtts"
            else: mode = "11"
            if "-all" in str(sys.argv[2:]).lower(): job = "all"
            elif "-words" in str(sys.argv[2:]).lower(): job = "words"
            elif "-sentences" in str(sys.argv[2:]).lower(): job = "sentences"
            else: job = "all"
            if "-force" in str(sys.argv[2:]).lower(): force = True
            else: force = False
        
        if force:
            shutil.rmtree("pronunciations")
            os.makedirs("pronunciations") 
        words,typer = load_words('words.csv')
        """ print(typer[0]) """
        all_words = set()
        all_sentences = set()
        i = 0
        for word_dict in words:
            i = i + 1
            key = next(iter(word_dict.keys()))
            try: sh = typer[i-1].get(key)[2][1]
            except: sh = ""
            sentence = f"{typer[i-1].get(key)[2][0]} {key} {sh}"
            if not os.path.exists(f"pronunciations/{safe_filename(key)}.mp3"):
                all_words.add(key)
            if not os.path.exists(f"pronunciations/{safe_filename(sentence)}.mp3"):
                all_sentences.add(sentence)
        
        print(f"Generating TTS cache for",end="")
        if job == "words": print(f"{len(all_words)} words")
        elif job == "sentences": print(f"{len(all_sentences)} sentences")
        else: print(f"{len(all_words)} words and {len(all_sentences)} sentences")
        print(f"Using mode : {mode}")
        print("This process may take a while depending on the number of words/sentences to generate and the TTS mode selected. Please wait...")
        print("Generating words..." if job != "sentences" else "Generating sentences...")
        if job != "sentences":
            i = 1
            for word in all_words:
                print(f"[{i}/{len(all_words)} (%{i/len(all_words)*100:.2f})] Generating TTS for word: {word}")
                get_audio(word,lang_="en",server=mode)
                i = i + 1
        if job != "words":
            print("\n\n All words generated! Now generating sentences...\n")
            i = 1
            for sentence in all_sentences:
                print(f"[{i}/{len(all_sentences)} (%{i/len(all_sentences)*100:.2f})] Generating TTS for sentence: {sentence}")
                get_audio(sentence,lang_="en",server=mode,sentence=True)
                i = i + 1
            print("TTS cache generation complete. Exiting...")
        sys.exit(0)
    elif "-create-daily-stats" in sys.argv[1:]:
        if sys.argv[2:]:
            if "--help" in sys.argv[2:]:
                print("Usage: -create-daily-stats\nThis command creates or updates daily stats based on today's quiz performance. It reads today's quiz results from 'statistics.csv', calculates the number of correct, wrong, blank, and total answers, and then saves this data to 'daily_stats.csv'.")
                sys.exit(0)
        from Manuals import Create_daily_stats_manually as cdsm
        cdsm.main()
        print("Daily stats have been created/updated. Exiting...")
        sys.exit(0)
    elif "-help" in sys.argv[1]:
        print("Available command-line arguments:")
        print("- -pack-data: Packages important data files into a 'packaged_data' folder for backup.")
        print("- -create-tts-cache: Generates TTS cache for words and sentences. Use with additional flags to specify details.")
        print("- -create-daily-stats: Creates or updates daily stats based on today's quiz performance.")
        print("- -debug: Enables debug mode for more verbose output and legacy start menu.")
        print("\nFor detailed instructions on using each argument, please refer to the documentation or use the '-help' flag with the specific argument.")
        sys.exit(0)

if __name__ == "__main__":  
    lg("Starting...")
    lg(f"sys.argv: {sys.argv}\nPython version: {sys.version}\nPlatform: {sys.platform}")
    backup_data()
    try:
        if "-debug" in sys.argv:
            c_ = ASCII.ASCII_start_menu.main(debug=True)
        else:c_ = ASCII.ASCII_start_menu.main()
        cls()
        leg = False
       
    except Exception as e:
        print(f"An error occurred in start_menu: {e}.\n\n Falling back to legacy start menu.")
        leg = True
        c_ = "play"
    cls()
    try:
        lg("Checking for words.csv updates...")
        check_and_update_words_csv("MelihAydinYanibol/Coalide")
        if not get_config(["dummy_mode"])[0].get("dummy_mode"):
            main(legacy_start_menu=leg,mode=c_)
        else:
            dummy_main(legacy_start_menu=leg,mode=c_)
    except KeyboardInterrupt:
        print("Exiting the application")
    except Exception as e:
        print(f"Application error occurred: {e}")
        print("Restarting application in 5 seconds...")
        time.sleep(5)
        restart_application()
































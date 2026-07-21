"""
This files only job is to log.
"""

import sys
import os
import re
import copy
import json
from colorama import Fore, Style

def lg(a="",b="",c="",d="",e="",f="",g="",h="",i="",j="",k="",l="",m="",n="",o="",p="",q="",r="",s="",t="",u="",v="",w="",x="",y="",z=""):
    global DEBUG
    DEBUG = any(arg in ("-debug", "--debug") for arg in sys.argv[1:])
    if DEBUG:
        print(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z)

    return DEBUG

def cls():
    lg("cls()")
    if lg() != True:
        os.system('cls')

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
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    default_config = {
        "Daily_New_Word_Cap":15,
        "No_Repeat_Window":8,
        "Repo_Owner":"MelihAydinYanibol",
        "Repo_Name":"Coalide",
        "Update_Prereleases":False,
        "Source_Language":"Türkçe",
        "Target_Language":"İngilizce",
        "BASE_RATE_PER_MINUTE":5,
        "ESCALATION_PER_HOUR":0.5,
        "SPAM_PROTECTION":True,
        "INPUT_TIMEOUT":0,
        "Credit_Reset_Weekly":True,
        "BACKUP_PRONUNCIATIONS":True,
        "KIOSK_MODE":False,
        "BYPASS_SHORTCUTS":True,
        "Credit_Window_Start":"07:00",
        "Credit_Window_End":"22:00",
        "REQUIRE_INTERNET":False

    }
    if not os.path.exists(config_path):
        with open(config_path, "w", encoding="UTF-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        config = default_config if default else None
    if default:
        return default_config
    else:
        with open(config_path, "r", encoding="UTF-8") as f:
            try: config = json.load(f)
            except: config = default_config # Fallback if file is corrupted
    if not isinstance(config, dict):
        config = copy.deepcopy(default_config)

    # Repair missing keys/sections and persist the updated config
    config_updated = _merge_missing_config_keys(config, default_config)
    if config_updated:
        with open(config_path, "w", encoding="UTF-8") as file:
            json.dump(config, file, indent=4, ensure_ascii=False)
    return config

CURRENT_USER_FILE = os.path.join(os.path.dirname(__file__), "current_user.json")

# Only word characters (letters/digits/underscore, Unicode-aware so Turkish
# letters survive) and hyphens are kept. This is intentionally strict: the
# username ends up in a filename (see balance_obj.py), and terminals can
# leak raw ANSI escape sequences into stdin (e.g. a mouse click while
# input() is blocking, if mouse-tracking mode is on) which otherwise
# produces control characters that Windows refuses to use in a path.
_USERNAME_UNSAFE_RE = re.compile(r"[^\w\-]", re.UNICODE)

def _sanitize_username(raw: str) -> str:
    return _USERNAME_UNSAFE_RE.sub("", raw).strip()

def get_current_user() -> str:
    """
    Returns the username of the currently logged-in user, read from
    current_user.json. If no one is logged in yet (fresh install, or the
    file was removed), asks for a username once and remembers it for
    every future run.
    """
    if os.path.exists(CURRENT_USER_FILE):
        with open(CURRENT_USER_FILE, "r", encoding="UTF-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        raw_username = data.get("username") if isinstance(data, dict) else None
        if raw_username:
            username = _sanitize_username(raw_username)
            if username:
                return username
            # Saved username was corrupted (e.g. control/escape characters) --
            # fall through and ask again instead of crashing on every run.

    username = ""
    while not username:
        username = _sanitize_username(input("Giriş yapmak için kullanıcı adınızı giriniz: "))
    set_current_user(username)
    return username

def set_current_user(username: str):
    with open(CURRENT_USER_FILE, "w", encoding="UTF-8") as f:
        json.dump({"username": username}, f, indent=4, ensure_ascii=False)

def repair_config():
    lg("repair_config()")
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    default_config = get_config(default=True)  # This will create the file if it doesn't exist
    current_config = get_config()  # Load current config (or default if file was missing/corrupted)
    if default_config != current_config:
        print(f"{Fore.YELLOW}Config file is different from the default. Checking for repair...{Style.RESET_ALL}")

    # get_config() already adds missing keys; this function is a manual trigger.
    changed = _merge_missing_config_keys(current_config, default_config)
    if changed:
        with open(config_path, "w", encoding="UTF-8") as file:
            json.dump(current_config, file, indent=4, ensure_ascii=False)
        print(f"{Fore.GREEN}Missing config keys were added successfully.{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Config is already complete. No missing keys found.{Style.RESET_ALL}")

def kiosk_batch_creator():
    """
    Writes launch_kiosk.bat next to this file. The batch cd's into the Coalide
    folder (so the app finds config.json, words.json, etc.) and relaunches
    Coalide in a loop, so if it ever exits it comes straight back.

    Uses sys.executable -- the interpreter actually running this program -- so it
    works whether Coalide runs under a venv or the machine's global Python.
    """
    import os
    import sys

    project_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(project_dir, "coalide.py")
    batch_path = os.path.join(project_dir, "launch_kiosk.bat")

    # The interpreter running us right now -- venv or global, always a real path.
    python_exe = sys.executable
    # If we're under pythonw (no console), prefer python.exe so the TUI is visible.
    if os.path.basename(python_exe).lower() == "pythonw.exe":
        candidate = os.path.join(os.path.dirname(python_exe), "python.exe")
        if os.path.exists(candidate):
            python_exe = candidate

    batch_content = (
        "@echo off\n"
        "title Coalide\n"
        'cd /d "%~dp0"\n'
        ":loop\n"
        f'"{python_exe}" "{main_script}"\n'
        "timeout /t 1 /nobreak >nul\n"
        "goto loop\n"
    )

    with open(batch_path, "w", encoding="utf-8") as f:
        f.write(batch_content)

    print(f"{Fore.GREEN}Kiosk launch batch file created at: {batch_path}{Style.RESET_ALL}")
    return batch_path
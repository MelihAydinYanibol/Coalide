"""
This module contains CLI commands for the Coalide application. It provides a command-line interface for users to interact with the application, allowing them to perform various tasks.
"""

import sys
import os
import stat
import shutil
import fnmatch

# Files this command backs up. Supports glob patterns, same approach as
# coalide.py's PROTECTED_PATTERNS, since per-user files like
# "username_data.json" vary by name.
STATIC_FILE_PATTERNS = [
    "statistics.csv",
    "daily_stats.csv",
    "analytics.csv",
    "words.csv",
    "config.json",
    "sent_tg_messages.json",
    "*_data.json",  # per-user balance/credits files
    "current_user.json",  # which user is currently logged in
]


def _is_static_file(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in STATIC_FILE_PATTERNS)


def pack_data(target_dir=".", output_dir="packaged_data"):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    for item in os.listdir(target_dir):
        if not _is_static_file(item):
            continue
        s = os.path.join(target_dir, item)
        d = os.path.join(output_dir, item)
        if os.path.isfile(s):
            shutil.copy2(s, d)


# Everything -release-ready wipes, searched recursively from the folder the
# command is run in. Supports glob patterns, same approach as the other
# pattern lists in this project. These are user data / local-only artifacts
# that must never ship in a release.
RELEASE_CLEAN_PATTERNS = [
    ".git",
    ".env",
    "env",
    "venv",
    ".venv",
    "__pycache__",
    ".claude",
    "pronunciations",
    "packaged_data",
    "progress.json",
    "words.json",
    "*_data.json",      # per-user balance/credits files
    "current_user.json",
    "version.json",
    "config.json",      # regenerated with defaults on first run
    "sent_tg_messages.json",
    "statistics.csv",
    "daily_stats.csv",
    "analytics.csv",
]


def _matches_release_clean(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in RELEASE_CLEAN_PATTERNS)


def _force_remove(func, path, exc_info):
    # .git stores its objects as read-only files, which makes rmtree fail on
    # Windows -- clear the read-only flag and retry.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def find_release_clean_targets(target_dir="."):
    targets = []
    for root, dirs, files in os.walk(target_dir):
        for name in dirs + files:
            if _matches_release_clean(name):
                targets.append(os.path.join(root, name))
        # no point descending into folders that are getting deleted whole
        dirs[:] = [d for d in dirs if not _matches_release_clean(d)]
    return targets


def release_ready(target_dir="."):
    target_dir = os.path.abspath(target_dir)
    targets = find_release_clean_targets(target_dir)
    if not targets:
        print("Nothing to clean -- this folder already looks release-ready.")
        return

    print(f"This will PERMANENTLY delete the following from:\n  {target_dir}\n")
    for t in targets:
        kind = "folder" if os.path.isdir(t) else "file"
        print(f"  - {os.path.relpath(t, target_dir)}  ({kind})")
    print("\nThis erases ALL user data, progress, git history and virtual environments.")
    print("It CANNOT be undone.")

    first = input("\n[1/2] Are you sure you want to continue? (yes/no): ").strip().lower()
    if first != "yes":
        print("Aborted. Nothing was deleted.")
        return
    second = input("[2/2] Final check -- type 'ERASE' (all caps) to confirm: ").strip()
    if second != "ERASE":
        print("Aborted. Nothing was deleted.")
        return

    for t in targets:
        rel = os.path.relpath(t, target_dir)
        try:
            if os.path.isdir(t):
                try:
                    shutil.rmtree(t, onexc=_force_remove)
                except TypeError:  # Python < 3.12 has onerror instead of onexc
                    shutil.rmtree(t, onerror=_force_remove)
            else:
                os.chmod(t, stat.S_IWRITE)
                os.remove(t)
            print(f"Deleted: {rel}")
        except Exception as e:
            print(f"FAILED to delete {rel}: {e}")
    print("\nDone. The folder is ready for release.")


if sys.argv[1:]:
    if "-pack-data" in sys.argv[1:]:
        if "--help" in sys.argv[2:]:
            print("Usage: -pack-data\nThis command packages important data files into a 'packaged_data' folder for backup. It collects files such as 'statistics.csv', 'daily_stats.csv', 'analytics.csv', 'words.csv', 'config.json', and 'sent_tg_messages.json' and copies them into a new folder named 'packaged_data'. If the folder already exists, it will be cleared before copying the files. This is useful for creating a backup of your data or transferring it to another location.")
            sys.exit(0)

        pack_data()
        print("Data files packaged successfully into 'packaged_data'.")
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
        
        from word_engine import get_words
        from audio_engine import generate_audio
        words = get_words()
        total_tasks = len(words); n = 1
        for word in words:
            if job in ["all", "words"]:
                print(f"({n}/{total_tasks}) Generating TTS for word: {word.target}"); n += 1
                generate_audio(word, sentence=False, server=mode)
            if job in ["all", "sentences"]:
                print(f"({n}/{total_tasks}) Generating TTS for sentence: {' '.join(word.sentence)}"); n += 1
                generate_audio(word, sentence=True, server=mode)
    
    elif "-release-ready" in sys.argv[1:]:
        if "--help" in sys.argv[2:]:
            print("Usage: -release-ready\nPrepares the folder for release by PERMANENTLY deleting all user data and local-only artifacts found in the current folder and its subfolders: .git, .env, env/venv virtual environments, __pycache__, pronunciations, progress.json, words.json, per-user *_data.json files, current_user.json, config.json, version.json and old statistics files.\n\nIt first lists everything it found and then asks for confirmation TWICE (a 'yes' and then typing 'ERASE'), because this action erases all data and cannot be undone. Consider running -pack-data first if you want a backup.")
            sys.exit(0)

        release_ready()
        sys.exit(0)
    elif "-create-kiosk-batch" in sys.argv[1:]:
        if "--help" in sys.argv[2:]:
            print("Usage: -create-kiosk-batch\nCreates a batch file named 'launch_kiosk.bat' next to this script. The batch file launches Coalide in kiosk mode and suppresses Alt+F4, making it suitable for dedicated kiosk setups where you want to prevent users from closing the application with Alt+F4.")
            sys.exit(0)

        from utils import kiosk_batch_creator
        kiosk_batch_creator()
        print("Batch file 'launch_kiosk.bat' created successfully.")
        sys.exit(0)
    elif "-help" in sys.argv[1]:
        print("Available command-line arguments:")
        print("- -pack-data: Packages important data files into a 'packaged_data' folder for backup.")
        print("- -create-tts-cache: Generates TTS cache for words and sentences. Use with additional flags to specify details.")
        print("- -release-ready: Deletes ALL user data, .git, env/venv and caches to prepare the folder for release. Asks for confirmation twice.")
        print("- -debug: Enables debug mode for more verbose output and legacy start menu.")
        print("\nFor detailed instructions on using each argument, please refer to the documentation or use the '-help' flag with the specific argument.")
        sys.exit(0)
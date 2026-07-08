"""
This module contains CLI commands for the Coalide application. It provides a command-line interface for users to interact with the application, allowing them to perform various tasks.
"""

import sys
import os
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
    
    elif "-help" in sys.argv[1]:
        print("Available command-line arguments:")
        print("- -pack-data: Packages important data files into a 'packaged_data' folder for backup.")
        print("- -create-tts-cache: Generates TTS cache for words and sentences. Use with additional flags to specify details.")
        print("- -debug: Enables debug mode for more verbose output and legacy start menu.")
        print("\nFor detailed instructions on using each argument, please refer to the documentation or use the '-help' flag with the specific argument.")
        sys.exit(0)
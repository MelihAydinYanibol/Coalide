"""
This file manages the audio engine for the application. It handles audio playback, text-to-speech conversion, and any other audio-related functionalities required by the program.
"""

import os
import re
import time
import importlib

try:
    pyaudio = importlib.import_module("pyaudio")
    _PYAUDIO_AVAILABLE = True
except ImportError:
    pyaudio = None
    _PYAUDIO_AVAILABLE = False

from objects.word_obj import Word
try: from gogo.utils import lg
except: from utils import lg
# elevenlabs being missing is not fatal: every function that needs it imports
# it locally and returns None on failure, which triggers the gTTS fallback.
try:import elevenlabs
except ImportError:
    lg("Warning: elevenlabs module not installed. Falling back to gTTS for audio generation.")
from typing import Literal
import dotenv

def get_config(): ## Temporary function.
    """
    Load the configuration from the .env file and return it as a dictionary.
    """
    dotenv.load_dotenv()
    config = {
        "general": {
            "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", "[]"),
        }
    }
    return config

def safe_filename(name: str) -> str:
    # Windows-forbidden chars: <>:"/\|?*
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip(" .")

def elevenlabs_check_for_quota(api_key, word:Word):
    """
    Check if the provided ElevenLabs API key has enough quota to generate audio for the given word
    """
    try:from elevenlabs import ElevenLabs
    except ImportError:
        lg("Warning: elevenlabs module not installed. Audio features may not work.")
        return False
    client = ElevenLabs(api_key=api_key)
    try:
        user = client.user.get()
        quota = user.subscription.character_limit - user.subscription.character_count
        return False if quota < len(word.target)*2 else True
    except Exception as e:
        lg(f"Error checking ElevenLabs quota: {e}")
        return False

def elevenlabs_tts(word:Word,sentence:bool=False):
    """
    Generate audio for a given word using ElevenLabs TTS.
    """
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings
    except ImportError:
        lg("Warning: elevenlabs module not installed. Audio features may not work.")
        return None
    
    api_keys_str = str(os.getenv("ELEVENLABS_API_KEY", "[]")).strip()
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
        lg("No ElevenLabs API key found in .env file.")
        return None
    
    lg(f"Found {len(api_keys)} ElevenLabs API key(s) in environment.")

    if len(api_keys) == 1: api_key = api_keys[0]
    else:
        for _api_key in api_keys:
            if elevenlabs_check_for_quota(_api_key,word):
                api_key = _api_key
                break
        else:
            lg("All provided ElevenLabs API keys have insufficient quota. Falling back to gTTS.")
            return None

    if not os.path.exists("pronunciations"):
        os.makedirs("pronunciations")
    id = word.id if not sentence else f"{word.id}_sentence"
    filename = os.path.join("pronunciations", f"11-{safe_filename(id)}.mp3")

    try:
        voice_id = get_config()["general"].get("elevenlabs_voice_id", "JBFqnCBsd6RMkjVDRZzb")
        client = ElevenLabs(api_key=api_key)
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=word.target if not sentence else word.sentence[0] + f" {word.target} " + word.sentence[1],
            model_id="eleven_multilingual_v2",
            language_code=word.language,
            voice_settings=VoiceSettings(
                stability=0.85,
                similarity_boost=0.75,
                speed=0.82
            )
        )
        with open(filename, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)
    except Exception as e:
        lg(f"ElevenLabs TTS failed for '{word.target}': {e}")
        # Don't leave a partial/empty mp3 behind -- pronounce() would treat it as a valid cache hit.
        if os.path.exists(filename):
            try: os.remove(filename)
            except OSError: pass
        return None
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return filename
    else:
        lg(f"Failed to generate audio for word '{word.target}' with ElevenLabs TTS.")
        return None
    
def gtts_tts(word:Word,sentence:bool=False):
    """
    Generate audio for a given word using gTTS (Google Text-to-Speech).
    """
    try:from gtts import gTTS
    except ImportError:
        lg("Warning: gTTS module not installed. Audio features may not work.")
        return None

    text = word.target if not sentence else word.sentence[0] + f" {word.target} " + word.sentence[1]
    tts = gTTS(text=text, lang=word.language)
    
    if not os.path.exists("pronunciations"): os.makedirs("pronunciations")
    id = word.id if not sentence else f"{word.id}_sentence"
    filename = os.path.join("pronunciations", f"gtts-{safe_filename(id)}.mp3")
    tts.save(filename)
    
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return filename
    else:
        lg(f"Failed to generate audio for word '{word.target}' with gTTS.")
        return None

def generate_audio(
        word: Word,
        sentence: bool = False,
        server:Literal["elevenlabs","gtts","11",11] = "elevenlabs",
        tries: int = 0
        ) -> str:
    """
    Generate audio for a given word using the specified TTS server.
    """
    if server in ["elevenlabs", "11", 11]:
        audio_file = elevenlabs_tts(word, sentence)
        if audio_file:
            return audio_file
        else:
            lg("Falling back to gTTS due to ElevenLabs failure or quota issues.")
            return gtts_tts(word, sentence)
    elif server == "gtts":
        audio_file = gtts_tts(word, sentence)
        if audio_file:
            return audio_file
        if tries < 3:
            lg("gTTS failed to generate audio. Trying again")
            return generate_audio(word, sentence, server, tries=tries+1)
        else:
            lg("gTTS failed to generate audio after 3 tries. No audio will be generated.")
            return None
            
def play_audio(filename):
    lg(f"play_audio({filename})")
    # Backwards-compatible wrapper that uses the resilient player below
    return play_audio_with_unplug_handling(filename)

def is_output_device_available():
    """Return True if a default output device appears available to PyAudio."""
    if not _PYAUDIO_AVAILABLE:
        # pyaudio is an optional dependency used only for this check; without
        # it, skip detection entirely rather than reporting false negatives.
        return True
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
    """
    Return a list of files in the specified folder. If the folder does not exist, return an empty list.
    """
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
    
def pronounce(word:Word, sentence=False):
    lg(f"pronounce_word({word}, {sentence})")
    files = get_folder("pronunciations")
    for file in files: # Going through the files in the pronunciations folder
        file = safe_filename(file)

        name = f"{safe_filename(word.id)}_sentence.mp3" if sentence else f"{safe_filename(word.id)}.mp3"
        if file.lower() == f"11-{name}".lower():
            lg(f"Playing existing ElevenLabs pronunciation for '{word.target}'.")
            play_audio(os.path.join("pronunciations", file))
            return
        elif file.lower() == f"gtts-{name}".lower():
            lg(f"Playing existing gTTS pronunciation for '{word.target}'.")
            play_audio(os.path.join("pronunciations", file))
            return
    else:
        audio_file = generate_audio(word, sentence=sentence)
        if audio_file:
            play_audio(audio_file)

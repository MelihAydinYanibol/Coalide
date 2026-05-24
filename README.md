# Coalide - Interactive Quiz Learning Application

<div align="center">

**A Python-based interactive English–Turkish vocabulary quiz with ASCII art menus, text-to-speech pronunciation, Telegram progress reports, and optional parental-control integration.**

</div>

---

## 🎯 Overview

Coalide is a terminal-based English–Turkish vocabulary quiz application. It presents words from a local `words.csv` database in a two-level quiz: Level 1 reviews words you already know, and Level 2 introduces new ones. Questions are asked randomly in both directions (English → Turkish and Turkish → English). After each quiz session, performance statistics are saved locally and optionally sent to a Telegram chat. The UI is rendered in Turkish and uses colorful ASCII art animations.

---

## 🚀 Features

### Core Features

- **Two-Level Quiz System**: Level 1 covers previously seen/mastered words; Level 2 covers remaining vocabulary
- **Bidirectional Questions**: Words are tested in both English → Turkish and Turkish → English directions
- **Speech Synthesis**: Correct word pronunciations are played via gTTS/ElevenLabs + PyAudio after each answer
- **Progress Tracking**: Per-word accuracy and session statistics saved to local CSV files
- **Example Sentences**: Each word is shown with a fill-in-the-blank example sentence during the quiz
- **Configurable Timeouts**: Optional per-question answer time limit (set to unlimited by default)
- **Spam-Answer Protection**: Enforces a minimum time between question display and answer submission
- **Telegram Notifications**: Automatic quiz result reporting via a Telegram bot

### Admin Features

- **Admin Console (CLI)**: Password-protected command-line interface for adjusting quiz settings before a session
  - `set <key> <value>` — temporarily override a setting for the current session
  - `dset <key> <value>` — permanently save a setting to `config.json`
  - `show` — display the current configuration
- **BETA TUI Admin Console**: Experimental terminal user interface (`BETA_admin_console_test_TUI.py`) built with `asciimatics` — standalone, not yet integrated into the main app
- **Debug Mode**: Verbose logging enabled with the `-debug` flag; also suppresses screen-clear and ASCII animations for easier debugging

### Parental Control Integration (Optional)

- Communicates with a running [PCV2](https://github.com/cekirge1972/PCV2) parental-control server to add timed exceptions for applications
- Supports custom reasons and per-date tracking

### Data Management

- **Automatic Backup**: On startup, key data files are backed up to `~/.ProjectEnglish_Backups/` (last 10 backups kept)
- **Words Auto-Update**: Optionally checks GitHub for a newer `words.csv` and downloads it if one exists

---

## 📋 Requirements

### Python Packages

See `requirements.txt` for the full pinned list. Key packages:

| Group | Packages |
|---|---|
| User Interface | `asciimatics`, `colorama` |
| Audio | `PyAudio`, `pydub`, `gTTS`, `mutagen`, `pyglet` |
| Web / API | `requests` |
| Data Processing | `numpy`, `Pillow` |
| I/O | `python-dotenv`, `inputimeout` |

Install everything with:

```bash
pip install -r requirements.txt
```

### System Requirements

- **Python**: 3.12.x recommended
- **OS**: Primarily developed and tested on **Windows**. The restart helper spawns a new console window using the Windows `CREATE_NEW_CONSOLE` flag; all other functionality should work cross-platform.
- **Audio output device**: Required for text-to-speech playback. The app waits up to 5 seconds for a device to become available before skipping audio.
- **Telegram Bot** *(optional)*: Required only if `send_telegram_message` is enabled in the configuration.

---

## 🔧 Installation

### 1. Clone the repository

```bash
git clone https://github.com/MelihAydinYanibol/Coalide.git
cd Coalide
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv env
# Windows
env\Scripts\activate
# macOS / Linux
source env/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

On first run the application automatically creates a `.env` file with safe defaults:

```env
ADMIN_PASSWORD=0000
PARENTAL_CONTROL_URL=http://IP-TO-YOUR-PCV2-SERVER:5005
```

To enable Telegram reporting or change the admin password, edit `.env` and add:

```env
ADMIN_PASSWORD=your_secure_password
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
PARENTAL_CONTROL_URL=http://your-pcv2-server-ip:5005
```

### 5. (Optional) Customise configuration

`config.json` is created automatically on first run with the following defaults. Edit the file to change quiz behaviour:

```json
{
    "default_quiz_config": {
        "level_1_question_count": 20,
        "level_2_question_count": 50,
        "random_order": true,
        "pronounce_words": true,
        "send_telegram_message": true,
        "save_statistics": true
    },
    "dummy_mode": {
        "dummy_mode": false,
        "dummy_question_count": 100,
        "send_telegram_message": true,
        "pronounce_words": true
    },
    "general": {
        "spam_answer_proof": true,
        "set_time_for_pc": true,
        "set_time_for_tomorrow": false,
        "pc_time_multiplier": 1,
        "answer_timeout": -1
    }
}
```

> **Note**: `answer_timeout: -1` means no time limit. Set a positive integer (seconds) to enable timed questions.

---

## 📖 Usage

### Running the application

```bash
python main.py
```

The ASCII start menu loads, then the selection menu. Choose **"Varsayılan modda başlat"** (Start in default mode) to begin a quiz, or **"Admin kontrolü"** (Admin control) to adjust settings before starting.

### Debug mode

```bash
python main.py -debug
```

Enables verbose logging, disables screen-clearing, and skips ASCII animations so you can follow program flow in the terminal.

### Standalone Telegram test

```bash
python telegram_report.py
```

Sends a sample report message to verify your `BOT_TOKEN` and `CHAT_ID` are configured correctly.

### words.csv format

Each row in `words.csv` must have exactly five comma-separated fields:

```
<English word>,<Turkish translation>,<word type>,<example sentence — first half>,<example sentence — second half>
```

Example:

```
be,olmak,verb,He is,a teacher
have,sahip olmak,verb,I,a pen
```

---

## 🗂️ Project Structure

```
Coalide/
├── main.py                          # Main application entry point
├── telegram_report.py               # Telegram integration module
├── parental_connection.py           # Parental control (PCV2) integration
├── BETA_admin_console_test_TUI.py   # Experimental TUI admin console (standalone)
├── requirements.txt                 # Python dependencies
├── words.csv                        # Primary vocabulary database
├── words_v1.csv                     # Legacy vocabulary list (v1)
├── words_v3.csv                     # Legacy vocabulary list (v3)
│
├── ASCII/                           # ASCII art and animations
│   ├── ASCII_start_menu.py
│   ├── ASCII_selection_menu.py
│   ├── ASCII_LevelUp.py
│   └── Animations/
│       ├── video.py
│       ├── gifs.txt
│       └── DB_VDATA.csv
│
└── Manuals/                         # Utility scripts
    └── Create_daily_stats_manually.py
```

> **Runtime-generated files** (excluded from version control via `.gitignore`):
> `config.json`, `.env`, `analytics.csv`, `daily_stats.csv`, `statistics.csv`,
> `sent_tg_messages.json`, `pronunciations/` (cached TTS audio)

---

## 🔌 Integration Guides

### Telegram Integration

1. **Get a Bot Token**: Message [@BotFather](https://t.me/botfather) on Telegram, create a new bot, and copy the token.
2. **Get your Chat ID**: Start a conversation with your bot, then use [@userinfobot](https://t.me/userinfobot) to retrieve your `CHAT_ID`.
3. **Set variables in `.env`**:
   ```env
   BOT_TOKEN=your_bot_token_here
   CHAT_ID=your_chat_id_here
   ```
4. Ensure `send_telegram_message: true` in `config.json`.

### Parental Controls Integration

Coalide integrates with the [PCV2](https://github.com/cekirge1972/PCV2) parental-control server. Set the server address in `.env`:

```env
PARENTAL_CONTROL_URL=http://your-server-ip:5005
```

The application can automatically add timed exceptions for itself (or another executable) via `parental_connection.py`.

---

## ⚙️ Configuration Reference

| Section | Key | Default | Description |
|---|---|---|---|
| `default_quiz_config` | `level_1_question_count` | `20` | Number of Level-1 (known words) questions |
| `default_quiz_config` | `level_2_question_count` | `50` | Number of Level-2 (new words) questions |
| `default_quiz_config` | `random_order` | `true` | Randomise question order |
| `default_quiz_config` | `pronounce_words` | `true` | Play TTS audio after each answer |
| `default_quiz_config` | `send_telegram_message` | `true` | Send session report to Telegram |
| `default_quiz_config` | `save_statistics` | `true` | Write results to `statistics.csv` |
| `dummy_mode` | `dummy_mode` | `false` | Enable dummy/practice mode |
| `dummy_mode` | `dummy_question_count` | `100` | Questions per dummy-mode session |
| `general` | `spam_answer_proof` | `true` | Require ≥2 s between prompt and answer |
| `general` | `answer_timeout` | `-1` | Seconds to answer (`-1` = unlimited) |
| `general` | `set_time_for_pc` | `true` | Request parental-control time exception |
| `general` | `set_time_for_tomorrow` | `false` | Request exception for tomorrow instead of today |
| `general` | `pc_time_multiplier` | `1` | Multiplier for awarded PCV2 time (`2` doubles, `0.5` halves) |

---

## 📊 Data & Statistics

The application writes the following runtime files (all gitignored):

| File | Contents |
|---|---|
| `statistics.csv` | Per-answer record: timestamp, word, translation, given answer, correct/wrong/blank, level |
| `daily_stats.csv` | Daily summary: date, correct, wrong, blank, total, level, time elapsed |
| `analytics.csv` | Session completion timestamps per level |
| `sent_tg_messages.json` | Log of Telegram messages sent |
| `pronunciations/` | Cached MP3 files generated by gTTS/Elevenlabs |

---

## 🛠️ Troubleshooting

### Audio Issues

- Ensure an audio output device is connected and recognised by the OS.
- The app waits up to 5 seconds for a device to appear; if unavailable, audio is silently skipped.
- On Windows, verify that PyAudio installed correctly (`pip install PyAudio`).

### Telegram Issues

- Verify `BOT_TOKEN` and `CHAT_ID` are set correctly in `.env`.
- Run `python telegram_report.py` directly to test connectivity.
- Ensure your bot has permission to message the target chat.

### Parental Control Connection

- Verify `PARENTAL_CONTROL_URL` points to a running [PCV2](https://github.com/cekirge1972/PCV2) server.
- Connection errors are caught and logged; the quiz continues regardless.

### Debug Mode

Run with the `-debug` flag for verbose logs:

```bash
python main.py -debug
```

---

## 🤝 Contributing

Pull requests and issue reports are welcome. Please keep changes focused and describe what you changed and why.

---

## 🗺️ Roadmap

- [ ] Multi-language support
- [ ] Startup admin interface (press `-` on startup)
- [ ] Additional admin commands (e.g., `pos` for selecting a key by absolute position)
- [ ] Detailed statistics viewer and reset tool in admin controls
- [ ] Full integration of the TUI admin console (`BETA_admin_console_test_TUI.py`)
- [ ] Performance optimisations

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

**Last Updated**: March 2026

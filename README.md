# Coalide — Spaced-Repetition Vocabulary Trainer

<div align="center">

**A terminal-based English–Turkish vocabulary trainer built around SM-2 spaced repetition, per-word progress tracking, a credit-for-screen-time reward loop, and neural text-to-speech pronunciation.**

</div>

---

## 🎯 Overview

Coalide teaches vocabulary by scheduling each word with the **SM-2 spaced-repetition algorithm**: words you know well come back less often, and words you struggle with come back sooner. Questions are asked in both directions (source → target and target → source) with a fill-in-the-blank example sentence, and the correct word and sentence are read aloud after every answer.

Every correct answer earns **credits**, which can be redeemed for real screen time through an optional [PCV2](https://github.com/cekirge1972/PCV2) parental-control server — turning study into an allowance system for kids. The app supports **multiple users**, keeps each learner's progress and balance separate, and can **update itself** from GitHub releases.

The interface is a [Textual](https://textual.textualize.io/) TUI, rendered in Turkish by default, and everything from languages to pricing lives in a self-repairing `config.json`.

> **Status:** `2.0.0` — a ground-up, object-oriented rewrite of the original procedural app. See [CHANGELOG.md](CHANGELOG.md) for history.

---

## 🚀 Features

### Learning engine
- **SM-2 spaced repetition** — per-word `ease_factor`, `interval`, and `next_review_date` drive scheduling (`sm2.py`).
- **Bidirectional questions** — each word is asked source → target or target → source at random.
- **Example sentences** — every prompt shows a fill-in-the-blank sentence for context.
- **Daily New-Word Cap** — limits how many brand-new words are introduced per day (default 15).
- **No-Repeat Window** — a word can't reappear within the last *N* questions of a session (default 8).
- **Never runs dry** — if nothing is strictly due, the soonest-upcoming word is served early instead of ending the session.
- **Live success rates** — per-word accuracy (last 10 attempts) is shown and color-coded before each question.
- **Turkish-aware matching** — answers are normalized so Turkish `İ/I` casing is handled correctly.
- **Spam protection** — rejects answers submitted in under 2 seconds so learners actually think.
- **Optional answer timeout** — set a per-question time limit, or leave it unlimited.

### Audio
- **Neural TTS** — pronunciations via **ElevenLabs** (multilingual), with automatic **gTTS** fallback when ElevenLabs is unavailable or out of quota.
- **Multi-key rotation** — supports several ElevenLabs API keys and picks one with remaining quota.
- **On-disk cache** — generated audio is cached in `pronunciations/`; replay a word or sentence any time with `P` / `S`.
- **Device-loss resilience** — waits for an output device to reappear and skips playback gracefully if none is found.

### Rewards & parental controls
- **Credit system** — earn credits for correct answers; balances are per-user (`<username>_data.json`).
- **Redeem for screen time** — spend credits to grant real minutes via the [PCV2](https://github.com/cekirge1972/PCV2) API, for today, tomorrow, or a specific future date.
- **Escalating pricing** — each additional hour redeemed *for a given date* costs progressively more, tracked independently per date.
- **Weekly reset** — balances can auto-reset at the start of each week (Monday 00:00).
- **Safe redemption** — credits are only spent when the grant actually succeeds (or is queued by the server); otherwise they're refunded.

### Platform
- **Multiple users** — a username is captured once and remembered; each user keeps separate progress and credits.
- **Self-updating** — on launch, checks GitHub releases and updates itself, unless it detects a developer git checkout (or `-dev`).
- **Words auto-update** — checks GitHub for a newer `words.json` and hot-reloads it.
- **Automatic backups** — key data files (and optionally the audio cache) are backed up to `~/.ProjectEnglish_Backups/` on startup; the last 10 are kept.
- **Self-repairing config** — missing config keys are filled in from defaults automatically.

---

## 📋 Requirements

- **Python** 3.12.x recommended (the `-release-ready` tool relies on `shutil` behavior introduced in 3.12).
- **OS** — developed and tested primarily on **Windows**; the quiz, audio, and TUI are otherwise cross-platform.
- **Audio output device** — required for pronunciation playback (waits up to 5 s, then skips).
- **PCV2 server** *(optional)* — only needed for redeeming credits for screen time.
- **ElevenLabs API key** *(optional)* — for neural TTS; without it, Coalide falls back to gTTS.

### Python packages (`requirements.txt`)

| Group | Packages |
|---|---|
| UI | `textual`, `colorama` |
| Audio / TTS | `elevenlabs`, `gTTS`, `pyglet`, `mutagen` |
| Networking | `Requests` |
| Input / env | `inputimeout`, `python-dotenv` |

> **Note:** `pyaudio` is used only to detect whether an output device is present. It is an optional dependency — if it isn't installed, Coalide degrades gracefully and audio device-detection is skipped.

```bash
pip install -r requirements.txt
```

---

## 🔧 Installation

### 1. Clone

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

### 4. Configure `.env`

On first run Coalide creates a `.env` file with safe placeholders:

```env
ADMIN_PASSWORD=0000
BOT_TOKEN=ENTER_YOUR_TOKEN_HERE
CHAT_ID=YOUR_CHAT_ID_HERE
PARENTAL_CONTROL_URL=http://IP-TO-YOUR-PCV2-SERVER:5005
ELEVENLABS_API_KEY=[]
```

Fill in what you need:

| Variable | Purpose |
|---|---|
| `ELEVENLABS_API_KEY` | ElevenLabs key(s) for neural TTS. Single key or a list: `[key1, key2]`. Leave as `[]` to use gTTS. |
| `PARENTAL_CONTROL_URL` | Base URL of your [PCV2](https://github.com/cekirge1972/PCV2) server, used when redeeming credits. |
| `ELEVENLABS_VOICE_ID` | *(optional)* Override the default ElevenLabs voice. |
| `ADMIN_PASSWORD` | Reserved for the admin menu. |
| `BOT_TOKEN` / `CHAT_ID` | Reserved for Telegram reporting. |

### 5. (Optional) Tune `config.json`

`config.json` is generated on first run with the defaults below and self-repairs if keys go missing. See the [Configuration Reference](#️-configuration-reference).

---

## 📖 Usage

### Launch the app

```bash
python coalide.py
```

This checks for updates, prepares config/words, and opens the Textual main menu. On first launch you'll be asked for a username. Menu options (Turkish):

| Menu item | Meaning | Status |
|---|---|---|
| 📝 Öğrenmeye Başla! | Start the spaced-repetition quiz | ✅ |
| 💰 Kredilerini Kullan! | Redeem credits for screen time | ✅ |
| 📚 Pratik Modu | Practice mode | 🚧 planned |
| 📊 İstatistikler | Statistics viewer | 🚧 planned |
| ⚙️ Admin Modu | Admin controls | 🚧 planned |
| 🚪 Çıkış | Quit (shuts the computer down) | ✅ |

Press `F2` inside the menu to open the command palette for the same actions plus developer shortcuts.

### During a quiz

- Type your answer and press **Enter**.
- After each answer: **Enter** to continue, **P** to replay the word, **S** to replay the sentence.
- Type **exit** to leave the session.

### Run the quiz directly (skips the menu)

```bash
python new_master.py
```

### Debug mode

```bash
python coalide.py -debug
```

Enables verbose logging and disables screen-clearing so you can follow program flow.

---

## 🛠️ Command-Line Tools (`cli.py`)

Run these as flags on the app (e.g. `python coalide.py -pack-data`). Add `--help` after any command for details.

| Command | Description |
|---|---|
| `-pack-data` | Copies user data files into a `packaged_data/` folder for backup. |
| `-create-tts-cache` | Pre-generates TTS audio for all words/sentences. Flags: `-gtts`, `-words`, `-sentences`, `-all`, `-force`. |
| `-release-ready` | **Destructive.** Wipes all user data, `.git`, virtualenvs, caches and config to prepare a clean release. Double-confirmation required. |
| `-debug` | Verbose logging. |
| `-dev` | Forces "development checkout" mode, disabling auto-update. |
| `-help` | Lists available commands. |

---

## 🗂️ Project Structure

```
Coalide/
├── coalide.py              # Launcher: self-update check → boot menu
├── menu.py                 # Textual TUI main menu
├── new_master.py           # Quiz engine, session loop, credit/redeem flow, backups
├── sm2.py                  # SM-2 scheduling, question selection, quality scoring
├── word_engine.py          # words.json ↔ Word objects, progress merge
├── audio_engine.py         # TTS (ElevenLabs → gTTS fallback) + playback
├── parental_connection.py  # PCV2 parental-control API client
├── cli.py                  # -pack-data / -create-tts-cache / -release-ready
├── utils.py                # config load/repair, logging, current-user
│
├── objects/
│   ├── word_obj.py         # Word model + progress.json persistence
│   ├── question_obj.py     # Question model (prompt / expected answer)
│   └── balance_obj.py      # User, Balance, credit pricing & redemption
│
├── words.json              # Vocabulary database (word definitions only)
├── config.json             # App configuration (generated, self-repairing)
├── requirements.txt
│
├── ASCII/                  # ASCII art / animations (legacy menus)
├── Manuals/                # Utility scripts
└── testers/                # Standalone test scripts
```

### Runtime-generated files (gitignored)

| File / folder | Contents |
|---|---|
| `.env` | Secrets & server URLs |
| `config.json` | Configuration (recreated with defaults if deleted) |
| `progress.json` | Per-word SM-2 state and attempt history (keyed by word) |
| `current_user.json` | The currently logged-in username |
| `<username>_data.json` | That user's credit balance & redeemed-minutes history |
| `version.json` | Locally installed release tag (for auto-update) |
| `pronunciations/` | Cached TTS `.mp3` files |

---

## 🧠 How Scheduling Works

Words live in `words.json` as static definitions; all learning state lives separately in `progress.json`, merged at load time. Each answer is graded into an SM-2 **quality** score (0–5) from correctness **and** speed (a per-word time cap based on answer length):

| | Within time cap | Over time cap |
|---|---|---|
| **Correct** | 5 | 4 |
| **Wrong** | 1 | 2 |
| **Blank** | 0 | 0 |

- Quality **≥ 3** advances the word (interval grows by its ease factor); **< 3** resets it to be re-asked today.
- Brand-new words carry a sentinel date so they surface first, but only up to the **Daily New-Word Cap** per day.
- The **No-Repeat Window** keeps recently seen words from bunching up within a session.

---

## 💰 Credits & Screen Time

- Each correct answer awards **7 credits** (`user.add_credits(7)`).
- Redeeming converts credits → minutes of screen time via the PCV2 API.
- Cost per minute starts at `BASE_RATE_PER_MINUTE` and rises by `ESCALATION_PER_HOUR` for each hour already redeemed **for that date**, so banking time far ahead stays affordable while marathon days on a single date get pricier.
- Redemptions can target **today**, **tomorrow**, or a **specific future date**.
- If `Credit_Reset_Weekly` is on, balances reset every Monday.

---

## ⚙️ Configuration Reference

| Key | Default | Description |
|---|---|---|
| `Daily_New_Word_Cap` | `15` | Max brand-new words introduced per day |
| `No_Repeat_Window` | `8` | A word can't repeat within this many questions |
| `Repo_Owner` | `MelihAydinYanibol` | GitHub owner for auto-update & words sync |
| `Repo_Name` | `Coalide` | GitHub repo for auto-update & words sync |
| `Update_Prereleases` | `false` | Also accept prereleases when auto-updating |
| `Source_Language` | `Türkçe` | Label for the source language |
| `Target_Language` | `İngilizce` | Label for the target language |
| `BASE_RATE_PER_MINUTE` | `5` | Credits per minute of screen time (base rate) |
| `ESCALATION_PER_HOUR` | `0.5` | Per-hour price escalation for same-date redemptions |
| `SPAM_PROTECTION` | `true` | Reject answers submitted in under 2 seconds |
| `INPUT_TIMEOUT` | `0` | Per-question answer time limit in seconds (`0` = unlimited) |
| `Credit_Reset_Weekly` | `true` | Reset balances every Monday |
| `BACKUP_PRONUNCIATIONS` | `true` | Include the audio cache in startup backups |

---

## 🔌 Parental Control Integration (PCV2)

Coalide talks to a [PCV2](https://github.com/cekirge1972/PCV2) server to grant screen-time exceptions.

1. Run a PCV2 server on your network.
2. Set its address in `.env`:
   ```env
   PARENTAL_CONTROL_URL=http://your-server-ip:5005
   ```
3. Redeem credits from the menu (**Kredilerini Kullan!**). On success, PCV2 adds the granted minutes for the chosen date. If the server is unreachable, credits are refunded automatically.

---

## 🛠️ Troubleshooting

**No audio plays**
- Confirm an output device is connected and recognized by the OS.
- Coalide waits up to 5 s for a device, then skips playback silently.
- Neural TTS needs a valid `ELEVENLABS_API_KEY`; otherwise it falls back to gTTS (needs internet).

**Credits won't redeem**
- Verify `PARENTAL_CONTROL_URL` points at a running PCV2 server. Connection failures refund credits and cancel the redemption.

**Auto-update didn't run**
- Auto-update is intentionally skipped on developer git checkouts and when launched with `-dev`. A downloaded release without a `.git` folder will update normally.

**Something looks broken after editing `config.json`**
- Delete it — Coalide regenerates it from defaults on next launch. Missing keys are also repaired automatically.

**Verbose logs**
```bash
python coalide.py -debug
```

---

## 🗺️ Roadmap

- [ ] Practice mode (Pratik Modu)
- [ ] In-app statistics viewer (İstatistikler)
- [ ] Admin controls panel (Admin Modu)
- [ ] Telegram progress reporting (wired into the rewrite)
- [ ] Cross-platform polish

---

## 🤝 Contributing

Pull requests and issues are welcome. Keep changes focused and describe what you changed and why. Follow the [Keep a Changelog](https://keepachangelog.com/) format in [CHANGELOG.md](CHANGELOG.md).

---

## 📄 License

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

---

**Last Updated:** July 2026 · **Version:** 2.0.0

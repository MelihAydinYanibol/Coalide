# Coalide — Spaced-Repetition Vocabulary Trainer

<div align="center">

**An English–Turkish vocabulary trainer built around SM-2 spaced repetition, per-word progress tracking, a credit-for-screen-time reward loop and neural text-to-speech — with a terminal app, a browser app, and an optional parent-side dashboard.**

</div>

---

## 🎯 Overview

Coalide teaches vocabulary by scheduling each word with the **SM-2 spaced-repetition algorithm**: words you know well come back less often, and words you struggle with come back sooner. Questions are asked in both directions (source → target and target → source) with a fill-in-the-blank example sentence, and the correct word and sentence are read aloud after every answer.

Every correct answer earns **credits**, which can be redeemed for real screen time through an optional [PCV2](https://github.com/cekirge1972/PCV2) parental-control server — turning study into an allowance system for kids. The app supports **multiple users**, keeps each learner's progress and balance separate, and **updates itself** from GitHub releases.

The project ships **three surfaces**, all sharing the same `words.json` and the same SM-2 core:

| Surface | What it is | Docs |
|---|---|---|
| **Terminal app** (repo root) | The main [Textual](https://textual.textualize.io/) TUI — quiz, practice, statistics, redeem, settings and admin. Turkish UI, Windows-first, built for a kiosk machine. | this file |
| **Web app** (`webapp/`) | A Flask port of the trainer for the browser, with per-user progress, a full statistics dashboard and a parent admin panel. | [`webapp/README.md`](webapp/README.md) |
| **Parental server** (`serverside/`) | A zero-dependency stdlib server the *parent* runs: live stats dashboard, remote config/word admin, daily Telegram/ntfy report. Never ships in a release. | [`serverside/README.md`](serverside/README.md) |

The vocabulary database covers the full **Oxford 3000** — 3,012 words with example sentences, word types and multiple accepted Turkish meanings.

> **Status:** `v2.3.4` — see [CHANGELOG.md](CHANGELOG.md) for the full history.

---

## 🚀 Features

### Learning engine
- **SM-2 spaced repetition** — per-word `ease_factor`, `interval`, and `next_review_date` drive scheduling (`sm2.py`).
- **Bidirectional questions** — each word is asked source → target or target → source at random.
- **Example sentences** — every prompt shows a fill-in-the-blank sentence for context.
- **Daily New-Word Cap** — limits how many brand-new words are introduced per day (default 15).
- **No-Repeat Window** — a word can't reappear within the last *N* questions of a session (default 8).
- **Pinned questions** — a question's direction *and* which alias is shown are frozen in `.pending_question.json` until it is graded, so quitting and restarting can't re-roll it into a free hint.
- **Optional new-word shuffle** — `SHUFFLE_NEW_WORDS` introduces new words in random order instead of `words.json` order.
- **Never runs dry** — if nothing is strictly due, the soonest-upcoming word is served early instead of ending the session.
- **Live success rates** — per-word accuracy (last 10 attempts) is shown and color-coded before each question.
- **Turkish-aware matching** — answers are normalized so Turkish `İ/I` casing is handled correctly.
- **Spam protection** — rejects answers submitted in under 2 seconds so learners actually think.
- **Optional answer timeout** — set a per-question time limit, or leave it unlimited.
- **Offline gate** — with `REQUIRE_INTERNET` on, the quiz refuses to start without a connection (checked with a quick TCP probe to `8.8.8.8:53`). Only the quiz is gated; the menu, practice, stats and redeem screens stay usable offline.

### Screens
- **📝 Öğrenmeye Başla** — the spaced-repetition quiz (`new_master.py`).
- **📚 Pratik Modu** — a hands-off flashcard run through the whole word list: each word is shown and pronounced, then its meaning and sentence, advancing on a timer. Any key exits (`practice.py`).
- **💰 Kredilerini Kullan** — a redeem TUI with a live balance, date picker, minute picker, an **En Fazla** button for the largest amount the balance can buy, and live pricing on the confirm button (`redeem_menu.py`).
- **📊 İstatistikler** — six tabs (Genel Bakış, Krediler, Haftalık & Günlük, Süre & Hız, Kelimeler, Gelecek & SM-2): overview tiles, SM-2 maturity buckets, hardest words, daily/weekly charts, daily study time against the daily time limit with an answer-speed breakdown, time-of-day activity, a question-direction comparison, a per-word table filterable by maturity bucket, and an SM-2 health view (`stats_menu.py`).
- **⚙️ Ayarlar** — Hakkında (version, user, language pair, word count; local paths masked behind the admin password), Ses (a slider bound to the *real* Windows master volume via Core Audio, with a configurable floor), and Yönetim (opens admin, plus a process-local **Sudo** unlock) (`settings_menu.py`).
- **🛠 Admin Paneli** — password-gated parent panel: Krediler (view/adjust balance), Ayarlar (edit every `config.json` key with type-aware inputs and Turkish descriptions), Kelimeler (browse/add/edit/delete words, keeping progress in sync, plus per-maturity-bucket progress resets) (`admin.py`).
- **🚪 Çıkış** — a dialog offering log out or shut down.

Press `F2` anywhere in the menu for the command palette: the same actions plus developer shortcuts (restart in debug, pack data, build the TTS cache, open admin).

### Audio
- **Neural TTS** — pronunciations via **ElevenLabs** (multilingual), with automatic **gTTS** fallback when ElevenLabs is unavailable or out of quota.
- **Multi-key rotation** — supports several ElevenLabs API keys and picks one with remaining quota.
- **On-disk cache** — generated audio is cached in `pronunciations/`; replay a word or sentence any time with `P` / `S`.
- **Device-loss resilience** — waits for an output device to reappear and skips playback gracefully if none is found.
- **Parent-controlled sound** — `Sound_Effects` gates all playback and `Minimum_Volume` sets a floor the settings slider won't go below (which also disables the mute switch), so a learner can't silence the lesson.

### Rewards & parental controls
- **Credit system** — earn credits for correct answers; balances are per-user (`<username>_data.json`).
- **Credit window** — credits are only earned between `Credit_Window_Start` and `Credit_Window_End` (default 07:00–22:00). Answers outside the window still count for SM-2, they just don't pay.
- **Redeem for screen time** — spend credits to grant real minutes via the [PCV2](https://github.com/cekirge1972/PCV2) API, for today, tomorrow, or a specific date. When the weekly reset is on, redemptions are capped at the current week (through Sunday) so credits can't be banked past the reset.
- **Escalating pricing** — each additional hour redeemed *for a given date* costs progressively more, tracked independently per date.
- **Weekly reset** — balances can auto-reset at the start of each week (Monday 00:00).
- **Safe redemption** — credits are only spent when the grant actually succeeds (or is queued by the server); otherwise they're refunded.

### Parent-side monitoring (optional)
- **Stats push** — every time the menu opens, a snapshot of `build_stats()` is pushed to the parental server on a background thread (`stats_reporter.py`). Silent on failure, and off entirely until `STATS_SERVER_URL` points at a real address.
- **Config & word sync** — the same menu-open hook pushes `config.json` / `words.json` plus a hash of `ADMIN_PASSWORD`, then pulls back any parent edits and applies them locally, pruning progress for deleted words (`config_sync.py`). Revision-tracked, so each change applies exactly once.
- **Remote progress resets** — a reset queued from the web admin is applied on the child's device at the next sync, after backing up `progress.json`.
- **Daily report** — the server can send a once-a-day summary over Telegram, ntfy.sh, or both, including the day's study time and what is left of the daily time limit.

### Platform
- **Multiple users** — a username is captured once and remembered; each user keeps separate progress and credits. Input is sanitized (whole ANSI sequences stripped) so terminal mouse escapes can't corrupt the saved name.
- **Dependency self-check** — on launch, `dependency_check.py` (stdlib only) verifies every package in `requirements.txt` and pip-installs anything missing, so a fresh machine with base Python just works.
- **Self-updating** — checks GitHub releases on launch and updates itself, unless it detects a developer git checkout (or `-dev`). Local data, `.env` and `words.json` are never overwritten by an update.
- **Words auto-update** — checks GitHub for a newer `words.json` and hot-reloads it.
- **Kiosk mode** — a low-level keyboard hook swallows Alt+F4 (`bypasser.py`), and `-create-kiosk-batch` writes a `launch_kiosk.bat` that relaunches Coalide in a loop if it ever exits.
- **Automatic backups** — key data files (and optionally the audio cache) are backed up to `~/.ProjectEnglish_Backups/` on startup; the last 10 are kept.
- **Self-repairing config** — missing config keys are filled in from defaults automatically.

---

## 📋 Requirements

- **Python** 3.12.x recommended (the `-release-ready` tool relies on `shutil` behavior introduced in 3.12).
- **OS** — the terminal app is **Windows-first**: practice mode uses `msvcrt`, the volume control uses the Windows Core Audio API, and the kiosk/exit actions shell out to `shutdown`. For other platforms, use the [web app](webapp/README.md). The parental server is cross-platform.
- **Audio output device** — required for pronunciation playback (waits up to 5 s, then skips).
- **PCV2 server** *(optional)* — only needed for redeeming credits for screen time.
- **ElevenLabs API key** *(optional)* — for neural TTS; without it, Coalide falls back to gTTS.

### Python packages (`requirements.txt`)

| Group | Packages |
|---|---|
| UI | `textual`, `colorama`, `asciimatics` |
| Audio / TTS | `elevenlabs`, `gTTS`, `pyglet`, `mutagen` |
| Networking | `Requests` |
| Input / env | `inputimeout`, `python-dotenv` |
| Media / math | `Pillow`, `numpy` |

They are installed automatically on first launch, but you can do it yourself:

```bash
pip install -r requirements.txt
```

> **Note:** `pyaudio` is *not* in `requirements.txt`. It is used only to detect whether an output device is present — if it isn't installed, Coalide degrades gracefully and skips the device check.

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

(Or skip it — `coalide.py` installs anything missing on launch.)

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
| `ADMIN_PASSWORD` | Gates the admin panel, the settings Sudo unlock and the parental server's web admin. **Change it from `0000`.** |
| `ELEVENLABS_API_KEY` | ElevenLabs key(s) for neural TTS. Single key or a list: `[key1, key2]`. Leave as `[]` to use gTTS. |
| `ELEVENLABS_VOICE_ID` | *(optional)* Override the default ElevenLabs voice. |
| `PARENTAL_CONTROL_URL` | Base URL of your [PCV2](https://github.com/cekirge1972/PCV2) server, used when redeeming credits. |
| `BOT_TOKEN` / `CHAT_ID` | Legacy Telegram reporting fields. Daily reports now live in `serverside/.env` (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`). |

### 5. (Optional) Tune `config.json`

`config.json` is generated on first run with the defaults below and self-repairs if keys go missing. See the [Configuration Reference](#️-configuration-reference), or edit it from the admin panel instead of by hand.

---

## 📖 Usage

### Launch the app

```bash
python coalide.py
```

This installs missing dependencies, checks for updates, prepares config/words, and opens the Textual main menu. On first launch you'll be asked for a username. Menu options (Turkish):

| Menu item | Meaning |
|---|---|
| 📝 Öğrenmeye Başla! | Start the spaced-repetition quiz |
| 📚 Pratik Modu | Practice mode — flashcard run through the word list |
| 💰 Kredilerini Kullan! | Redeem credits for screen time |
| 📊 İstatistikler | Statistics screen |
| ⚙️ Ayarlar | Settings (about, audio, admin access) |
| 🚪 Çıkış | Log out or shut the computer down |

Press `F2` inside the menu to open the command palette for the same actions plus developer shortcuts and the admin panel.

### During a quiz

- Type your answer and press **Enter**.
- After each answer: **Enter** to continue, **P** to replay the word, **S** to replay the sentence.
- Type **exit** to leave the session.

### Run a screen directly (skips the menu)

```bash
python new_master.py     # quiz
python practice.py       # practice mode
python redeem_menu.py    # redeem credits
python stats_menu.py     # statistics
python settings_menu.py  # settings
python admin.py          # admin panel
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
| `-create-kiosk-batch` | Writes `launch_kiosk.bat`, which relaunches Coalide in a loop so it can't be closed for good. |
| `-release-ready` | **Destructive.** Wipes all user data, `.git`, `serverside/`, virtualenvs, caches and config to prepare a clean release. Double-confirmation required. |
| `-debug` | Verbose logging. |
| `-dev` | Forces "development checkout" mode, disabling auto-update. |
| `-help` | Lists available commands. |

---

## 🗂️ Project Structure

```
Coalide/
├── coalide.py              # Launcher: dependency check → self-update → boot menu
├── dependency_check.py     # Installs anything missing from requirements.txt (stdlib only)
├── menu.py                 # Textual TUI main menu (+ stats push / config sync hooks)
├── new_master.py           # Quiz engine, session loop, credits, backups
├── practice.py             # Pratik Modu — flashcard run through the word list
├── redeem_menu.py          # Kredilerini Kullan — redeem TUI
├── stats_menu.py           # İstatistikler — statistics TUI + statistics.csv answer log
├── settings_menu.py        # Ayarlar — about / volume / admin access, sudo unlock
├── admin.py                # Admin paneli — credits, config, words, progress resets
├── sm2.py                  # SM-2 scheduling, question selection, quality scoring
├── word_engine.py          # words.json ↔ Word objects, progress merge
├── audio_engine.py         # TTS (ElevenLabs → gTTS fallback) + playback
├── parental_connection.py  # PCV2 parental-control API client
├── stats_reporter.py       # Pushes stats snapshots to the parental server
├── config_sync.py          # Pulls parent-made config/word/reset changes back down
├── bypasser.py             # Kiosk: low-level hook that swallows Alt+F4
├── cli.py                  # -pack-data / -create-tts-cache / -release-ready / …
├── utils.py                # config load/repair, logging, current-user, kiosk batch
│
├── objects/
│   ├── word_obj.py         # Word model + progress.json persistence
│   ├── question_obj.py     # Question model (prompt / expected answer)
│   └── balance_obj.py      # User, Balance, credit pricing & redemption
│
├── webapp/                 # Flask web version (own README + requirements)
├── serverside/             # Parent-side stats server & web admin (never ships)
│
├── words.json              # Vocabulary database — 3,012 Oxford 3000 entries
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
| `statistics.csv` | One row per answered question (time, word, result, given, expected, prompt, direction, time spent) |
| `current_user.json` | The currently logged-in username |
| `<username>_data.json` | That user's credit balance & redeemed-minutes history |
| `.pending_question.json` | The question currently on screen, so restarting can't re-roll it |
| `.config_sync.json` | Last config/words revision applied from the parental server |
| `version.json` | Locally installed release tag (for auto-update) |
| `launch_kiosk.bat` | Kiosk relaunch loop (only if you ran `-create-kiosk-batch`) |
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
- A word whose interval reaches **21 days** counts as *learned* on the statistics screen; the maturity buckets are Yeni (≤1g), Öğreniliyor (2–6g), Genç (1–3 hafta), Olgun (3h–2 ay), Usta (2 ay +).

---

## 💰 Credits & Screen Time

- Each correct answer awards **7 credits** (`user.add_credits(7)`), but only inside the credit window (`Credit_Window_Start` – `Credit_Window_End`, default 07:00–22:00).
- Redeeming converts credits → minutes of screen time via the PCV2 API.
- Cost per minute starts at `BASE_RATE_PER_MINUTE` and rises by `ESCALATION_PER_HOUR` for each hour already redeemed **for that date**, so spreading time across days stays affordable while marathon days on a single date get pricier.
- Redemptions can target **today**, **tomorrow**, or a **specific date**.
- If `Credit_Reset_Weekly` is on, balances reset every Monday — and redemptions are limited to the current week (through Sunday), so credits can't be converted into screen time that outlives the reset. With the flag off, any future date is allowed.
- Total redemptions for a single date are capped at **24 hours (1440 minutes)** — a day has no more minutes to grant.

---

## ⚙️ Configuration Reference

| Key | Default | Description |
|---|---|---|
| `Daily_New_Word_Cap` | `15` | Max brand-new words introduced per day |
| `No_Repeat_Window` | `8` | A word can't repeat within this many questions |
| `SHUFFLE_NEW_WORDS` | `false` | Introduce new words in random order instead of `words.json` order |
| `Repo_Owner` | `MelihAydinYanibol` | GitHub owner for auto-update & words sync |
| `Repo_Name` | `Coalide` | GitHub repo for auto-update & words sync |
| `Update_Prereleases` | `false` | Also accept prereleases when auto-updating |
| `Source_Language` | `Türkçe` | Label for the source language |
| `Target_Language` | `İngilizce` | Label for the target language |
| `BASE_RATE_PER_MINUTE` | `5` | Credits per minute of screen time (base rate) |
| `ESCALATION_PER_HOUR` | `0.5` | Per-hour price escalation for same-date redemptions |
| `SPAM_PROTECTION` | `true` | Reject answers submitted in under 2 seconds |
| `INPUT_TIMEOUT` | `0` | Per-question answer time limit in seconds (`0` = unlimited) |
| `DAILY_COALIDE_TIME_LIMIT` | `0` | Daily limit in seconds on time spent answering questions (`0` = unlimited) |
| `Credit_Reset_Weekly` | `true` | Reset balances every Monday |
| `Credit_Window_Start` | `07:00` | Time of day credit earning starts |
| `Credit_Window_End` | `22:00` | Time of day credit earning stops |
| `PRONOUNCE_WORDS` | `true` | Read the word aloud after an answer |
| `PRONOUNCE_SENTENCES` | `true` | Read the example sentence aloud after an answer |
| `BACKUP_PRONUNCIATIONS` | `true` | Include the audio cache in startup backups |
| `Sound_Effects` | `true` | Master gate for all playback; the Ayarlar switch is locked until Sudo |
| `Minimum_Volume` | `25` | Floor (%) the settings slider won't go below; also disables mute (`0` = no floor) |
| `KIOSK_MODE` | `false` | Kiosk mode: relaunch the app automatically when it closes |
| `BYPASS_SHORTCUTS` | `true` | Block escape shortcuts such as Alt+F4 |
| `REQUIRE_INTERNET` | `true` | Refuse to start the quiz while offline |
| `STATS_REPORTING_ENABLED` | `true` | Push stats snapshots to the parental server |
| `STATS_SERVER_URL` | *(placeholder)* | Parental server address; nothing is sent while it holds the placeholder |
| `CONFIG_SYNC_ENABLED` | `true` | Pull parent-made config/word/reset changes from the server |

---

## 🌐 Web App (`webapp/`)

A Flask port of the trainer that runs in a browser, reusing the same `words.json` and SM-2 core. It keeps per-user progress under `webapp/data/`, pronounces words through the browser's Web Speech API (no TTS keys needed), ships the full İstatistikler dashboard (including the Süre & Hız tab, since it logs each answer's duration and direction too), and has its own parent admin panel with per-user config overlays.

```bash
cd webapp
pip install -r requirements.txt
python app.py     # http://localhost:6656
```

Full details — config layering, the admin panel, importing a terminal user, production notes — are in [`webapp/README.md`](webapp/README.md).

> The web app records redemptions locally rather than calling PCV2, since a web deployment usually can't reach a device on the family LAN.

---

## 🖥️ Parental Server (`serverside/`)

An optional, **zero-dependency** server the parent runs on their own machine. The child's app pushes a stats snapshot and its config on every menu open; the server renders a live dashboard (six tabs, each chart with its own time window and a table view: progress, credits, daily activity, study time and answer speed, words, review forecast), sends a daily report over Telegram and/or ntfy.sh, and offers a password-gated web admin for editing config, words and queuing progress resets remotely.

```bash
cd serverside
python server.py          # listens on 0.0.0.0:5055
```

Then point the child's `config.json` at it:

```json
"STATS_REPORTING_ENABLED": true,
"STATS_SERVER_URL": "http://192.168.1.50:5055"
```

The admin password is hashed **in the browser**, so the plaintext never reaches the server. Full setup is in [`serverside/README.md`](serverside/README.md).

> This folder is development/parent-side infrastructure and never ships in a Coalide release — `python cli.py -release-ready` deletes it.

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
- Check that `Sound_Effects` is on in `config.json` — it gates all playback and is locked for learners (unlock with Sudo or the admin panel).
- Neural TTS needs a valid `ELEVENLABS_API_KEY`; otherwise it falls back to gTTS (needs internet).

**The quiz won't start**
- `REQUIRE_INTERNET` is on by default and blocks the quiz while offline. Everything else (menu, practice, stats, redeem) still works — set `"REQUIRE_INTERNET": false` to lift the gate.

**Credits won't redeem**
- Verify `PARENTAL_CONTROL_URL` points at a running PCV2 server. Connection failures refund credits and cancel the redemption.
- Check the credit window: correct answers outside `Credit_Window_Start`–`Credit_Window_End` don't pay.

**Parent edits aren't reaching the child**
- Sync only runs when the main menu opens (or is returned to). Confirm `CONFIG_SYNC_ENABLED` is on and `STATS_SERVER_URL` is a real address — the shipped placeholder disables both sync and reporting.

**The volume slider won't go down**
- That's `Minimum_Volume` (default 25%). Use the **Sudo** button in Ayarlar → Yönetim with the admin password to unlock it for that window, or change the key from the admin panel.

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

- [x] Practice mode (Pratik Modu)
- [x] In-app statistics viewer (İstatistikler)
- [x] Admin controls panel (Admin Modu)
- [x] Settings menu (Ayarlar)
- [x] Parent-side dashboard and remote admin
- [x] Browser version of the trainer
- [x] Full Oxford 3000 vocabulary coverage
- [ ] Telegram progress reporting from the client itself (currently server-side only)
- [ ] Cross-platform polish for the terminal app (it is Windows-only today)

---

## 🤝 Contributing

Pull requests and issues are welcome. Keep changes focused and describe what you changed and why. Follow the [Keep a Changelog](https://keepachangelog.com/) format in [CHANGELOG.md](CHANGELOG.md).

---

## 📄 License

Licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

---

**Last Updated:** September 2026 · **Version:** v2.3.4

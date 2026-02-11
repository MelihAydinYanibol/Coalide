# ProjectEnglish
A small Python project to help with English practice and reporting. Provides CLI/TUI helpers, data files for words/pronunciations, and scripts to generate reports (including Telegram integration).

## Future Features
- [x] Show the words type (Noun or Verb) when asking questions
- [ ] Checking for bad audio files when downloading
- [ ] Startup admin interface (press - on startup) UI and menu itself
- [ ] More commmands in admin controls (pos command for selecting an key with its abs position)
- [ ] Colorama with question asking/answering and with the stats
- [ ] Admin Controls (on setup) will have detailed statistics and can control/manipulate stats. Admin controls will also have a way to reset statistic for test purposes
- [ ] Telegram report tool will also include that days leaderboard for words
- [ ] Optimization
- [ ] POTENTIAL : Admin Console with TUI with dropback to legacy

**(BELLOW THIS TEXT IS WRITTEN BY AI)**

**Status:** Working prototype — scripts and data provided; see usage below.

**Main scripts:**
- `main.py` — project entry point / primary workflow
- `telegram_report.py` — generate/send Telegram reports
- `test.py` — quick test harness
- `ASCII/` — TUI/ASCII helper scripts

## Features
- Manage and review words from `words.csv` and `pronunciations/`.
- Generate CSV analytics (`analytics.csv`, `daily_stats.csv`, `statistics.csv`).
- Send reports or messages via Telegram (see `telegram_report.py`).

## Files
- `words.csv` — word list used by the app
- `pronunciations/` — pronunciation audio assets
- `analytics.csv`, `daily_stats.csv`, `statistics.csv` — generated statistics
- `sent_tg_messages.json` — record of Telegram messages sent
- `config.json` — configuration (e.g., tokens, settings)

## Requirements
- Python 3.8+ (project uses standard libs + some common packages).
- Recommended packages (some may already be present in the provided `env` virtualenv):
	- `requests`
	- `python-dotenv` (or `dotenv`)
	- `gtts`, `pydub` (if using audio features)
	- `googletrans` (if translation is used)

If you prefer to create a fresh venv on Windows:

```powershell
python -m venv env
env\Scripts\activate
pip install -r requirements.txt  # optional if you create one
```

Or reuse the included virtualenv at `env/` by activating it:

```powershell
env\Scripts\activate
```

## Configuration
Edit `config.json` to set project-specific settings (API tokens, Telegram chat id, etc.). If environment variables are preferred, you can adapt the scripts to read from a `.env` file.

## Usage
Run the main script:

```powershell
python main.py
```

Generate/send a Telegram report:

```powershell
python telegram_report.py
```

Run tests or quick checks:

```powershell
python test.py
```

## Development
- Keep word list data in `words.csv` and audio in `pronunciations/`.
- Analytics are appended to the CSV files; check `sent_tg_messages.json` to see Telegram history.

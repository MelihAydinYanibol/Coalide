# Changelog

All notable changes to **Coalide** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.3] - 2026-09-13

Daily time-budget release: a parent can now cap how long the child spends
answering questions in a day, and every answer's duration is logged so the cap
has something real to measure against.

### Added
- **Daily Coalide time limit (`DAILY_COALIDE_TIME_LIMIT`)** — a per-day budget
  in seconds for time spent answering questions (`0` = off, the default). The
  quiz shows the remaining budget above each question, coloured green, yellow
  under 30% and red under 10%, and stops with *"Günlük süre sınırına
  ulaştınız"* back to the main menu once it is used up. The limit is enforced
  both before a question is asked and while one is on screen: the answer
  timeout becomes the smaller of `INPUT_TIMEOUT` and whatever is left of the
  day's budget, so a single long answer cannot run past the cap — and a timeout
  caused by the daily limit is reported as such instead of as "answer faster".
  The key is described in the admin panel alongside the other config keys.
- **Per-answer durations in `statistics.csv`** — a new `time_spent` column
  records how many seconds each question took. `record_answer()` takes the
  value and `read_log_rows()` exposes it; rows written by older builds (three
  or seven columns) are still read, with `time_spent` left as `None` rather
  than counted as zero.
- **`User.get_total_time_spent_today()` and `User.aprox_time_taken()`** — the
  day's total and a windowed average seconds-per-question, both summed from the
  logged durations. Rows with no recorded duration are skipped rather than
  treated as zero, so a pre-upgrade log cannot understate a total or drag an
  average down. Neither raises: an unreadable log simply reads as `0.0`.

### Fixed
- Several rounds of corrections to `words.json`: mismatched example sentences,
  weak or wrong Turkish glosses, two article errors and a number of Turkish
  spelling mistakes.

## [2.3.2] - 2026-08-08

Parent-dashboard and admin release: every daily widget gets its own time
window, the word list can be narrowed to a single SM-2 maturity bucket,
progress can be reset remotely from the web admin, and the charts work on a
phone.

### Added
- **Per-widget time windows on the dashboard** — Cevap Dağılımı, Aktivite,
  Kazanılan vs Harcanan Kredi, Ekran Süresi, Günlük Cevaplar, Günlük Yeni
  Kelimeler and Yeni Kelime Trendi each carry their own 7g / 14g / 30g / 90g /
  Tümü / Özel picker instead of a fixed range. The stats payload now ships full
  per-day history (`earned_by_date`, `spent_by_date`, `minutes_by_date`,
  `new_by_date`) to make this possible.
- **Maturity filter on the word list** — the per-word table can be narrowed to
  one bucket (Yeni, Öğreniliyor, Genç, Olgun, Usta) or shown in full, both in
  the terminal İstatistikler screen and on the web dashboard.
- **Remote progress reset from the web admin** — a parent can reset a maturity
  bucket back to "not started" from the browser. The reset is queued as a
  revision-tracked job and applied on the child's device at its next menu-open
  sync, so it runs exactly once; `progress.json` is backed up first.

### Fixed
- Dashboard chart tooltips now work on touch: a press reveals the tooltip on
  all four chart types, a horizontal drag scrubs the line chart while a
  vertical drag still scrolls the page. Mouse behaviour is unchanged.

## [2.3.1] - 2026-08-07

### Fixed
- **A question can no longer be re-rolled into a free hint.** Leaving the quiz
  with `exit` and restarting used to hand out the answer: the direction was
  re-rolled on every draw, and when the prompt side had several aliases
  (1321 of 3012 words do) the shown alias was re-picked too. Both are now
  pinned until the question has actually been graded, stored in their own
  `.pending_question.json` so that merely being shown a question doesn't count
  the word as "started" on the statistics screen.
- **Parent config changes now apply on the next menu, as promised.** The sync
  only ran from `MainMenu.on_mount()`, which fires once at launch — and because
  sub-flows suspend the app rather than switching screens, returning from one
  never re-synced. Coalide now pulls again every time the TUI resumes.

### Added
- A dimmed version line at the bottom-center of the main menu, read from
  `version.json` with a compiled-in fallback.

## [2.3.0] - 2026-08-05

The biggest release since the rewrite: Coalide now runs in a browser as well as
in the terminal, the vocabulary database is more than four times larger, and the
terminal app gets a real settings menu.

### Added
- **Web app (`webapp/`)** — a Flask port of the trainer reusing the same
  `words.json` and SM-2 core: per-user login and progress under `webapp/data/`,
  pronunciation through the browser's Web Speech API, the full İstatistikler
  dashboard, a parent admin panel at `/admin` with per-user config overlays, and
  an `import_user.py` importer for bringing a terminal learner across.
- **Settings menu (`settings_menu.py`)** — three tabs: Hakkında (version, user,
  language pair, word count, with local paths masked behind the admin
  password), Ses (a slider bound to the real Windows master volume through the
  Core Audio `IAudioEndpointVolume` interface, raw ctypes/COM, no new
  dependency), and Yönetim (admin panel + a process-local **Sudo** unlock).
- **Config keys `Sound_Effects` and `Minimum_Volume`** — a master gate for all
  playback that a learner cannot switch off, and a volume floor that also
  disables the mute switch and is applied at startup.
- **Redeem TUI (`redeem_menu.py`)** — replaces the old console prompt: live
  pricing, up-front validation of every redeem rule, and an **En Fazla** button
  for the largest amount the balance can buy for that date.
- **Çıkış dialog** — offering Çıkış Yap (log out) or Bilgisayarı Kapat, with an
  X to cancel.
- **Answer log on the dashboard** — a per-day Cevap Günlüğü showing every
  question asked, the accepted answer, what the child typed and how it was
  graded. `statistics.csv` gained four columns (`given`, `expected`, `prompt`,
  `direction`) to make this possible.
- **Genel Başarı over a time window** — the success ring can be scoped to
  Bugün, Dün, Bu hafta, Bu ay or a custom range.

### Changed
- **Vocabulary grew from 695 to 3,012 words**, covering the full Oxford 3000.
  British spellings were normalised to American throughout, so `colour`/`color`
  style duplicates no longer split progress across two entries.
- The parent dashboard was rebuilt for phones: defined grid breakpoints at
  1024px and 640px, a reflowing header, scrollable tab strip, 40px touch
  targets, viewport-clamped tooltips, and charts drawn at their container's
  real pixel width.
- Every chart gained a table view, symbol-carrying legends and tooltips
  (✓ ✗ ∅ ▲ ▼) so a series is never identified by colour alone, and re-stepped
  greens and reds for colour-vision deficiency.

### Fixed
- **Launching with no saved user showed a blank screen and hung.** The username
  prompt ran `input()` from inside the Textual menu's `compose()`, so the
  question was painted into a screen Textual immediately repainted while the
  app sat blocked on stdin — and with mouse tracking on, escape sequences fed
  into that hidden prompt saved usernames like `354916M354914M…`. Reading and
  prompting are now separate, the app refuses to prompt while a TUI owns the
  screen, and whole ANSI sequences are stripped before filtering.
- The İstatistikler → Kelimeler tab was unusable: the word-type chart grew a
  line per type and squeezed the table down to two rows. It now shows the top
  six types and counts the rest, and focuses the table on open.
- A comma in a word no longer corrupts the answer log — `statistics.csv` is
  written and read through the `csv` module on both ends.
- Off-by-one day in the answer log's prev/next buttons (they went through
  `toISOString()`, which converts to UTC first).
- The admin page logo links back to the dashboard, like the dashboard's own.

## [2.2.2] - 2026-07-25

### Added
- `SHUFFLE_NEW_WORDS` config key: introduce new words in random order instead of
  `words.json` order.

## [2.2.1] - 2026-07-25

### Fixed
- New-word shuffling now takes effect when questions are asked.

## [2.2.0] - 2026-07-24

Optional **parent-side companion server** (`serverside/`) that runs on the
parent's own device — dependency-free (Python standard library only) and
entirely opt-in.

### Added
- **Web dashboard** mirroring the in-app İstatistikler screen, with
  self-contained inline-SVG charts (line/area, grouped columns, donut, progress
  ring, distribution) and hover tooltips.
- **Stats API + client reporter** (`stats_reporter.py`) — the app pushes a
  snapshot on every menu open and after quiz/redeem flows, on a background
  thread that fails silently.
- **Daily report** over **Telegram** *and* **ntfy.sh** — either or both, at a
  configurable time (midnight by default), ending with a link to the dashboard.
  Catches up automatically if the machine was asleep at the scheduled minute.
- **Password-gated web admin** to edit `config.json`, `words.json` and the
  server's own `.env` from the browser. The password is hashed in the browser,
  so the plaintext never reaches the server.
- **Config sync** (`config_sync.py`) — because the server runs on a different
  device, edits flow through a revision-numbered sync API: the child pushes its
  config/words on each menu open and pulls back any parent edits.
- New config keys: `STATS_REPORTING_ENABLED`, `STATS_SERVER_URL`,
  `CONFIG_SYNC_ENABLED`.

### Fixed
- Daily-report setup no longer reports itself as "configured" when the `.env`
  still holds the example Telegram token/chat-id, which made it attempt a
  doomed send.

### Notes
- `serverside/` is parent-side infrastructure and never ships in a client
  release — `cli.py -release-ready` wipes it along with `.config_sync.json`.

## [2.1.6] - 2026-07-23

### Fixed
- The menu no longer gets blocked when offline. In 2.1.4/2.1.5 the internet
  check ran at startup, so with `REQUIRE_INTERNET` enabled an offline machine
  exited before the main menu appeared. The check now runs only when the quiz
  starts, leaving the menu, redeem, practice and stats screens usable offline.

## [2.1.4] - 2026-07-21

### Added
- `REQUIRE_INTERNET` config key (default `true`): the credit-earning quiz won't
  start without a connection. Connectivity is verified with a quick TCP check
  to Google's public DNS (`8.8.8.8:53`).

## [2.1.3] - 2026-07-15

### Added
- **Credit window** (`Credit_Window_Start` / `Credit_Window_End`, default
  07:00–22:00): correct answers only earn credits inside the window. Answers
  outside it still count for SM-2 scheduling.

## [2.1.2] - 2026-07-15

### Fixed
- Assorted bug patches.

## [2.1.1] - 2026-07-13

### Added
- **Admin Mode rebuilt as a Textual TUI** (`admin.py`) with three tabs:
  Krediler (view/add/remove balance), Ayarlar (live-edit every `config.json`
  key with switches and typed inputs) and Kelimeler (browse, add, edit and
  delete vocabulary entries, keeping SM-2 progress in sync).

### Changed
- Admin Mode launches as its own subprocess from the main menu, since a nested
  Textual app would fight the menu over the terminal.

### Fixed
- Exiting a question early (via `e`/`q`) no longer skips saving that question's
  SM-2 update and credit award.

## [2.1.0] - 2026-07-13

### Added
- Statistics screen (`stats_menu.py`) — overview tiles, weekly/daily new-word
  charts, per-answer logging to `statistics.csv`, a per-word table, an upcoming
  review forecast and SM-2 health (shipped in 2.0.9).
- Practice mode (`practice.py`) — a hands-off flashcard run through the whole
  word list, pronouncing each word and sentence, exited with any key (shipped
  in 2.0.8).

## [2.0.5] - 2026-07-12

### Added
- **Kiosk mode.** `bypasser.py` installs a low-level Windows keyboard hook that
  swallows Alt+F4 (no admin rights, no third-party packages), and
  `cli.py -create-kiosk-batch` writes a `launch_kiosk.bat` that relaunches
  Coalide in a loop if it ever exits. New config keys `KIOSK_MODE` and
  `BYPASS_SHORTCUTS`.
- `dependency_check.py`: a stdlib-only check that pip-installs anything missing
  from `requirements.txt` before the first third-party import, so a fresh
  machine with base Python works.

## [2.0.1] - 2026-07-08

Quality-of-life patch line (2.0.1 – 2.0.4).

### Fixed
- Redemptions can no longer target dates beyond the current week when
  `Credit_Reset_Weekly` is on, closing a loophole where credits could be
  banked as future screen time to survive the Monday reset.
- Total redeemed screen time for a single date is now capped at 24 hours
  (1440 minutes), since a day has no more minutes than that.

## [2.0.0] - 2026-07-08

First stable release of the rewrite.

### Changed
- Moved the application from the `gogo/` subdirectory to the repository root.
- Removed legacy v1/v2 code now superseded by the re-write.

## [2.0.0-alpha] - 2026-07-07

A ground-up rewrite of Coalide around an object-oriented architecture and a
spaced-repetition learning model.

### Added
- **OOP architecture**: quiz logic restructured around `Word` and session
  objects, replacing the previous procedural flow.
- **SM-2 spaced-repetition algorithm**: word scheduling now uses the SM-2
  algorithm with per-word review intervals.
- **Progress tracking**: per-word `ID` and `last_review_date` attributes, plus
  richer object attributes for tracking learning state.
- **No-Repeat Window**: prevents the same word from reappearing too soon within
  a session.
- **Daily New-Word Cap**: limits how many previously unseen words are introduced
  per day.
- **Balance & credit system**: earn and spend credit/balance based on quiz
  performance.
- **Audio subsystem**: reworked text-to-speech / pronunciation playback.

### Changed
- Consolidated the two parallel versions of the app into a single codebase.

## [1.2] - 2026-06-27

Final release of the original (v1) procedural line.

### Added
- **Configurable PCV2 time multiplier** (`pc_time_multiplier`): scale awarded
  parental-control time (`2` doubles, `0.5` halves).
- Expanded the `words.csv` vocabulary database.

### Fixed
- PCV2 pending exception-time deduplication no longer double-counts pending time.
- Telegram end-of-quiz text now displays correctly when `set_time_for_pc` is
  disabled in the config.
- Various word-list corrections.

### Changed
- Clarified multiplier display formatting and output text; kept the multiplier
  flow backward-compatible.

## [1.2-legacy] - 2026-02-12

Tagged snapshot of the early legacy line.

### Added
- Initial two-level, bidirectional English–Turkish vocabulary quiz.
- ASCII art start and selection menus.
- Text-to-speech pronunciation (gTTS / PyAudio).
- Telegram progress reporting.
- Optional PCV2 parental-control integration.
- Password-protected admin console (`set` / `dset` / `show`) and `-debug` mode.
- Automatic data backups and optional `words.csv` auto-update.

[Unreleased]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.3.3...HEAD
[2.3.3]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.3.2...v2.3.3
[2.3.2]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.3.1...v2.3.2
[2.3.1]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.2.2_0...v2.3.0
[2.2.2]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.2.1...v2.2.2_0
[2.2.1]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.1.6...v2.2.0
[2.1.6]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.1.5...v2.1.6
[2.1.4]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.1.3...v2.1.4
[2.1.3]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.1.2...v2.1.3
[2.1.2]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.0.9...v2.1.0
[2.0.5]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.0.4...v2.0.5
[2.0.1]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.0.0-alpha...v2.0.0
[2.0.0-alpha]: https://github.com/MelihAydinYanibol/Coalide/compare/v1.2...v2.0.0-alpha
[1.2]: https://github.com/MelihAydinYanibol/Coalide/compare/v1.2-legacy...v1.2
[1.2-legacy]: https://github.com/MelihAydinYanibol/Coalide/releases/tag/v1.2-legacy

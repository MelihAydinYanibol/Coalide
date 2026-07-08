# Changelog

All notable changes to **Coalide** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Redemptions can no longer target dates beyond the current week when
  `Credit_Reset_Weekly` is on, closing a loophole where credits could be
  banked as future screen time to survive the Monday reset.
- Total redeemed screen time for a single date is now capped at 24 hours
  (1440 minutes), since a day has no more minutes than that.

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

[Unreleased]: https://github.com/MelihAydinYanibol/Coalide/compare/v2.0.0-alpha...HEAD
[2.0.0-alpha]: https://github.com/MelihAydinYanibol/Coalide/compare/v1.2...v2.0.0-alpha
[1.2]: https://github.com/MelihAydinYanibol/Coalide/compare/v1.2-legacy...v1.2
[1.2-legacy]: https://github.com/MelihAydinYanibol/Coalide/releases/tag/v1.2-legacy

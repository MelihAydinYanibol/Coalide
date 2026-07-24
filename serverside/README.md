# Coalide — Parental Stats Server (`serverside/`)

A small, **zero-dependency** (Python standard library only) server that lets a
parent watch a learner's Coalide progress from a web browser.

The child's Coalide app pushes a snapshot of its statistics to this server
every time the main **menu opens** (and after each quiz/redeem flow). The server
stores the latest snapshot per user and renders it as a web dashboard that shows
the same information as the in-app **İstatistikler** screen.

> ⚠️ This whole folder is **development/server infrastructure** and never ships
> in a Coalide release — `python cli.py -release-ready` deletes `serverside/`
> along with the other local-only artifacts.

## Components

| File | Purpose |
| --- | --- |
| `server.py` | HTTP server: stats API, sync API, admin API + serves the pages |
| `dashboard.html` | The web dashboard (single self-contained page) |
| `admin.html` | The web admin panel (config + words + server settings) |
| `report.py` | Daily Telegram report (summary text + dashboard link) |
| `admin_api.py` | Admin auth + config/words sync backend |
| `.env.example` | Template for Telegram / report configuration |
| `data/` | Created at runtime: per-user stats + synced config/words |

## Running it (on the parent's machine)

```bash
cd serverside
python server.py
```

By default it listens on `0.0.0.0:5055`. Override with environment variables:

```bash
COALIDE_STATS_HOST=127.0.0.1 COALIDE_STATS_PORT=8000 python server.py
```

Then open the dashboard in a browser:

```
http://<parent-server-ip>:5055/
```

## Pointing the child's app at it

In the child's `config.json` (created on first run), set:

```json
"STATS_REPORTING_ENABLED": true,
"STATS_SERVER_URL": "http://192.168.1.50:5055"
```

Reporting is skipped as long as `STATS_SERVER_URL` still contains the shipped
placeholder (`IP-TO-YOUR-PARENT-SERVER`), so nothing is sent until you set a real
address. The push runs on a background thread with a short timeout and fails
silently — it can never slow down or break the learner's app.

## Daily Telegram report

Once a day (at **midnight** by default) the server sends a text summary of every
learner's stats to a Telegram chat, ending with a link back to the dashboard
(`🔗 Daha fazla bilgi: <url>`).

Configure it via environment variables or a `.env` file next to `server.py`
(copy `.env.example` → `.env`). The report turns on automatically once a bot
token and chat id are set:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-your-token
TELEGRAM_CHAT_ID=123456789
COALIDE_REPORT_TIME=00:00          # 24h local time; default midnight
COALIDE_DASHBOARD_URL=http://192.168.1.50:5055/
```

Test it without waiting for midnight:

```bash
python server.py --report-preview   # print the message, don't send
python server.py --send-report      # send it right now via Telegram
```

You can also `GET /api/report/preview` to see the current report text as JSON.
If the machine is asleep at the scheduled minute, the report still goes out at
the first moment it is awake at or after that time on a day it hasn't sent yet.

## Web admin — manage Coalide remotely

Because the server runs on a **different device** than Coalide, it can't touch the
child's files directly. Instead the child's app **syncs** on every menu open: it
pushes its current `config.json`, `words.json`, and a SHA-256 hash of
`ADMIN_PASSWORD`, then pulls back any changes you made in the web admin and applies
them locally (writing the files and reloading, pruning progress for deleted words).

Open the admin from the dashboard's **🛠️ Yönetim** button (or go to `/admin`) and
log in with the Coalide **admin password** (the same `ADMIN_PASSWORD` from the
child's `.env`). The password is hashed **in the browser** — only the hash is sent,
and it is checked against the hash the child synced, so the plaintext password never
reaches the server. It has two sections:

1. **Coalide Yapılandırması** — edit every `config.json` value (toggles for
   booleans, typed inputs for the rest) and add / edit / delete words in
   `words.json`, just like Coalide's built-in admin panel.
2. **Sunucu (.env) Ayarları** — edit *this* server's own `.env` (Telegram/report
   settings). Report changes apply within ~30s; host/port changes need a restart.

Edits are versioned: each save bumps a revision number, and the child applies it the
next time its menu opens. Until a child has synced at least once, the admin shows
"henüz eşitlenmedi" and login is unavailable (fail-closed).

> ⚠️ Traffic is plain HTTP — fine on a trusted home LAN, but don't expose this
> server directly to the internet. Put it behind a VPN / reverse proxy with TLS if
> you need remote access.

## HTTP API

| Method & path | Description |
| --- | --- |
| `GET /` | The web dashboard |
| `GET /api/users` | List users with data and their last-updated times |
| `GET /api/stats?user=<name>` | Latest stored snapshot for a user (defaults to the most recently updated) |
| `POST /api/stats` | Store a snapshot. Body: `{ "username", "client_time", "stats" }` |
| `GET /api/report/preview` | The current daily-report text + whether it is enabled |
| `POST /api/sync` | Child push/pull of config + words + admin hash (by revision) |
| `POST /api/admin/login` | Exchange the password hash for a session token |
| `GET/POST /api/admin/coalide-config` | Read / save the Coalide config (token) |
| `GET/POST /api/admin/words` | Read / add / edit / delete words (token) |
| `GET/POST /api/admin/server-env` | Read / save this server's `.env` (token) |
| `GET /health` | Liveness check |

Admin endpoints require an `X-Admin-Token` header from `/api/admin/login`.

The `stats` payload is exactly what `stats_menu.build_stats()` produces, run
through a JSON serializer in the client's `stats_reporter.py`. Keeping the
statistics logic in one place means the dashboard only ever *renders* data — it
never recomputes it.

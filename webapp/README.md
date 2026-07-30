# Coalide — Web App

A browser-based version of the [Coalide](../README.md) spaced-repetition
vocabulary trainer. It reuses the project's vocabulary database
(`../words.json`) and the SM-2 learning core, and wraps them in a Flask backend
with a responsive single-page quiz UI.

Where the original app runs as a terminal (Textual/CLI) program for one machine,
this version runs as a small web server so the trainer can be opened from any
browser, with **per-user progress** kept separately for each learner.

![Quiz screen](docs/quiz.png)

## What's included

- **Same learning engine** — SM-2 scheduling, quality grading (correctness +
  speed), the daily new-word cap, the no-repeat window, bidirectional questions
  and Turkish-aware answer matching are all ported verbatim from the terminal
  app (`sm2.py`, `objects/word_obj.py`), so learning behaves identically.
- **Per-user progress** — each learner logs in with a username; their SM-2 state
  and credit balance live in `webapp/data/<user>_progress.json` and
  `webapp/data/<user>_data.json`. The shared root `progress.json` is never
  touched.
- **Credits & rewards** — correct answers earn credits inside the configured
  earning window, with the same escalating pricing, weekly reset and 24h/day cap
  as the terminal app. See the note on parental controls below.
- **Pronunciation** — the target word and example sentence are read aloud using
  the browser's built-in Web Speech API, so no TTS keys or server-side audio are
  required. (The terminal app's ElevenLabs/gTTS pipeline is not needed here.)
- **Stats dashboard** — words seen, due now, well-known count and overall
  success rate.
- **Admin dashboard** — a password-protected parent panel at `/admin`,
  connected to the web app's own data: see every learner's progress and
  balance, adjust credits, and edit the shared `config.json` from the browser.

## Admin dashboard

Open <http://localhost:5000/admin> (there's also a link on the login page). It's
gated by the same `ADMIN_PASSWORD` the terminal admin uses — read from the
`ADMIN_PASSWORD` environment variable, else the `ADMIN_PASSWORD=` line in the
project's `../.env`, else the placeholder default `0000`. **Set a real password
before exposing the app beyond localhost.**

![Admin dashboard](docs/admin.png)

From the panel a parent can:

- **Users** — list every web-app learner with balance, words seen, words due,
  well-known count, overall success rate and minutes already redeemed today;
  adjust any learner's credits with one click (−10 / +10 / +100).
- **Ayarlar (Settings)** — edit a whitelisted set of `config.json` keys
  (new-word cap, no-repeat window, credit pricing/window, spam protection,
  language labels, …) with type-aware inputs and toggles. These write the same
  `config.json` the quiz engine reads, so changes take effect on the next
  question — and are shared with the terminal app.

The admin panel is deliberately connected to the web app's **own** per-user data
under `webapp/data/`, so no separate server process is required. (This is
distinct from the terminal project's separate `serverside/` parental server,
which stores pushed snapshots from the terminal client.)

## Running it

```bash
cd webapp
pip install -r requirements.txt
python app.py
```

Then open <http://localhost:5000> and enter a username to start.

### Configuration

The app reads the project's existing `../config.json` (creating nothing new), so
keys like `Daily_New_Word_Cap`, `No_Repeat_Window`, `Source_Language`,
`Target_Language`, `Credit_Window_Start/End`, `BASE_RATE_PER_MINUTE`,
`ESCALATION_PER_HOUR` and `Credit_Reset_Weekly` all apply here too. An optional
`CREDITS_PER_CORRECT` key (default `7`) controls the reward per correct answer.

Environment variables:

| Variable | Purpose | Default |
|---|---|---|
| `COALIDE_SECRET_KEY` | Flask session secret — **set this in production** | dev placeholder |
| `PORT` | Port to listen on | `5000` |
| `COALIDE_DEBUG` | Set to enable Flask debug mode | off |

## How it maps to the terminal app

| Terminal app | Web app |
|---|---|
| `sm2.get_next_question` / `calculate_quality` / `update_sm2` | `engine.get_next_word` / `calculate_quality` / `apply_result` |
| `objects/word_obj.py` (`Word`, progress) | reuses `Word`; progress persisted per-user in `engine.py` |
| `new_master.normalize_answer` | `engine.normalize_answer` |
| `objects/balance_obj.py` (credits/pricing) | `credits.py` |
| `current_user.json` | Flask session cookie |
| ElevenLabs / gTTS audio | browser Web Speech API |

### A note on parental controls (PCV2)

The terminal app redeems credits by calling a [PCV2](https://github.com/cekirge1972/PCV2)
server on the family LAN to grant real screen time. A web deployment generally
can't reach a device on that private network, so this version records
redemptions locally (applying all the same pricing, caps and weekly-reset rules)
without making the PCV2 call. If you deploy this alongside a reachable PCV2
server, wiring `credits.redeem` to `parental_connection.add_exceptional_time`
would restore the real grant.

## Project layout

```
webapp/
├── app.py            # Flask app: pages + JSON API (quiz + admin)
├── engine.py         # per-user SM-2 learning engine (reuses words.json + Word)
├── credits.py        # per-user credit earning / pricing / redemption
├── requirements.txt
├── templates/
│   ├── login.html
│   ├── index.html    # single-page quiz / rewards / stats UI
│   └── admin.html    # parent admin dashboard (users + settings)
├── static/
│   ├── style.css
│   ├── app.js        # quiz front-end logic
│   └── admin.js      # admin dashboard logic
└── data/             # per-user progress + balances (gitignored)
```

## Production note

`python app.py` uses Flask's development server, which is fine for local/family
use. For a real deployment, run it behind a WSGI server, e.g.:

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

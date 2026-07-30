"""
Coalide — Web App.

A Flask front end for the Coalide spaced-repetition vocabulary trainer. It
reuses the project's ``words.json`` vocabulary and the SM-2 learning core
(via ``engine.py``) and adds per-user progress, a browser quiz UI and the
credit/reward loop (``credits.py``).

Run:
    cd webapp
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""

from __future__ import annotations

import os
import secrets

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

import engine
import credits

app = Flask(__name__)
# A stable secret keeps sessions valid across restarts in dev; override in prod.
app.secret_key = os.environ.get("COALIDE_SECRET_KEY", "coalide-dev-secret-change-me")


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def current_user() -> str | None:
    return session.get("username")


def admin_password() -> str:
    """
    The admin password, matching the terminal app: the ADMIN_PASSWORD env var,
    else the value in the project's ../.env, else the placeholder default 0000.
    """
    env = os.environ.get("ADMIN_PASSWORD")
    if env:
        return env
    env_path = os.path.join(engine.PROJECT_ROOT, ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("ADMIN_PASSWORD="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "0000"


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "admin_required"}), 401
        return fn(*args, **kwargs)

    return wrapper


def login_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"error": "not_logged_in"}), 401
        return fn(*args, **kwargs)

    return wrapper


# --------------------------------------------------------------------------- #
# Pages                                                                        #
# --------------------------------------------------------------------------- #

@app.route("/")
def index():
    if not current_user():
        return redirect(url_for("login_page"))
    cfg = engine.get_config()
    return render_template(
        "index.html",
        username=current_user(),
        source_language=cfg.get("Source_Language", "Türkçe"),
        target_language=cfg.get("Target_Language", "İngilizce"),
    )


@app.route("/login", methods=["GET"])
def login_page():
    if current_user():
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/admin", methods=["GET"])
def admin_page():
    return render_template("admin.html", is_admin=bool(session.get("is_admin")))


# --------------------------------------------------------------------------- #
# Auth API                                                                     #
# --------------------------------------------------------------------------- #

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    raw = (data.get("username") or "").strip()
    # Keep only the safe characters, then require at least one survived, so a
    # symbols-only entry is rejected rather than silently becoming "guest".
    cleaned = "".join(c for c in raw if c.isalnum() or c in ("-", "_")).strip()
    if not cleaned:
        return jsonify({"error": "Geçersiz kullanıcı adı."}), 400
    username = engine._safe_username(cleaned)
    session["username"] = username
    session["feed"] = []
    return jsonify({"ok": True, "username": username})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


# --------------------------------------------------------------------------- #
# Quiz API                                                                     #
# --------------------------------------------------------------------------- #

@app.route("/api/next", methods=["GET"])
@login_required
def api_next():
    user = current_user()
    feed = session.get("feed", [])
    word, is_target_wanted = engine.get_next_word(user, feed)
    if word is None:
        return jsonify({"done": True})
    payload = engine.build_question(word, is_target_wanted)
    # Remember which word/direction was served so grading can't be spoofed.
    session["pending"] = {"word_id": word.id, "is_target_wanted": is_target_wanted}
    return jsonify({"done": False, "question": payload})


@app.route("/api/answer", methods=["POST"])
@login_required
def api_answer():
    user = current_user()
    pending = session.get("pending")
    if not pending:
        return jsonify({"error": "no_active_question"}), 400

    data = request.get_json(silent=True) or {}
    answer = data.get("answer", "")
    time_taken = float(data.get("time_taken", 0) or 0)

    words = engine.load_word_list(user)
    word = engine._find_word(words, pending["word_id"])
    if word is None:
        return jsonify({"error": "word_not_found"}), 400

    is_target_wanted = pending["is_target_wanted"]
    result = engine.grade_answer(word, is_target_wanted, answer, time_taken)
    engine.save_word_progress(user, word)

    # Credits for a correct answer (respects the earning window).
    credit_info = {"awarded": 0, "balance": credits.load_user(user)["balance"], "in_window": True}
    if result["is_correct"] is True:
        credit_info = credits.award_credits(user)

    # Update the no-repeat feed.
    feed = session.get("feed", [])
    feed.append(word.id)
    session["feed"] = feed[-50:]
    session.pop("pending", None)

    result["credits"] = credit_info
    return jsonify(result)


# --------------------------------------------------------------------------- #
# Stats & credits API                                                          #
# --------------------------------------------------------------------------- #

@app.route("/api/stats", methods=["GET"])
@login_required
def api_stats():
    user = current_user()
    data = credits.load_user(user)
    credits.check_weekly_reset(data)
    stats = engine.user_stats(user)
    stats["balance"] = data["balance"]
    return jsonify(stats)


@app.route("/api/redeem", methods=["POST"])
@login_required
def api_redeem():
    user = current_user()
    data = request.get_json(silent=True) or {}
    try:
        minutes = int(data.get("minutes", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Geçersiz dakika."}), 400
    target_date = data.get("date") or ""
    result = credits.redeem(user, minutes, target_date)
    status = 200 if result.get("ok") else 400
    return jsonify(result), status


@app.route("/api/quote", methods=["POST"])
@login_required
def api_quote():
    """Return the credit cost for a prospective redemption without committing it."""
    user = current_user()
    data = request.get_json(silent=True) or {}
    try:
        minutes = int(data.get("minutes", 0))
    except (TypeError, ValueError):
        return jsonify({"cost": None})
    target_date = data.get("date") or ""
    if minutes <= 0 or not target_date:
        return jsonify({"cost": None})
    udata = credits.load_user(user)
    return jsonify({"cost": credits.cost_for_minutes(udata, minutes, target_date), "balance": udata["balance"]})


# --------------------------------------------------------------------------- #
# Admin API (parent-facing dashboard)                                          #
# --------------------------------------------------------------------------- #

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json(silent=True) or {}
    password = str(data.get("password", ""))
    if password and password == admin_password():
        session["is_admin"] = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Hatalı şifre."}), 401


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    session.pop("is_admin", None)
    return jsonify({"ok": True})


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def api_admin_users():
    users = []
    total_words = 0
    for name in engine.list_usernames():
        stats = engine.user_stats(name)
        total_words = stats["total_words"]
        data = credits.load_user(name)
        credits.check_weekly_reset(data)
        redeemed_today = data["redeemed_minutes_by_date"].get(_today_iso(), 0)
        users.append({
            "username": name,
            "balance": data["balance"],
            "words_seen": stats["words_seen"],
            "due_now": stats["due_now"],
            "mastered": stats["mastered"],
            "overall_rate": stats["overall_rate"],
            "redeemed_today": redeemed_today,
        })
    return jsonify({"users": users, "total_words": total_words})


@app.route("/api/admin/credits", methods=["POST"])
@admin_required
def api_admin_credits():
    data = request.get_json(silent=True) or {}
    username = engine._safe_username(str(data.get("username", "")))
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Geçersiz miktar."}), 400
    if username not in engine.list_usernames():
        return jsonify({"ok": False, "error": "Kullanıcı bulunamadı."}), 404
    new_balance = credits.adjust_balance(username, delta)
    return jsonify({"ok": True, "username": username, "balance": new_balance})


@app.route("/api/admin/config", methods=["GET"])
@admin_required
def api_admin_get_config():
    cfg = engine.get_config()
    fields = []
    for key, spec in engine.EDITABLE_CONFIG_KEYS.items():
        fields.append({
            "key": key,
            "type": spec["type"],
            "desc": spec["desc"],
            "value": cfg.get(key),
        })
    return jsonify({"fields": fields})


@app.route("/api/admin/config", methods=["POST"])
@admin_required
def api_admin_save_config():
    data = request.get_json(silent=True) or {}
    updates = data.get("updates") or {}
    try:
        engine.save_config(updates)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True})


def _today_iso() -> str:
    from datetime import date
    return date.today().isoformat()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("COALIDE_DEBUG")))

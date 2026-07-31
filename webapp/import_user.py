"""
Import a terminal-app user's data files into the web app.

The terminal app and the web app use the same per-word / per-user JSON schemas,
so bringing a learner across is mostly a rename — with one catch this script
handles for you: the credits file carries a ``"username"`` field that must match
the target username, or the app would later save to the wrong file.

Usage
-----
    python import_user.py <username> <source_folder> [--config] [--force]

Example (Windows)
    python import_user.py mert D:\\pack
    python import_user.py mert D:\\pack --config      # also import per-user config

What it does, looking inside <source_folder>:

    progress.json           ->  webapp/data/<username>_progress.json
    <any>_data.json / data.json ->  webapp/data/<username>_data.json  (username field fixed)
    statistics.csv          ->  webapp/data/<username>_stats.csv  (per-answer log)
    config.json  (only with --config) -> webapp/data/<username>_config.json
                                          pruned to just the keys that differ
                                          from the shared root config.json

    version.json, words.json  ->  skipped (the web app doesn't use them)

Existing destination files are left alone unless you pass --force.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import engine  # sits next to this file; gives DATA_DIR, config helpers, _safe_username


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _find_data_file(src: str) -> str | None:
    """A *_data.json file (any username), or data.json, in the source folder."""
    candidates = sorted(glob.glob(os.path.join(src, "*_data.json")))
    if candidates:
        return candidates[0]
    plain = os.path.join(src, "data.json")
    return plain if os.path.exists(plain) else None


def import_user(username: str, src: str, with_config: bool = False, force: bool = False) -> None:
    username = engine._safe_username(username)
    if not username:
        sys.exit("error: invalid username")
    if not os.path.isdir(src):
        sys.exit(f"error: source folder not found: {src}")

    os.makedirs(engine.DATA_DIR, exist_ok=True)
    did, skipped = [], []

    def dest(name):
        return os.path.join(engine.DATA_DIR, f"{username}_{name}.json")

    def guard(path):
        if os.path.exists(path) and not force:
            skipped.append(f"{os.path.basename(path)} already exists (use --force to overwrite)")
            return False
        return True

    # 1) progress.json -> <username>_progress.json  (accept an already-prefixed name too)
    progress_src = next((os.path.join(src, n) for n in
                         (f"{username}_progress.json", "progress.json")
                         if os.path.exists(os.path.join(src, n))), None)
    if progress_src:
        try:
            data = _load_json(progress_src)
            if not isinstance(data, dict):
                raise ValueError("progress file is not a JSON object")
            if guard(dest("progress")):
                _write_json(dest("progress"), data)
                did.append(f"progress ({len(data)} words) -> {os.path.basename(dest('progress'))}")
        except (OSError, ValueError, json.JSONDecodeError) as e:
            skipped.append(f"progress: {e}")
    else:
        skipped.append("no progress.json found")

    # 2) *_data.json -> <username>_data.json  (fix the internal username field)
    data_src = _find_data_file(src)
    if data_src:
        try:
            data = _load_json(data_src)
            if not isinstance(data, dict):
                raise ValueError("data file is not a JSON object")
            original = data.get("username")
            data["username"] = username  # keep the filename and the field in sync
            data.setdefault("balance", 0)
            data.setdefault("redeemed_minutes_by_date", {})
            data.setdefault("last_reset_date", None)
            if guard(dest("data")):
                _write_json(dest("data"), data)
                note = f" (username '{original}' -> '{username}')" if original and original != username else ""
                did.append(f"credits (balance {data.get('balance', 0)}){note} -> {os.path.basename(dest('data'))}")
        except (OSError, ValueError, json.JSONDecodeError) as e:
            skipped.append(f"credits: {e}")
    else:
        skipped.append("no *_data.json found")

    # 3) statistics.csv -> <username>_stats.csv  (per-answer log; also accept a prefixed name)
    import shutil
    stats_src = next((os.path.join(src, n) for n in
                      (f"{username}_stats.csv", "statistics.csv")
                      if os.path.exists(os.path.join(src, n))), None)
    if stats_src:
        dst = os.path.join(engine.DATA_DIR, f"{username}_stats.csv")
        if guard(dst):
            try:
                with open(stats_src, "r", encoding="utf-8") as f:
                    rows = sum(1 for _ in f)
                shutil.copyfile(stats_src, dst)
                did.append(f"answer log ({max(0, rows - 1)} answers) -> {os.path.basename(dst)}")
            except OSError as e:
                skipped.append(f"stats log: {e}")
    else:
        skipped.append("no statistics.csv found")

    # 4) config.json -> <username>_config.json  (opt-in, pruned to real overrides)
    config_src = os.path.join(src, "config.json")
    if with_config and os.path.exists(config_src):
        try:
            incoming = _load_json(config_src)
            if not isinstance(incoming, dict):
                raise ValueError("config file is not a JSON object")
            root = dict(engine.CONFIG_DEFAULTS)
            root.update(engine._read_json_dict(engine._root_config_path()))
            # Keep only editable keys whose value differs from the root config,
            # so the overlay stays minimal and unchanged keys track the root.
            overlay = {k: v for k, v in incoming.items()
                       if k in engine.EDITABLE_CONFIG_KEYS and root.get(k) != v}
            if not overlay:
                skipped.append("config: nothing differs from root config.json (no overlay needed)")
            elif guard(dest("config")):
                _write_json(dest("config"), overlay)
                did.append(f"config overlay ({', '.join(overlay)}) -> {os.path.basename(dest('config'))}")
        except (OSError, ValueError, json.JSONDecodeError) as e:
            skipped.append(f"config: {e}")
    elif os.path.exists(config_src):
        skipped.append("config.json present but not imported (pass --config to import as per-user overlay)")

    # Report
    print(f"\nImporting '{username}' from {src}\n" + "-" * 48)
    for line in did:
        print("  ✓ " + line)
    for line in skipped:
        print("  – " + line)
    print("-" * 48)
    print(f"Done. Files written to: {engine.DATA_DIR}")
    if did:
        print(f"Log in to the web app as '{username}' to see the imported data.")


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    import_user(args[0], args[1], with_config="--config" in flags, force="--force" in flags)


if __name__ == "__main__":
    main(sys.argv[1:])

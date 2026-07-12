"""
update.py
This is the module that will be run to start the application, but before that it will check github repository for new updates and if there are any, it will update the application automatically.
"""

import sys
import os
import shutil
import zipfile
import io
import json
import fnmatch
from datetime import datetime

# Make sure every third-party package in requirements.txt is installed before
# we import any of them (requests, colorama via utils, etc.). Uses only the
# standard library, so it works on a fresh machine with just base Python.
from dependency_check import ensure_dependencies
ensure_dependencies()

import requests
from utils import lg, get_config

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

REPO_OWNER = "MelihAydinYanibol"
REPO_NAME = "Coalide"
INCLUDE_PRERELEASES = get_config().get("Update_Prereleases", False)  # Read from config.json

VERSION_FILE = "version.json"

# Files/folders that must never be touched by an update, even if the
# release zip happens to contain something with the same name (e.g. a
# template .env or example words.json committed to the repo). Supports
# glob patterns, since per-user files like "username_data.json" vary by name.
PROTECTED_PATTERNS = [
    ".env",
    "words.json",
    "progress.json",
    "*_data.json",      # per-user balance/credits files
    "current_user.json",  # which user is currently logged in
    "pronunciations",   # cached generated audio -- runtime data, not source
    VERSION_FILE,        # our own locally-tracked version record
]


def _is_protected(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in PROTECTED_PATTERNS)


def get_installed_version() -> str | None:
    """
    Returns the version actually installed locally, read from VERSION_FILE.
    Returns None if this is a fresh install that has never completed an
    update yet -- no hardcoded fallback, since that would need manually
    bumping in sync with every release and could silently drift out of
    date. check_for_updates() treats None as "sync to whatever's
    currently published" and records the real tag from there.
    """
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("version")
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_installed_version(version: str):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"version": version, "updated_at": datetime.now().isoformat()}, f, indent=4)


def _get_latest_release():
    """
    Returns the latest release dict. GitHub's /releases/latest endpoint
    explicitly excludes prereleases and drafts ("the most recent
    non-prerelease, non-draft release"), so if INCLUDE_PRERELEASES is True
    we have to fetch the full /releases list instead and take the first
    non-draft entry ourselves -- the list is already sorted newest-first.
    """
    if not INCLUDE_PRERELEASES:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases"
    response = requests.get(url)
    response.raise_for_status()
    releases = response.json()
    for release in releases:
        if not release.get("draft", False):
            return release
    raise RuntimeError("No published releases found (excluding drafts).")


def _merge_extracted_update(temp_dir="update_temp", target_dir="."):
    """
    GitHub's zipball_url always wraps the release contents in a single
    extra top-level folder named like 'owner-repo-commitsha'. This
    descends into that folder before merging files into target_dir,
    so the update actually lands in the right place instead of sitting
    beside the real files as an unused extra folder.

    Anything matching PROTECTED_PATTERNS is left completely alone --
    local data, configs, and .env survive the update untouched, even if
    the release zip contains a same-named file.
    """
    top_level = os.listdir(temp_dir)
    if not top_level:
        raise RuntimeError("Downloaded update archive was empty.")

    extracted_root = os.path.join(temp_dir, top_level[0])

    for item in os.listdir(extracted_root):
        if _is_protected(item):
            continue  # never touch local data/config, regardless of what the release ships

        s = os.path.join(extracted_root, item)
        d = os.path.join(target_dir, item)

        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)  # handles non-empty directories, unlike os.rmdir
            shutil.move(s, d)
        else:
            if os.path.exists(d):
                os.remove(d)
            shutil.move(s, d)


def update_application(download_url, new_version=None):
    """
    Downloads the latest version of the application from the given URL
    and replaces the current application files with the new ones.
    """
    try:
        response = requests.get(download_url)
        response.raise_for_status()  # Raise an error for bad responses

        # Extract the downloaded zip file
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            zip_ref.extractall("update_temp")

        _merge_extracted_update("update_temp", ".")

        shutil.rmtree("update_temp", ignore_errors=True)

        if new_version:
            _save_installed_version(new_version)

        print("Application updated successfully to the latest version.")
    except Exception as e:
        print(f"Failed to update application: {e}")


def _find_git_root(start_path) -> bool:
    """
    Walk upward from start_path looking for a .git folder, the same way
    git itself locates the repo root. Needed because update.py/new_master.py
    live in a subfolder (e.g. "gogo") while .git sits in the parent repo
    root -- checking only the current directory would miss it.
    """
    current = os.path.abspath(start_path)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return True
        parent = os.path.dirname(current)
        if parent == current:  # reached filesystem root without finding it
            return False
        current = parent


def _is_development_checkout() -> bool:
    """
    True if this looks like a developer's local git clone rather than an
    end-user's downloaded release. GitHub's zipball downloads never
    include a .git folder, so its presence (anywhere up the folder tree)
    reliably means this isn't a packaged install -- self-updating here
    would overwrite uncommitted local changes with whatever's currently
    published on GitHub.

    Also true if launched with -dev, as a manual override for cases
    where a .git folder isn't present (e.g. testing a plain downloaded
    copy without wanting auto-update to kick in).
    """
    import sys
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if _find_git_root(script_dir):
        return True
    if len(sys.argv) > 1 and sys.argv[1] == "-dev":
        return True
    return False


def check_for_updates():
    """
    Checks for updates in the GitHub repository (including prereleases,
    if INCLUDE_PRERELEASES is True) and updates the application if a
    newer version than what's actually installed locally is found.
    Skips entirely on a development checkout -- see _is_development_checkout().
    """
    if _is_development_checkout():
        print("Development checkout detected -- skipping auto-update.")
        return

    installed_version = get_installed_version()  # None on a fresh install

    try:
        latest_release = _get_latest_release()
        latest_version = latest_release["tag_name"]
        download_url = latest_release["zipball_url"]

        if installed_version is None:
            print(f"First run detected -- installing latest release {latest_version}...")
            update_application(download_url, new_version=latest_version)
        elif latest_version != installed_version:
            print(f"New version available: {latest_version}. Updating from {installed_version}...")
            update_application(download_url, new_version=latest_version)
        else:
            print("You are using the latest version.")
    except Exception as e:
        print(f"Failed to check for updates: {e}")


if __name__ == "__main__":
    try:
        from bypasser import block_alt_f4
        block_alt_f4()  # kiosk: stop kids closing the window with Alt+F4
        check_for_updates()
        from new_master import starter
        from menu import main
        starter(get_ready=True)
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        os._exit(1)
"""
dependency_check.py
Verifies that every third-party package listed in requirements.txt is
installed, and pip-installs any that are missing before the rest of the
application tries to import them.

This module MUST stay standard-library only. It runs before any of the
project's third-party imports, so on a fresh machine (base Python, nothing
installed yet) it still has to work.
"""

import os
import sys
import subprocess
import importlib.metadata as importlib_metadata

REQUIREMENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")

# Characters that begin a version specifier in a requirements line, e.g.
# "numpy==2.5.1" -> "numpy". We only need the distribution name to ask
# importlib.metadata whether it's installed.
_SPECIFIER_CHARS = "=<>!~ "


def _parse_requirement_names(path):
    """
    Reads requirements.txt and yields (raw_line, distribution_name) for each
    real requirement, skipping blank lines and comments. Distribution names
    are matched against installed packages, so there's no need to know the
    import name (e.g. "Pillow" installs but is imported as "PIL").
    """
    requirements = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip inline comments and environment markers/extras -- we only
            # want the bare distribution name for the presence check.
            name = line.split(";")[0].strip()
            for i, ch in enumerate(name):
                if ch in _SPECIFIER_CHARS:
                    name = name[:i]
                    break
            name = name.split("[")[0].strip()  # drop extras like pkg[foo]
            if name:
                requirements.append((line, name))
    return requirements


def _is_installed(dist_name):
    """True if a distribution with this name is installed (case-insensitive)."""
    try:
        importlib_metadata.version(dist_name)
        return True
    except importlib_metadata.PackageNotFoundError:
        return False


def ensure_dependencies():
    """
    Checks requirements.txt against installed packages and pip-installs any
    that are missing. Returns True if everything is (now) satisfied, False if
    the check couldn't run or the install failed.
    """
    if not os.path.exists(REQUIREMENTS_FILE):
        print(f"Warning: {REQUIREMENTS_FILE} not found -- skipping dependency check.")
        return False

    requirements = _parse_requirement_names(REQUIREMENTS_FILE)
    missing = [line for line, name in requirements if not _is_installed(name)]

    if not missing:
        return True

    print("Missing dependencies detected:")
    for line in missing:
        print(f"  - {line}")
    print("Installing missing dependencies with pip...")

    # Install the exact pinned lines so versions match requirements.txt.
    # sys.executable ensures we install into the same interpreter/venv
    # that's actually running the app.
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", *missing],
        capture_output=True, text=True,
    )
    print(result.stdout, end="")
    print(result.stderr, end="")

    if result.returncode != 0:
        # Packages installed via the Microsoft Store put user-site packages
        # under a deeply nested per-user sandbox path (AppData\Local\Packages\...).
        # Combined with a package that has deeply nested submodules, the full
        # path can exceed Windows' 260-char MAX_PATH, and pip aborts partway
        # through -- looking like a completed install (files were written)
        # right up until it fails, and repeating identically on every launch
        # since nothing was actually installed.
        if "No such file or directory" in result.stderr and "Long Path" in result.stderr:
            print(
                "\nThis install failed because of Windows' 260-character path limit, "
                "not because pip or the package is broken -- it will fail the same way "
                "on every launch until this is fixed. Either:\n"
                "  1. Enable Windows Long Path support (requires admin): "
                "https://pip.pypa.io/warnings/enable-long-paths\n"
                "  2. Or install Python from python.org instead of the Microsoft Store -- "
                "the Store version sandboxes packages under an unusually long path."
            )
        else:
            print(f"Please run: {sys.executable} -m pip install -r requirements.txt")
        return False

    # Re-check so an install that silently produced nothing still surfaces.
    still_missing = [line for line, name in requirements if not _is_installed(name)]
    if still_missing:
        print("Some dependencies are still missing after install:")
        for line in still_missing:
            print(f"  - {line}")
        return False

    print("All dependencies installed successfully.")
    return True


if __name__ == "__main__":
    ok = ensure_dependencies()
    sys.exit(0 if ok else 1)

"""
kiosk_lock.py
Disables the Alt+F4 / close-window action for the console Coalide runs in.

Kids use a dedicated Windows account that boots straight into Coalide
fullscreen. Instead of a global keyboard hook (which needs admin rights and
would disable Alt+F4 for every app on the machine), we simply remove the
SC_CLOSE command from *this* console window's system menu. That makes the
window ignore Alt+F4 and greys out the X button -- scoped to this one window,
no admin, no keyboard hook.

Caveat: this works on the classic console host (conhost.exe), which is what a
fullscreen kiosk launched via a .bat / `python coalide.py` normally uses. It
does not affect Windows Terminal (wt.exe), which owns its own window -- if the
kid's account ends up launching in Windows Terminal, we'd need the keyboard-hook
approach instead.
"""
import ctypes
from ctypes import wintypes


def disable_alt_f4() -> bool:
    """
    Remove the Close command from the console window so Alt+F4 and the X button
    stop closing it. Returns True on success, False if it couldn't be applied
    (not Windows, or no console window handle -- e.g. launched with pythonw).
    Safe to call unconditionally; it no-ops instead of raising.
    """
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    except (AttributeError, OSError):
        return False  # not Windows

    # Set restype/argtypes so 64-bit HWND/HMENU handles aren't truncated to
    # 32-bit ints (the ctypes default), which would corrupt the handle.
    kernel32.GetConsoleWindow.restype = wintypes.HWND
    user32.GetSystemMenu.restype = wintypes.HMENU
    user32.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
    user32.DeleteMenu.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user32.DrawMenuBar.argtypes = [wintypes.HWND]

    SC_CLOSE = 0xF060
    MF_BYCOMMAND = 0x0000

    hwnd = kernel32.GetConsoleWindow()
    if not hwnd:
        return False

    hmenu = user32.GetSystemMenu(hwnd, False)
    if not hmenu:
        return False

    user32.DeleteMenu(hmenu, SC_CLOSE, MF_BYCOMMAND)
    user32.DrawMenuBar(hwnd)  # refresh so the greyed-out X shows immediately
    return True

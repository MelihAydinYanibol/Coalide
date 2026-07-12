"""
kiosk_lock.py
Blocks Alt+F4 so kids can't close Coalide.

The dedicated kids account launches Coalide in Windows Terminal (wt.exe).
Windows Terminal owns its own window, so the console-system-menu trick doesn't
apply, and Alt+F4 is a system window command Terminal won't let us unbind from
its settings. Instead we install a low-level keyboard hook (WH_KEYBOARD_LL)
that swallows the Alt+F4 keystroke before any window sees it.

Notable properties:
  * No admin rights required -- low-level keyboard hooks install unelevated.
  * No third-party packages -- pure ctypes.
  * Only Alt+F4 is suppressed; every other keystroke passes through untouched.
  * The hook runs on a daemon thread with its own message loop and dies with
    the process, so it is active exactly as long as Coalide is running.

Note: the hook is global while running (it sees all keystrokes and drops
Alt+F4 system-wide). That is fine here because this is a dedicated kiosk
account that only ever runs Coalide.
"""
import ctypes
import threading
from ctypes import wintypes

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104  # key events that arrive while Alt is held
VK_F4 = 0x73
LLKHF_ALTDOWN = 0x20    # KBDLLHOOKSTRUCT.flags bit: Alt was down

# LowLevelKeyboardProc: LRESULT CALLBACK(int nCode, WPARAM wParam, LPARAM lParam)
_HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]


# Module-level refs so the callback and hook handle are never garbage-collected
# out from under the running message loop.
_state = {}


def _run_hook():
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    user32.SetWindowsHookExW.restype = wintypes.HHOOK
    user32.SetWindowsHookExW.argtypes = [
        ctypes.c_int, _HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD
    ]
    user32.CallNextHookEx.restype = ctypes.c_long
    user32.CallNextHookEx.argtypes = [
        wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    ]

    def _proc(nCode, wParam, lParam):
        if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if kb.vkCode == VK_F4 and (kb.flags & LLKHF_ALTDOWN):
                return 1  # swallow Alt+F4; do not pass it to any window
        return user32.CallNextHookEx(None, nCode, wParam, lParam)

    callback = _HOOKPROC(_proc)
    hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, callback, None, 0)
    if not hook:
        return

    _state["callback"] = callback  # keep alive for the life of the process
    _state["hook"] = hook

    # A low-level hook only fires while this thread pumps messages.
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


def block_alt_f4() -> bool:
    """
    Start blocking Alt+F4 in the background. Returns True if the hook thread was
    started (Windows), False on non-Windows. Safe to call once at startup; the
    daemon thread stops automatically when the process exits.
    """
    if not hasattr(ctypes, "WinDLL"):
        return False  # not Windows
    threading.Thread(target=_run_hook, daemon=True, name="alt-f4-block").start()
    return True

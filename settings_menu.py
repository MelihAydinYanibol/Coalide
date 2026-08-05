"""
Coalide — Ayarlar Menüsü (TUI)

A Textual TUI with three tabs:
  - 🏠 Hakkında: version, developer info, runtime details and support links.
                 Paths, file names and config keys are masked (••••) with a 👁
                 button that asks for the admin password to reveal them.
  - 🔊 Ses:      a slider bound to the *Windows* master volume and a system
                 mute switch. Coalide's own sounds (pronunciations) are shown
                 read-only: switching them off is an admin-only setting
                 (config.json -> Sound_Effects, honoured by audio_engine), so
                 a learner cannot silence the lesson from here. The slider
                 also refuses to go below config.json -> Minimum_Volume
                 (default 25%), and while that floor is set the mute switch is
                 disabled too — otherwise one click would undo it.
  - 🛠 Yönetim:  a button that opens the admin panel (admin.py), plus a Sudo
                 button that asks for the admin password and unlocks the locked
                 audio controls for this window only (the admin panel has no
                 volume slider, so a parent needs a way to get past their own
                 floor). Sudo is process-local: going back to the main menu
                 closes the settings app and with it sudo.

The volume slider talks to the Windows Core Audio API (IAudioEndpointVolume)
through raw ctypes/COM — no extra dependency — so moving it changes the real
system volume, not just this app's playback. On non-Windows machines, or if
COM is unavailable, the audio controls are disabled and say so.

Run standalone:  python settings_menu.py
From the menu:   the "Ayarlar" button launches it as a subprocess (it is its
                 own Textual app, so it must not run nested inside menu.py's).
"""

import json
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
WORDS_FILE = os.path.join(BASE_DIR, "words.json")
VERSION_FILE = os.path.join(BASE_DIR, "version.json")
ADMIN_SCRIPT = os.path.join(BASE_DIR, "admin.py")

# Palette — matches menu.py / stats_menu.py / admin.py
BG = "#0f0f1a"
PANEL_BG = "#16162a"
PURPLE = "#7c5cff"
GREEN = "#42d6a4"
YELLOW = "#f5c542"
RED = "#ff6b81"
MUTED = "#9a9ac0"

# Stand-in for values a learner should not see (paths, file names, config
# keys). The 👁 button next to them asks for the admin password to unmask.
MASK = "••••••••"

FALLBACK_VERSION = "v2.0.0-alpha"
DEVELOPER = "Melih Aydın Yanıbol"
LICENSE = "GNU GPL v3.0"
PCV2_URL = "https://github.com/cekirge1972/PCV2"


# --------------------------------------------------------------------------
# Windows master volume (Core Audio / IAudioEndpointVolume via raw ctypes COM)
# --------------------------------------------------------------------------

_IS_WINDOWS = os.name == "nt"

_CLSID_MMDeviceEnumerator = "{BCDE0395-E52F-467C-8E3D-C4579291692E}"
_IID_IMMDeviceEnumerator = "{A95664D2-9614-4F35-A746-DE8DB63617E6}"
_IID_IAudioEndpointVolume = "{5CDF2C82-841E-4546-9722-0CF74078229A}"

_CLSCTX_ALL = 23
_E_RENDER = 0        # EDataFlow.eRender — playback devices
_E_MULTIMEDIA = 1    # ERole.eMultimedia — the "default device" apps play to

# Method slots in each interface's vtable (IUnknown occupies 0-2).
_IMMDeviceEnumerator_GetDefaultAudioEndpoint = 4
_IMMDevice_Activate = 3
_IAudioEndpointVolume_SetMasterVolumeLevelScalar = 7
_IAudioEndpointVolume_GetMasterVolumeLevelScalar = 9
_IAudioEndpointVolume_SetMute = 14
_IAudioEndpointVolume_GetMute = 15

if _IS_WINDOWS:
    import ctypes
    from ctypes import POINTER, byref, c_float, c_int, c_void_p, c_wchar_p

    class _GUID(ctypes.Structure):
        _fields_ = [("Data1", ctypes.c_uint32),
                    ("Data2", ctypes.c_uint16),
                    ("Data3", ctypes.c_uint16),
                    ("Data4", ctypes.c_byte * 8)]

    def _guid(text: str) -> "_GUID":
        guid = _GUID()
        if ctypes.windll.ole32.CLSIDFromString(c_wchar_p(text), byref(guid)) != 0:
            raise OSError(f"Geçersiz GUID: {text}")
        return guid

    def _vcall(interface, slot: int, *args, types=()):
        """Call method #slot of a COM interface pointer through its vtable.

        ctypes turns a failing HRESULT into an OSError, which the callers below
        catch — nothing here is allowed to take the whole settings menu down."""
        vtable = ctypes.cast(interface, POINTER(POINTER(c_void_p)))[0]
        prototype = ctypes.WINFUNCTYPE(ctypes.HRESULT, c_void_p, *types)
        return prototype(vtable[slot])(interface, *args)

    def _release(interface) -> None:
        if not interface:
            return
        try:
            vtable = ctypes.cast(interface, POINTER(POINTER(c_void_p)))[0]
            ctypes.WINFUNCTYPE(ctypes.c_ulong, c_void_p)(vtable[2])(interface)
        except Exception:
            pass

    def _create_endpoint():
        """Return a fresh IAudioEndpointVolume* for the default output device."""
        ole32 = ctypes.windll.ole32
        ole32.CoInitialize(None)  # S_FALSE if this thread already did it — fine
        enumerator = c_void_p()
        device = c_void_p()
        endpoint = c_void_p()
        try:
            if ole32.CoCreateInstance(byref(_guid(_CLSID_MMDeviceEnumerator)), None,
                                      _CLSCTX_ALL, byref(_guid(_IID_IMMDeviceEnumerator)),
                                      byref(enumerator)) != 0:
                raise OSError("MMDeviceEnumerator oluşturulamadı.")
            _vcall(enumerator, _IMMDeviceEnumerator_GetDefaultAudioEndpoint,
                   _E_RENDER, _E_MULTIMEDIA, byref(device),
                   types=(c_int, c_int, POINTER(c_void_p)))
            _vcall(device, _IMMDevice_Activate,
                   byref(_guid(_IID_IAudioEndpointVolume)), _CLSCTX_ALL, None,
                   byref(endpoint),
                   types=(POINTER(_GUID), ctypes.c_uint32, c_void_p, POINTER(c_void_p)))
            return endpoint
        finally:
            # The enumerator and the device are only needed to reach the
            # endpoint; the endpoint itself is what we keep alive and cache.
            _release(device)
            _release(enumerator)


# The endpoint is cached because the slider hits it on every step while
# dragging, and building one costs a few COM round-trips.
_endpoint_cache = None


def _drop_endpoint() -> None:
    global _endpoint_cache
    if _IS_WINDOWS and _endpoint_cache is not None:
        _release(_endpoint_cache)
        _endpoint_cache = None


def _with_endpoint(action, default=None):
    """Run `action(endpoint)`; on failure drop the cached endpoint and retry
    once (the default output device may just have changed), then give up and
    return `default`."""
    global _endpoint_cache
    if not _IS_WINDOWS:
        return default
    for attempt in (1, 2):
        try:
            if _endpoint_cache is None:
                _endpoint_cache = _create_endpoint()
            return action(_endpoint_cache)
        except Exception:
            _drop_endpoint()
            if attempt == 2:
                return default
    return default


def system_volume_available() -> bool:
    """True if the Windows master volume can actually be read right now."""
    return get_system_volume() is not None


def get_system_volume():
    """Master volume as 0-100, or None if it cannot be read."""
    def read(endpoint):
        level = c_float()
        _vcall(endpoint, _IAudioEndpointVolume_GetMasterVolumeLevelScalar,
               byref(level), types=(POINTER(c_float),))
        return int(round(level.value * 100))
    return _with_endpoint(read)


def set_system_volume(percent: int) -> bool:
    """Set the master volume (0-100). Returns True on success."""
    scalar = max(0.0, min(1.0, percent / 100))

    def write(endpoint):
        _vcall(endpoint, _IAudioEndpointVolume_SetMasterVolumeLevelScalar,
               c_float(scalar), None, types=(c_float, POINTER(_GUID)))
        return True
    return bool(_with_endpoint(write, default=False))


def get_system_mute():
    """True/False, or None if the mute state cannot be read."""
    def read(endpoint):
        muted = c_int()
        _vcall(endpoint, _IAudioEndpointVolume_GetMute, byref(muted),
               types=(POINTER(c_int),))
        return bool(muted.value)
    return _with_endpoint(read)


def set_system_mute(muted: bool) -> bool:
    def write(endpoint):
        _vcall(endpoint, _IAudioEndpointVolume_SetMute, c_int(1 if muted else 0),
               None, types=(c_int, POINTER(_GUID)))
        return True
    return bool(_with_endpoint(write, default=False))


def enforce_minimum_volume(config=None):
    """Pull the system volume up to config.json -> Minimum_Volume if it starts
    out below it, and unmute (a muted machine is at zero however high the
    slider reads).

    Called when Coalide starts and when the settings menu opens, so lowering
    the volume outside the app before launching does not get around the floor.
    Returns the floor when something was changed, otherwise None. Never raises:
    a locked-down volume is not worth failing startup over."""
    if not _IS_WINDOWS:
        return None
    try:
        if config is None:
            from utils import get_config
            config = get_config()
        floor = max(0, min(100, int(config.get("Minimum_Volume", 0))))
    except Exception:
        return None
    if not floor:
        return None

    changed = False
    try:
        current = get_system_volume()
        if current is not None and current < floor and set_system_volume(floor):
            changed = True
        if get_system_mute() and set_system_mute(False):
            changed = True
    except Exception:
        return None
    return floor if changed else None


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _shorten(text: str, limit: int = 58) -> str:
    """Keep an info-panel value on one line (usernames and paths can be long)."""
    text = str(text)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def app_version() -> str:
    """Installed version from version.json, or the fallback."""
    data = _load_json(VERSION_FILE, {})
    if isinstance(data, dict) and data.get("version"):
        return str(data["version"])
    return FALLBACK_VERSION


# --------------------------------------------------------------------------
# Textual UI
# --------------------------------------------------------------------------

from rich.markup import escape
from rich.text import Text
from textual import events, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (Button, Footer, Header, Input, Static, Switch,
                             TabbedContent, TabPane)


class VolumeSlider(Widget, can_focus=True):
    """A 0-100 slider driven by the arrow keys, a click, a drag or the wheel.

    Textual has no slider widget, so this draws its own bar and reports every
    change with a `VolumeSlider.Changed` message.

    `minimum` is a floor the *user* cannot go below (config.json ->
    Minimum_Volume). It never clamps `sync_value()`: if the volume is already
    lower because it was set outside Coalide, the slider shows the truth."""

    DEFAULT_CSS = f"""
    VolumeSlider {{
        height: 1;
        width: 1fr;
    }}
    VolumeSlider:focus {{
        text-style: bold;
    }}
    """

    BINDINGS = [
        Binding("left,down,h", "slide(-5)", "Sesi azalt", show=False),
        Binding("right,up,l", "slide(5)", "Sesi artır", show=False),
        Binding("home", "jump(0)", "En düşük", show=False),
        Binding("end", "jump(100)", "En yüksek", show=False),
    ]

    value = reactive(0, init=False)

    class Changed(Message):
        """Posted whenever the user moves the slider."""

        def __init__(self, slider: "VolumeSlider", value: int) -> None:
            super().__init__()
            self.slider = slider
            self.value = value

        @property
        def control(self) -> "VolumeSlider":
            """The slider that sent this message (lets `@on(..., "#volume")`
            match on a selector, like every built-in widget message)."""
            return self.slider

    def __init__(self, value: int = 0, minimum: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._silent = False    # True while the app syncs the slider from the OS
        self._dragging = False
        self.minimum = max(0, min(100, int(minimum)))
        self.set_reactive(VolumeSlider.value, max(0, min(100, int(value))))

    # ---- painting --------------------------------------------------------

    def _bar_width(self) -> int:
        """Cells available for the bar itself (the rest holds the '100%')."""
        return max(10, self.size.width - 7)

    def render(self) -> Text:
        bar_width = self._bar_width()
        filled = max(0, min(bar_width, int(round(self.value / 100 * bar_width))))
        color = MUTED if self.disabled else GREEN
        if filled == 0:
            bar = f"[{MUTED}]{'─' * bar_width}[/]"
        else:
            track = filled - 1  # cells before the knob
            # The stretch below the floor is drawn in the "locked" colour, so
            # it is obvious why the knob refuses to go any further left.
            locked = min(track, max(0, int(round(self.minimum / 100 * bar_width)) - 1))
            bar = (f"[{YELLOW}]{'━' * locked}[/]"
                   f"[{color}]{'━' * (track - locked)}◉[/]"
                   f"[{MUTED}]{'─' * (bar_width - filled)}[/]")
        return Text.from_markup(f"{bar} [bold]{self.value:>3}%[/]")

    def validate_value(self, value: int) -> int:
        return max(0, min(100, int(value)))

    def set_by_user(self, value: int) -> None:
        """Apply a user-driven change, honouring the floor."""
        self.value = max(self.minimum, min(100, int(value)))

    def watch_value(self, value: int) -> None:
        self.refresh()
        if not self._silent:
            self.post_message(self.Changed(self, value))

    def sync_value(self, value: int) -> None:
        """Update the displayed value *without* reporting it back — used when
        the value comes from the OS rather than from the user."""
        self._silent = True
        try:
            self.value = value
        finally:
            self._silent = False

    # ---- input -----------------------------------------------------------

    @property
    def is_dragging(self) -> bool:
        """True while the knob is being dragged (the app pauses its polling
        so a sync cannot yank the knob out from under the mouse)."""
        return self._dragging

    def action_slide(self, delta: int) -> None:
        self.set_by_user(self.value + delta)

    def action_jump(self, value: int) -> None:
        self.set_by_user(value)

    def _value_from_x(self, x: int) -> None:
        bar_width = self._bar_width()
        ratio = x / max(1, bar_width - 1)
        self.set_by_user(round(max(0.0, min(1.0, ratio)) * 100))

    def on_mouse_down(self, event: events.MouseDown) -> None:
        self.focus()
        self._dragging = True
        self.capture_mouse()
        self._value_from_x(event.x)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self._dragging:
            self._value_from_x(event.x)

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if self._dragging:
            self._dragging = False
            self.release_mouse()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.set_by_user(self.value - 5)
        event.stop()

    def on_mouse_scroll_up(self, event: events.MouseScrollUp) -> None:
        self.set_by_user(self.value + 5)
        event.stop()


class SudoScreen(ModalScreen):
    """Admin password prompt for sudo mode.

    Dismisses True on the right password, False after the attempts run out,
    and None if the user backs out with ESC."""

    ATTEMPTS = 3

    BINDINGS = [Binding("escape", "cancel", "Vazgeç")]

    def __init__(self, password: str) -> None:
        super().__init__()
        self._password = password
        self._left = self.ATTEMPTS

    def compose(self) -> ComposeResult:
        with Vertical(id="sudo-box"):
            yield Static(f"[bold {YELLOW}]🔐 Sudo — yönetici doğrulaması[/]")
            yield Static(f"[{MUTED}]Kilitli ses ayarlarını [b]sadece bu oturum[/b] "
                         f"için açar. Ayarlardan çıkınca sudo kapanır.[/]")
            yield Input(password=True, placeholder="Admin şifresi", id="sudo-input")
            yield Static("", id="sudo-msg")

    def on_mount(self) -> None:
        self.query_one("#sudo-input", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Input.Submitted, "#sudo-input")
    def _check(self, event: Input.Submitted) -> None:
        if event.value == self._password:
            self.dismiss(True)
            return
        self._left -= 1
        if self._left <= 0:
            self.dismiss(False)
            return
        self.query_one("#sudo-msg", Static).update(
            f"[{RED}]Yanlış şifre. {self._left} deneme hakkı kaldı.[/]")
        event.input.value = ""


class SettingsApp(App):
    """Coalide settings TUI."""

    TITLE = "Coalide — Ayarlar"
    BINDINGS = [
        Binding("q,escape", "quit", "Çıkış"),
        Binding("a", "open_admin", "Admin Paneli"),
        Binding("s", "sudo", "Sudo"),
    ]

    CSS = f"""
    Screen {{ background: {BG}; }}
    Header {{ background: #1a1a2e; }}
    TabbedContent {{ height: 1fr; }}
    .tab-body {{ padding: 1 2; }}

    .panel {{
        background: {PANEL_BG};
        padding: 1 2;
        margin-bottom: 1;
        height: auto;
        color: #e0e0f0;
    }}
    .p-purple {{ border: round {PURPLE}; }}
    .p-green  {{ border: round {GREEN}; }}
    .p-yellow {{ border: round {YELLOW}; }}
    .p-red    {{ border: round {RED}; }}

    #banner {{
        content-align: center middle;
        height: 5;
        color: {YELLOW};
        text-style: bold;
        background: #1a1a2e;
        border-bottom: heavy {YELLOW};
    }}

    /* Audio tab */
    .slider-row {{ height: 1; margin-top: 1; }}
    .slider-icon {{ width: 4; color: {YELLOW}; }}
    .preset-row {{ height: auto; margin-top: 1; }}
    .preset-row Button {{ margin-right: 1; min-width: 8; }}
    .switch-row {{ height: auto; margin-top: 1; }}
    .switch-text {{ width: 1fr; height: auto; padding: 0 1; }}
    .switch-row Switch {{ width: auto; }}

    /* Masked values */
    .reveal-row {{ height: auto; margin-top: 1; }}
    .reveal {{ min-width: 12; background: #1e1e38; color: {YELLOW}; }}
    .reveal:hover {{ background: {YELLOW}; color: {BG}; }}

    /* Admin tab */
    .admin-row {{ height: auto; margin-top: 1; }}
    .admin-row Button {{ margin-right: 2; }}

    /* Sudo dialog */
    SudoScreen {{ align: center middle; }}
    #sudo-box {{
        width: 62;
        height: auto;
        background: {PANEL_BG};
        border: round {YELLOW};
        padding: 1 2;
    }}
    #sudo-box Input {{ margin-top: 1; }}
    #sudo-msg {{ height: auto; }}
    """

    def __init__(self) -> None:
        super().__init__()
        from utils import get_config
        self.config = get_config()
        self._volume_ok = _IS_WINDOWS and system_volume_available()
        self._active_tab = "tab-about"
        # Sudo lives only in this process: closing the settings menu (going
        # back to the main menu) drops it, and nothing about it is written to
        # disk, so the next run starts locked again.
        self.sudo = False

    @property
    def min_volume(self) -> int:
        """Lowest volume the learner may set, from config.json (0 = no floor).

        Muting is also blocked while a floor is set — otherwise one click on
        the mute switch would undo it. Sudo lifts both."""
        if self.sudo:
            return 0
        try:
            return max(0, min(100, int(self.config.get("Minimum_Volume", 0))))
        except (TypeError, ValueError):
            return 0

    # ---- composition -----------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(f"⚙️  A Y A R L A R  —  {app_version()}"
                     + ("   🔓 SUDO" if self.sudo else ""), id="banner")
        with TabbedContent(initial=self._active_tab):
            with TabPane("🏠 Hakkında", id="tab-about"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._compose_about()
            with TabPane("🔊 Ses", id="tab-audio"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._compose_audio()
            with TabPane("🛠 Yönetim", id="tab-admin"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._compose_admin()
        yield Footer(show_command_palette=False)

    def on_mount(self) -> None:
        if self._volume_ok:
            raised = enforce_minimum_volume(self.config)
            if raised is not None:
                self.notify(f"Ses seviyesi en düşük sınıra (%{raised}) "
                            f"yükseltildi.", title="🔊 Ses sınırı", timeout=5)
            self._sync_from_system()
            # The volume can also be changed outside Coalide (media keys, the
            # tray mixer...), so keep the slider honest while the tab is open.
            self.set_interval(2.0, self._sync_from_system)

    # ---- about tab -------------------------------------------------------

    def _panel(self, title: str, body: str, klass: str, accent: str,
               masked: bool = False) -> ComposeResult:
        """A bordered panel. `masked` adds the 👁 button that asks for sudo and
        reveals the hidden values."""
        with Vertical(classes=f"panel {klass}"):
            yield Static(f"[bold {accent}]{title}[/]\n\n{body}")
            if masked:
                with Horizontal(classes="reveal-row"):
                    yield Button("👁 Göster", classes="reveal")

    def _compose_about(self) -> ComposeResult:
        # Without sudo the paths, file names and config keys are masked: a
        # learner has no use for them, and knowing which file holds which
        # setting is the first step to editing it around the locks.
        settings_line = (f"[{MUTED}]Tüm ayarlar[/] [bold]config.json[/] "
                         f"[{MUTED}]dosyasında tutulur ve Admin Paneli'nden "
                         f"düzenlenir.[/]" if self.sudo else
                         f"[{MUTED}]Tüm ayarlar Admin Paneli'nden düzenlenir.[/]")
        yield Static(
            f"[bold {PURPLE}]Coalide[/] — [{MUTED}]aralıklı tekrar (SM-2) ile "
            f"kelime öğrenme uygulaması.[/]\n\n"
            f"[{MUTED}]Doğru cevaplar kredi kazandırır, krediler ekran süresine "
            f"çevrilir.[/] " + settings_line,
            classes="panel p-purple")

        yield from self._panel("ℹ️ Uygulama Bilgileri", self._app_info_text(),
                               "p-green", GREEN, masked=not self.sudo)

        yield Static(f"[bold {YELLOW}]👤 Geliştirici[/]\n\n"
                     f"[{MUTED}]Geliştiren:[/] [bold]{DEVELOPER}[/]\n"
                     f"[{MUTED}]Lisans:[/] [bold]{LICENSE}[/]\n"
                     f"[{MUTED}]Depo sahibi:[/] "
                     f"[bold]{escape(str(self.config.get('Repo_Owner', '—')))}[/]",
                     classes="panel p-yellow")

        yield from self._panel("🆘 Destek ve Kaynaklar", self._support_text(),
                               "p-purple", PURPLE, masked=not self.sudo)

    def _app_info_text(self) -> str:
        words = _load_json(WORDS_FILE, [])
        word_count = len(words) if isinstance(words, list) else 0
        try:
            from utils import get_current_user
            username = get_current_user()
        except Exception:
            username = "—"
        try:
            import textual
            textual_version = textual.__version__
        except Exception:
            textual_version = "—"
        source = self.config.get("Source_Language", "—")
        target = self.config.get("Target_Language", "—")
        rows = [
            ("Sürüm", app_version()),
            ("Kullanıcı", username),
            ("Diller", f"{source} → {target}"),
            ("Kayıtlı kelime", f"{word_count}"),
            ("Kurulum klasörü", BASE_DIR if self.sudo else MASK),
            ("Python", sys.version.split()[0]),
            ("Textual", textual_version),
        ]
        return "\n".join(f"[{MUTED}]{label + ':':<18}[/] [bold]{escape(_shorten(value))}[/]"
                         for label, value in rows)

    def _support_text(self) -> str:
        owner = self.config.get("Repo_Owner", "MelihAydinYanibol")
        name = self.config.get("Repo_Name", "Coalide")
        repo = f"https://github.com/{owner}/{name}"
        # Local file paths are masked without sudo, like the install folder.
        rows = [
            ("Proje sayfası", repo),
            ("Hata bildir", f"{repo}/issues"),
            ("Sürüm notları", os.path.join(BASE_DIR, "CHANGELOG.md")
             if self.sudo else MASK),
            ("Kullanım kılavuzu", os.path.join(BASE_DIR, "README.md")
             if self.sudo else MASK),
            ("Ebeveyn sunucusu", PCV2_URL),
        ]
        return "\n".join(f"[{MUTED}]{label + ':':<18}[/] [bold]{escape(_shorten(value))}[/]"
                         for label, value in rows)

    # ---- audio tab -------------------------------------------------------

    def _compose_audio(self) -> ComposeResult:
        floor = self.min_volume
        with Vertical(classes="panel p-green"):
            yield Static(f"[bold {GREEN}]🔊 Windows Ses Seviyesi[/]")
            yield Static(f"[{MUTED}]Bu kaydırıcı bilgisayarın ana ses seviyesini "
                         f"değiştirir. Ok tuşları (←/→) ile 5'er adım, fare "
                         f"tekerleği veya çubuğa tıklayarak da ayarlayabilirsiniz.[/]")
            with Horizontal(classes="slider-row"):
                yield Static("🔈", classes="slider-icon")
                yield VolumeSlider(get_system_volume() or 0, minimum=floor,
                                   id="volume", disabled=not self._volume_ok)
            with Horizontal(classes="preset-row"):
                for preset in self._presets(floor):
                    yield Button(f"%{preset}", name=str(preset), classes="preset",
                                 disabled=not self._volume_ok)
            if floor:
                yield Static(f"[bold {YELLOW}]🔒 En düşük ses seviyesi %{floor}[/] "
                             f"[{MUTED}]— yönetici ayarı. Daha kısığı için "
                             f"Yönetim sekmesindeki Sudo düğmesini kullanın.[/]",
                             id="floor-note")
            elif self.sudo:
                yield Static(f"[bold {GREEN}]🔓 Sudo aktif — ses sınırı "
                             f"(config.json → Minimum_Volume) bu oturum için "
                             f"kaldırıldı.[/]", id="floor-note")
            with Horizontal(classes="switch-row"):
                with Vertical(classes="switch-text"):
                    yield Static("[bold]Sistem sesi kapalı (mute)[/]"
                                 + (f" [{YELLOW}]🔒[/]" if floor else ""))
                    yield Static(f"[{MUTED}]" + ("En düşük ses seviyesi ayarlı "
                                 "olduğu için mute kapalı tutuluyor."
                                 if floor else
                                 "Açıkken bilgisayardan hiç ses çıkmaz.") + "[/]")
                yield Switch(value=bool(get_system_mute()), id="system-mute",
                             disabled=not self._volume_ok or bool(floor))

        if not self._volume_ok:
            reason = ("Bu bilgisayar Windows değil."
                      if not _IS_WINDOWS else
                      "Ses aygıtına erişilemedi (bağlı bir çıkış aygıtı yok olabilir).")
            yield Static(f"[bold {RED}]⚠️ Ses seviyesi kontrol edilemiyor[/]\n\n"
                         f"[{MUTED}]{reason} Kaydırıcı ve mute anahtarı devre "
                         f"dışı bırakıldı; ses seviyesini işletim sisteminden "
                         f"ayarlayabilirsiniz.[/]", classes="panel p-red")

        # Read-only unless sudo: pronunciation is part of the lesson, so only
        # someone with the admin password may switch it off.
        with Vertical(classes="panel p-yellow"):
            yield Static(f"[bold {YELLOW}]🎵 Uygulama Sesleri[/]")
            yield Static(f"[{MUTED}]Coalide'ın kendi sesleri: kelime ve cümle "
                         f"telaffuzları. Bu ayar öğrenmenin parçası olduğu için "
                         + ("[b]sudo açık olduğu için düzenlenebilir[/b]."
                            if self.sudo else
                            "burada kapatılamaz — Yönetim sekmesindeki Sudo "
                            "düğmesi veya Admin Paneli gerekir.") + "[/]")
            with Horizontal(classes="switch-row"):
                with Vertical(classes="switch-text"):
                    yield Static("[bold]Telaffuz ve ses efektleri[/]")
                    yield Static(f"[{MUTED}]Ayar anahtarı: "
                                 + ("config.json → Sound_Effects (🔓 sudo)"
                                    if self.sudo else MASK) + "[/]")
                yield Switch(value=bool(self.config.get("Sound_Effects", True)),
                             id="sound-effects", disabled=not self.sudo)
            yield Static(
                self._sound_state_text(bool(self.config.get("Sound_Effects", True))),
                id="sound-state")
            if not self.sudo:
                with Horizontal(classes="reveal-row"):
                    yield Button("👁 Göster", classes="reveal")

    @staticmethod
    def _presets(floor: int) -> list:
        """Quick-set buttons: the floor itself, plus every standard step above
        it (anything below the floor would only bounce back)."""
        return sorted({floor} | {p for p in (0, 25, 50, 75, 100) if p > floor})

    @staticmethod
    def _sound_state_text(enabled: bool = True) -> str:
        return (f"[bold {GREEN}]✅ Sesler açık.[/]" if enabled else
                f"[bold {RED}]🔇 Sesler kapalı — telaffuzlar çalınmıyor.[/]")

    def _sync_from_system(self) -> None:
        """Pull the current OS volume/mute into the widgets (no write-back)."""
        try:
            slider = self.query_one("#volume", VolumeSlider)
        except NoMatches:
            return  # mid-recompose (see _rebuild); the next tick will do
        if slider.is_dragging:
            return
        volume = get_system_volume()
        if volume is not None and volume != slider.value:
            slider.sync_value(volume)
        muted = get_system_mute()
        if muted is not None:
            switch = self.query_one("#system-mute", Switch)
            if switch.value != muted:
                # set_reactive avoids re-triggering our own Switch.Changed
                # handler, which would push the same value straight back.
                switch.set_reactive(Switch.value, muted)
                switch.refresh()

    @on(VolumeSlider.Changed, "#volume")
    def _on_volume_changed(self, event: VolumeSlider.Changed) -> None:
        if not set_system_volume(event.value):
            self.notify("Ses seviyesi değiştirilemedi.", title="⚠️ Ses",
                        severity="error", timeout=4)

    @on(Button.Pressed, ".preset")
    def _on_preset(self, event: Button.Pressed) -> None:
        self.query_one("#volume", VolumeSlider).set_by_user(int(event.button.name))

    @on(Switch.Changed, "#sound-effects")
    def _on_sound_effects(self, event: Switch.Changed) -> None:
        # Only reachable with sudo — the switch is disabled otherwise.
        if not self.sudo:
            return
        saved = _load_json(CONFIG_FILE, {})
        if not isinstance(saved, dict):
            saved = {}
        saved["Sound_Effects"] = event.value
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(saved, f, indent=4, ensure_ascii=False)
        except Exception as error:
            self.notify(f"Ayar kaydedilemedi: {error}", title="⚠️ Kaydedilmedi",
                        severity="error", timeout=5)
            return
        self.config["Sound_Effects"] = event.value
        self.query_one("#sound-state", Static).update(
            self._sound_state_text(event.value))
        self.notify("Uygulama sesleri açıldı." if event.value
                    else "Uygulama sesleri kapatıldı — telaffuzlar çalınmayacak.",
                    title="✅ Ayar kaydedildi", timeout=4)

    @on(Switch.Changed, "#system-mute")
    def _on_mute(self, event: Switch.Changed) -> None:
        if set_system_mute(event.value):
            self.notify("Sistem sesi kapatıldı." if event.value
                        else "Sistem sesi açıldı.", title="🔇 Mute", timeout=3)
        else:
            self.notify("Mute durumu değiştirilemedi.", title="⚠️ Ses",
                        severity="error", timeout=4)

    # ---- admin tab -------------------------------------------------------

    def _compose_admin(self) -> ComposeResult:
        with Vertical(classes="panel p-purple"):
            yield Static(f"[bold {PURPLE}]🔐 Admin Paneli[/]")
            yield Static(f"[{MUTED}]Ebeveynler için: kredi ekleme/çıkarma, "
                         + ("config.json ayarları" if self.sudo else "ayarlar")
                         + " ve kelime listesi yönetimi. Açmak için "
                         + (".env dosyasındaki admin şifresi" if self.sudo
                            else "admin şifresi") + " gerekir.[/]")
            with Horizontal(classes="admin-row"):
                yield Button("🔐 Admin Panelini Aç", variant="primary", id="btn-admin")

        # Sudo unlocks the audio controls in *this* window. The admin panel has
        # no volume slider, so without it a parent could not lower the volume
        # past the floor they set themselves.
        with Vertical(classes="panel p-green" if self.sudo else "panel p-yellow"):
            if self.sudo:
                yield Static(f"[bold {GREEN}]🔓 Sudo aktif[/]")
                yield Static(f"[{MUTED}]Kilitli ses ayarları açıldı: kaydırıcı "
                             f"%0'a inebilir, mute ve telaffuz anahtarı "
                             f"kullanılabilir. Ayarlardan çıkınca sudo kapanır.[/]")
                with Horizontal(classes="admin-row"):
                    yield Button("🔒 Sudo'dan Çık", variant="warning", id="btn-sudo-off")
            else:
                yield Static(f"[bold {YELLOW}]🧑‍💻 Sudo[/]")
                yield Static(f"[{MUTED}]Admin şifresiyle bu penceredeki kilitli "
                             f"ses ayarlarını açar (en düşük ses sınırı, mute ve "
                             f"telaffuz anahtarı). Sadece bu oturum için geçerlidir; "
                             f"ana menüye dönünce kaybolur.[/]")
                with Horizontal(classes="admin-row"):
                    yield Button("🧑‍💻 Sudo", variant="success", id="btn-sudo")

        yield Static(f"[bold {YELLOW}]⌨️ Kısayollar[/]\n\n"
                     f"[{MUTED}]A[/]           Admin panelini aç\n"
                     f"[{MUTED}]S[/]           Sudo (kilitli ayarları aç)\n"
                     f"[{MUTED}]←  →[/]        Ses seviyesini 5'er ayarla\n"
                     f"[{MUTED}]Home / End[/]  Sesi en aza / en çoğa getir\n"
                     f"[{MUTED}]Q  /  Esc[/]   Ayarlardan çık",
                     classes="panel p-yellow")

    @on(Button.Pressed, "#btn-admin")
    def _on_admin(self) -> None:
        self.action_open_admin()

    @on(Button.Pressed, "#btn-sudo")
    def _on_sudo(self) -> None:
        self.action_sudo()

    @on(Button.Pressed, ".reveal")
    def _on_reveal(self) -> None:
        """The 👁 next to a masked value: unmasking is just sudo."""
        self.action_sudo()

    @on(Button.Pressed, "#btn-sudo-off")
    def _on_sudo_off(self) -> None:
        self.sudo = False
        self._rebuild()
        self.notify("Sudo kapatıldı, ayarlar yeniden kilitlendi.",
                    title="🔒 Sudo", timeout=4)

    def action_sudo(self) -> None:
        """Ask for the admin password and, if it matches, unlock the locked
        controls for the rest of this window's lifetime."""
        if self.sudo:
            self.notify("Sudo zaten açık.", title="🔓 Sudo", timeout=3)
            return
        from dotenv import load_dotenv
        load_dotenv()
        password = os.getenv("ADMIN_PASSWORD", "")
        if not password:
            self.notify(".env dosyasında ADMIN_PASSWORD tanımlı değil, sudo "
                        "kullanılamaz.", title="⚠️ Sudo", severity="error", timeout=6)
            return

        def handle(result) -> None:
            if result:
                self.sudo = True
                self._rebuild()
                self.notify("Kilitli ses ayarları bu oturum için açıldı.",
                            title="🔓 Sudo açık", timeout=5)
            elif result is False:
                self.notify("Şifre 3 kez yanlış girildi.", title="⛔ Sudo reddedildi",
                            severity="error", timeout=5)
        self.push_screen(SudoScreen(password), handle)

    def action_open_admin(self) -> None:
        """Run admin.py in the real terminal. It is its own Textual app, so the
        settings TUI has to step aside while it runs."""
        if not os.path.exists(ADMIN_SCRIPT):
            self.notify("admin.py bulunamadı.", title="⚠️ Açılamadı",
                        severity="error", timeout=5)
            return
        with self.suspend():
            print("\033c", end="")
            try:
                subprocess.run([sys.executable, ADMIN_SCRIPT])
            except Exception as error:
                print(f"Admin paneli açılamadı: {error}")
                input("Devam etmek için Enter'a basın...")
        # The admin panel edits config.json, so re-read it before anything here
        # (the sound-effects switch, the volume floor) shows a stale value.
        self._reload_config()

    def _reload_config(self) -> None:
        """Re-read config.json after the admin panel and rebuild the tabs — the
        volume floor, the preset buttons, the mute switch and the sound state
        all come from config, so a parent's change takes effect right away."""
        from utils import get_config
        self.config = get_config()
        self._rebuild()

    def _rebuild(self) -> None:
        """Re-run compose() so every lock (floor, mute, sound switch, masked
        values) is drawn for the current config and sudo state."""
        # compose() reads this, so the rebuilt tabs open on the one the user
        # was already looking at instead of jumping back to the first.
        self._active_tab = self.query_one(TabbedContent).active
        self.refresh(recompose=True)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    try:
        SettingsApp().run()
    finally:
        _drop_endpoint()


if __name__ == "__main__":
    main()

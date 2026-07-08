"""
Textual template: main menu for a language learning app (v2 — styled).

Install first:
    pip install textual

Run:
    python menu_template.py
"""

import subprocess
import sys
import time
import os
import random
from datetime import date, timedelta
from typing import Iterable

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
try:
    from gogo.objects.balance_obj import load_data
    from gogo.utils import get_current_user
except:
    from objects.balance_obj import load_data
    from utils import get_current_user

# Path to the external script you want "Quiz" to launch.
# Change this to wherever your quiz script actually lives.
APP_PATH = "new_master.py"


# Harry Potter quotes shown at the bottom of the menu — one picked at random
# each time the menu opens.
QUOTES = [
    ("Words are, in my not-so-humble opinion, our most inexhaustible source of "
     "magic. Capable of both inflicting injury, and remedying it.", "Albus Dumbledore"),
    ("Understanding is the first step to acceptance, and only with acceptance "
     "can there be recovery.", "Albus Dumbledore"),
    ("It matters not what someone is born, but what they grow to be.", "Albus Dumbledore"),
    ("It is our choices, Harry, that show what we truly are, far more than our "
     "abilities.", "Albus Dumbledore"),
    ("We must all face the choice between what is right and what is easy.", "Albus Dumbledore"),
    ("When in doubt, go to the library.", "Hermione Granger"),
    ("Working hard is important. But there is something that matters even more: "
     "believing in yourself.", "Harry Potter"),
    ("It does not do to dwell on dreams and forget to live.", "Albus Dumbledore"),
    ("Happiness can be found, even in the darkest of times, if one only "
     "remembers to turn on the light.", "Albus Dumbledore"),
    ("Of course it is happening inside your head, Harry, but why on earth "
     "should that mean that it is not real?", "Albus Dumbledore"),
]


class MainMenu(Screen):
    """The main menu screen with navigation options."""

    CSS = """
    Screen {
        background: #0f0f1a;
    }

    #banner {
        content-align: center middle;
        height: 5;
        color: #f5c542;
        text-style: bold;
        background: #1a1a2e;
        border-bottom: heavy #f5c542;
    }

    #body {
        height: 1fr;
        padding: 2 4;
    }

    #menu-panel {
        width: 36;
        height: 1fr;
        border: round #7c5cff;
        padding: 1 2;
        background: #16162a;
        overflow-y: auto;
    }

    #menu-panel-title {
        color: #7c5cff;
        text-style: bold;
        margin-bottom: 1;
    }

    .menu-button {
        width: 100%;
        margin-bottom: 1;
        background: #1e1e38;
        color: #e0e0f0;
        border: none;
        text-align: left;
    }

    .menu-button:hover {
        background: #7c5cff;
        color: #0f0f1a;
        text-style: bold;
    }

    #quit {
        background: #2a1420;
        color: #ff6b81;
    }

    #quit:hover {
        background: #ff6b81;
        color: #0f0f1a;
    }

    #stats-panel {
        width: 1fr;
        height: 1fr;
        margin-left: 3;
        border: round #42d6a4;
        padding: 1 2;
        background: #16162a;
        overflow-y: auto;
    }

    #stats-panel-title {
        color: #42d6a4;
        text-style: bold;
        margin-bottom: 1;
    }

    .stat-row {
        color: #cfcfe8;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("🌍  C O A L I D E  -  V2 🌍", id="banner")
        with Horizontal(id="body"):
            with VerticalScroll(id="menu-panel"):
                yield Static("Seçenekler", id="menu-panel-title")
                yield Button("📝  Öğrenmeye Başla!", id="coalide", classes="menu-button")
                yield Button("📚  Pratik Modu", id="practice", classes="menu-button")
                yield Button("💰  Kredilerini Kullan!", id="credit", classes="menu-button")
                yield Button("📊  İstatistikler", id="stats", classes="menu-button")
                yield Button("⚙️  Admin Modu", id="admin_mode", classes="menu-button")
                yield Button("🚪  Çıkış", id="quit", classes="menu-button")
            with VerticalScroll(id="stats-panel"):
                yield Static("İstatistikler", id="stats-panel-title")
                user = load_data(get_current_user())
                yield Static(self._balance_text(user), id="stat-balance", classes="stat-row")
                yield Static(self._max_text(user), id="stat-max", classes="stat-row")
                yield Static(self._used_text(user), id="stat-used", classes="stat-row")
                quote, author = random.choice(QUOTES)
                yield Static(f"\n[i]\"{quote}\"[/i]\n[i]— {author}[/i]")
        yield Footer(show_command_palette=False)

    @staticmethod
    def _balance_text(user) -> str:
        return f"💵 Kredi:        [b]{user.get_balance()}[/b]"

    @staticmethod
    def _max_text(user) -> str:
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        return f"⏱  En fazla:     [b]{user.max_redeemable_minutes()} dk (Bugün) | {user.max_redeemable_minutes(tomorrow)} dk (Yarın)[/b]"

    @staticmethod
    def _used_text(user) -> str:
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        return f"✅ Kullanılan:   [b]{user.redeemed_minutes_by_date.get(today, 0)} dk (Bugün) | {user.redeemed_minutes_by_date.get(tomorrow, 0)} dk (Yarın)[/b]"

    def refresh_stats(self) -> None:
        """Reload the current user and update the stats panel in place.

        The panel is built once in compose(), so after a subprocess (quiz,
        redeem, etc.) mutates the user's saved data we have to re-read it and
        push the new values into the existing widgets."""
        user = load_data(get_current_user())
        self.query_one("#stat-balance", Static).update(self._balance_text(user))
        self.query_one("#stat-max", Static).update(self._max_text(user))
        self.query_one("#stat-used", Static).update(self._used_text(user))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id in ["coalide", "practice", "credit", "admin_mode","stats"]:
            self.run_python_script(id=button_id)
        elif button_id == "quit":
            self.action_quit_and_shutdown()

    def action_quit_and_shutdown(self) -> None:
        os.system('shutdown -s -t 0')
        self.app.exit()

    def give_arg(self, arg):
        """restarts the application with given argument for sys.argv"""
        os.execv(sys.executable, [sys.executable] + sys.argv + [arg])

    def run_python_script(self,id) -> None:
        """Suspend the TUI, run the external python script in the real terminal,
        then resume the TUI once it exits."""
        with self.app.suspend():
            # Clear the screen so the quiz script starts on a blank terminal.
            print("\033c", end="")
            ret=False
            if id == "coalide": subprocess.run([sys.executable, APP_PATH])
            elif id == "credit": from new_master import redeem_flow; redeem_flow(load_data(get_current_user()))
            else:print(f"\n'{id}' Özelliği daha tamamlanmadı, Ana menüye dönülüyor...");time.sleep(3);ret=True
            if not ret:input("\nQuiz finished. Press Enter to return to the menu...")
        # The subprocess/flow above may have changed the user's credits or
        # redeemed minutes, so re-read them into the stats panel now that the
        # TUI has resumed.
        self.refresh_stats()

class PlaceholderScreen(Screen):
    """Generic placeholder screen for menu items not built out yet."""

    BINDINGS = [("escape", "app.pop_screen", "Back to menu")]

    CSS = """
    Screen {
        background: #0f0f1a;
    }
    #content {
        padding: 2 4;
        color: #e0e0f0;
    }
    #title {
        color: #f5c542;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="content"):
            yield Static(f"{self.name}", id="title")
            yield Static(f"Build out the '{self.name}' screen here.\n\nPress ESC to go back.")
        yield Footer(show_command_palette=False)


class LanguageApp(App):
    """Main app entry point."""

    TITLE = "Coalide V2"

    # Keep the palette feature itself ON — required for it to work at all.
    ENABLE_COMMAND_PALETTE = True

    # Custom hotkey instead of the default ctrl+p. show=False keeps it out
    # of any BINDINGS-based key display.
    BINDINGS = [
        Binding("f2", "command_palette", "Commands", show=False),
    ]

    # Hides the little icon in the top-left of the Header, which otherwise
    # shows an "Open the command palette" tooltip on hover.
    CSS = """
    HeaderIcon {
        display: none;
    }
    """

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        yield from super().get_system_commands(screen)
        if isinstance(screen, MainMenu):
            yield SystemCommand(
                "Start Learning", "Launch the main quiz (Öğrenmeye Başla)",
                lambda: screen.run_python_script("coalide"),
            )
            yield SystemCommand(
                "Restart in debug", "Restart the app with debug logging enabled",
                lambda: screen.give_arg("-debug"),
            )
            yield SystemCommand(
                "Pack Data", "Pack important data files into 'packaged_data' folder",
                lambda: screen.give_arg("-pack-data"),
            )
            yield SystemCommand(
                "Create TTS Cache", "Generate TTS cache for words and sentences with elevenlabs",
                lambda: screen.give_arg("-create-tts-cache"),
            )
            yield SystemCommand(
                "Practice Mode", "Open practice mode (Pratik Modu)",
                lambda: screen.run_python_script("practice"),
            )
            yield SystemCommand(
                "Redeem Credits", "Use your credits (Kredilerini Kullan)",
                lambda: screen.run_python_script("credit"),
            )
            yield SystemCommand(
                "Statistics", "View your stats (İstatistikler)",
                lambda: screen.run_python_script("stats"),
            )
            yield SystemCommand(
                "Admin Mode", "Open admin mode (Admin Modu)",
                lambda: screen.run_python_script("admin_mode"),
            )
            yield SystemCommand(
                "Quit & Shutdown", "Shut down the computer and exit (Çıkış)",
                screen.action_quit_and_shutdown,
            )

    def on_mount(self) -> None:
        self.push_screen(MainMenu())

def set_console_font_size(height: int = 3) -> None:
    """
    Shrink the console font on the classic Windows console (conhost.exe) so
    the menu fits more comfortably. Font size is otherwise the terminal's job,
    not the app's -- this uses the Win32 SetCurrentConsoleFontEx API, which
    only conhost honors. It is a silent no-op on non-Windows and inside
    Windows Terminal (which has no programmatic font-size support). The change
    persists for the console session after the app exits.
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        LF_FACESIZE = 32
        STD_OUTPUT_HANDLE = -11

        class CONSOLE_FONT_INFOEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("nFont", ctypes.c_ulong),
                ("dwFontSize", wintypes._COORD),
                ("FontFamily", ctypes.c_uint),
                ("FontWeight", ctypes.c_uint),
                ("FaceName", ctypes.c_wchar * LF_FACESIZE),
            ]

        handle = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        font = CONSOLE_FONT_INFOEX()
        font.cbSize = ctypes.sizeof(CONSOLE_FONT_INFOEX)
        # Read the current font first so we preserve the face name and weight.
        ctypes.windll.kernel32.GetCurrentConsoleFontEx(handle, False, ctypes.byref(font))
        font.dwFontSize.X = 0        # 0 = let Windows pick a matching width
        font.dwFontSize.Y = height   # pixel height; smaller value = smaller font
        ctypes.windll.kernel32.SetCurrentConsoleFontEx(handle, False, ctypes.byref(font))
    except Exception:
        pass  # never let a cosmetic tweak break app startup


def main():
    set_console_font_size()
    app = LanguageApp()
    app.run()

if __name__ == "__main__":
    main()
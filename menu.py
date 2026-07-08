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
                """ yield Static("🔥 Streak:        [b]12 days[/b]", classes="stat-row")
                yield Static("📖 Words learned: [b]348[/b]", classes="stat-row")
                yield Static("🎯 Accuracy:      [b]87%[/b]", classes="stat-row")
                yield Static("⏱  Time today:    [b]22 min[/b]", classes="stat-row") """
                yield Static("\n[i]\"Words are, in my not-so-humble opinion, our most inexhaustible source of magic.\"[/i]\n[i]— Albus Dumbledore[/i]")
        yield Footer(show_command_palette=False)

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

def main():
    app = LanguageApp()
    app.run()

if __name__ == "__main__":
    main()
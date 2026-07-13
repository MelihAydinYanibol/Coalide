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
from datetime import date, datetime, timedelta
from typing import Iterable

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button
try:
    from objects.balance_obj import load_data
    from utils import get_current_user
except:
    from objects.balance_obj import load_data
    from utils import get_current_user

# Path to the external script you want "Quiz" to launch.
# Change this to wherever your quiz script actually lives.
APP_PATH = "new_master.py"


# Inspirational quotes shown at the bottom of the menu — one picked at random
# each time the menu opens. A mix of Harry Potter, Star Wars, Star Trek and a
# few other classics.
QUOTES = [
    # --- Harry Potter ---
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
    ("We've all got both light and dark inside us. What matters is the part we "
     "choose to act on. That's who we really are.", "Sirius Black"),
    ("Fear of a name only increases fear of the thing itself.", "Hermione Granger"),

    # --- Star Wars ---
    ("Do. Or do not. There is no try.", "Yoda"),
    ("In a dark place we find ourselves, and a little more knowledge lights our "
     "way.", "Yoda"),
    ("Train yourself to let go of everything you fear to lose.", "Yoda"),
    ("The greatest teacher, failure is.", "Yoda"),
    ("Patience you must have, my young Padawan.", "Yoda"),
    ("Your focus determines your reality.", "Qui-Gon Jinn"),
    ("Never tell me the odds.", "Han Solo"),

    # --- Star Trek ---
    ("It is possible to commit no mistakes and still lose. That is not a "
     "weakness; that is life.", "Jean-Luc Picard"),
    ("Things are only impossible until they're not.", "Jean-Luc Picard"),
    ("Live long and prosper.", "Spock"),
    ("Insufficient facts always invite danger.", "Spock"),
    ("A little suffering is good for the soul.", "James T. Kirk"),

    # --- Other classics ---
    ("Not all those who wander are lost.", "J.R.R. Tolkien"),
    ("It is not our abilities that show what we truly are. It is our choices... "
     "Little by little, one travels far.", "J.R.R. Tolkien"),
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("Somewhere, something incredible is waiting to be known.", "Carl Sagan"),
    ("With great power comes great responsibility.", "Uncle Ben"),
]


# --- Easter egg: rare "secret" quotes ---
# There is a small chance (see compose) that the quote at the bottom of the
# menu is drawn from this pool instead of the Harry Potter one above.
SECRET_QUOTES = [
    ("I solemnly swear that I am up to no good.", "Marauder's Map"),
    ("Learning another language is not only learning different words for the "
     "same things, but learning another way to think about things.", "Flora Lewis"),
    ("A different language is a different vision of life.", "Federico Fellini"),
    ("The limits of my language mean the limits of my world.", "Ludwig Wittgenstein"),
    ("Şşşt... gizli bir mesaj buldun. Çalışmaya devam! 🤫", "Coalide"),
]


# --- Easter egg: the Konami code ---
# Enter ↑ ↑ ↓ ↓ ← → ← → B A on the main menu for a little surprise.
KONAMI_CODE = ["up", "up", "down", "down", "left", "right", "left", "right", "b", "a"]

BANNER_DEFAULT = "🌍  C O A L I D E  -  V2 🌍"
BANNER_SECRET = "✨🎉  H A R İ K A S I N !  🎉✨"


# --- Easter egg: click the banner a few times ---
# Click the COALIDE banner this many times to reveal a hidden dev credit.
BANNER_CLICKS_NEEDED = 7
BANNER_DEV_CREDIT = "👾  Coalide — Melih tarafından ❤️ ile yapıldı  👾"


# --- Easter egg: special-date banners ---
# On these days the banner shows a festive message instead of the default.
# Keys are "MM-DD". Add your own birthday below (uncomment and set the date).
SPECIAL_DATES = {
    "01-01": "🎆  M U T L U   Y I L L A R !  🎆",
    "04-01": "🤡  1 Nisan! Krediler bugün 2 katı... değil 😜  🤡",
    "12-31": "🥳  İyi ki bu yıl da çalıştın!  🥳",
    # "MM-DD": "🎂  İYİ Kİ DOĞDUN!  🎂",   # <- set your birthday here
}


# --- Easter egg: type a secret word ---
# Spell one of these on the main menu (just start typing) for a surprise.
# Each maps a word -> (banner text, toast title, toast message).
SECRET_WORDS = {
    "sudo": (
        "🔒  ERİŞİM REDDEDİLDİ... şaka şaka 😏  🔒",
        "🐧 sudo",
        "Nice try! Burada root yok, sadece kelimeler var.",
    ),
    "coalide": (
        "💜  C O A L I D E  💜",
        "💜 Coalide",
        "Uygulamanın adını yazdın! Sana bir tebrik borçluyuz. 🎉",
    ),
    "neo": (
        "💊  Kırmızı hap mı, mavi hap mı?  💊",
        "🕶️ Neo",
        "Matrix'e hoş geldin. Öğrenmek de en az onun kadar derin bir tavşan deliği.",
    ),
    "matrix": (
        "🟩  W A K E   U P . . .  🟩",
        "🟩 Matrix",
        "Takip et beyaz tavşanı 🐇",
    ),
    "poliglot": (
        "🗣️  P O L I G L O T   M O D U  🗣️",
        "🗣️ Poliglot",
        "Bir dil bir insan, iki dil iki insan! Devam et. 🌍",
    ),
}
MAX_WORD_LEN = max(len(w) for w in SECRET_WORDS)


# --- Easter egg: rainbow banner ---
# Colours the Konami-code flash cycles through for a couple of seconds.
RAINBOW_COLORS = ["#ff6b81", "#f5c542", "#42d6a4", "#7c5cff", "#5cc8ff", "#ff9f43"]
BANNER_COLOR = "#f5c542"   # the banner's normal colour (matches the CSS)


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
        yield Static(self._banner_text(), id="banner")
        with Horizontal(id="body"):
            with VerticalScroll(id="menu-panel"):
                yield Static("Seçenekler", id="menu-panel-title")
                yield Button("📝  Öğrenmeye Başla!", id="coalide", classes="menu-button")
                yield Button("📚  Pratik Modu", id="practice", classes="menu-button")
                yield Button("💰  Kredilerini Kullan!", id="credit", classes="menu-button")
                yield Button("📊  İstatistikler", id="stats", classes="menu-button")
                yield Button("⚙️  Ayarlar", id="settings", classes="menu-button")
                yield Button("🚪  Çıkış", id="quit", classes="menu-button")
            with VerticalScroll(id="stats-panel"):
                yield Static("İstatistikler", id="stats-panel-title")
                user = load_data(get_current_user())
                yield Static(self._balance_text(user), id="stat-balance", classes="stat-row")
                yield Static(self._max_text(user), id="stat-max", classes="stat-row")
                yield Static(self._used_text(user), id="stat-used", classes="stat-row")
                # Easter egg: click this quote to re-roll it (see on_click).
                yield Static(self._random_quote_text(), id="quote")
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

    @staticmethod
    def _random_quote_text() -> str:
        """Format a random quote — ~5% chance from the secret pool."""
        pool = SECRET_QUOTES if random.random() < 0.05 else QUOTES
        quote, author = random.choice(pool)
        return f"\n[i]\"{quote}\"[/i]\n[i]— {author}[/i]"

    @staticmethod
    def _time_greeting() -> tuple[str, str]:
        """Easter egg: a friendly (title, message) based on the time of day."""
        hour = datetime.now().hour
        if hour < 5:
            return ("🌙 Gece kuşu", "Gece gece çalışıyorsun! Efsanesin, ama uykuya da saygı 😴")
        if hour < 12:
            return ("☀️ Günaydın", "Güne kelimelerle başlamak gibisi yok! ☕")
        if hour < 18:
            return ("🌤️ İyi günler", "Günün ortası — biraz pratik zamanı! 💪")
        if hour < 23:
            return ("🌆 İyi akşamlar", "Akşam tekrarı bilgiyi kalıcı yapar! 📚")
        return ("🌙 İyi geceler", "Yatmadan önce birkaç kelime? 🌟")

    def _rainbow_banner(self, seconds: float = 3, interval: float = 0.15) -> None:
        """Easter egg: cycle the banner through rainbow colours, then restore."""
        banner = self.query_one("#banner", Static)
        state = {"i": 0}
        steps = max(1, int(seconds / interval))

        def tick() -> None:
            banner.styles.color = RAINBOW_COLORS[state["i"] % len(RAINBOW_COLORS)]
            state["i"] += 1
            if state["i"] >= steps:
                timer.stop()
                banner.styles.color = BANNER_COLOR

        timer = self.set_interval(interval, tick)

    @staticmethod
    def _banner_text() -> str:
        """Easter egg: festive banner on special dates, default otherwise."""
        return SPECIAL_DATES.get(date.today().strftime("%m-%d"), BANNER_DEFAULT)

    def _flash_banner(self, text: str, seconds: float = 4) -> None:
        """Show `text` on the banner, then restore the date-aware default."""
        banner = self.query_one("#banner", Static)
        banner.update(text)
        self.set_timer(seconds, lambda: banner.update(self._banner_text()))

    def on_mount(self) -> None:
        # State for the keyboard/click easter eggs (see on_key / on_click).
        self._konami_buffer: list[str] = []   # last few keys, for the Konami code
        self._word_buffer: str = ""           # recent letters, for secret words
        self._banner_clicks: int = 0          # running banner-click count

        # Easter egg: a friendly greeting based on the time of day.
        title, message = self._time_greeting()
        self.app.notify(message, title=title, timeout=6)

    def on_key(self, event) -> None:
        """Easter eggs: Konami code (↑↑↓↓←→←→ B A) and typed secret words."""
        key = event.key

        # Konami code.
        self._konami_buffer.append(key)
        self._konami_buffer = self._konami_buffer[-len(KONAMI_CODE):]
        if self._konami_buffer == KONAMI_CODE:
            self._konami_buffer.clear()
            self._trigger_konami()
            return

        # Typed secret words (only track single letters).
        if len(key) == 1 and key.isalpha():
            self._word_buffer = (self._word_buffer + key.lower())[-MAX_WORD_LEN:]
            for word in SECRET_WORDS:
                if self._word_buffer.endswith(word):
                    self._word_buffer = ""
                    self._trigger_word(word)
                    break

    def on_click(self, event) -> None:
        """Easter eggs: click the banner a few times, or click the quote to re-roll."""
        widget = getattr(event, "widget", None)
        widget_id = getattr(widget, "id", None)

        # Click the quote to swap in a fresh one.
        if widget_id == "quote":
            self.query_one("#quote", Static).update(self._random_quote_text())
            return

        # Click the banner BANNER_CLICKS_NEEDED times for a hidden dev credit.
        if widget_id == "banner":
            self._banner_clicks += 1
            if self._banner_clicks >= BANNER_CLICKS_NEEDED:
                self._banner_clicks = 0
                self._flash_banner(BANNER_DEV_CREDIT, seconds=5)
                self.app.notify(
                    "Geliştiriciye selam gönderdin! 👋",
                    title="🔧 Kim yaptı bunu?",
                    timeout=5,
                )

    def _trigger_konami(self) -> None:
        self._flash_banner(BANNER_SECRET)
        self._rainbow_banner()
        self.app.notify(
            "Gizli kodu buldun! 30 saniye çalışırsan bir şey olmaz... ya da olur? 🚀",
            title="🎮 Konami Code",
            timeout=5,
        )

    def _trigger_word(self, word: str) -> None:
        banner_text, title, message = SECRET_WORDS[word]
        self._flash_banner(banner_text)
        self.app.notify(message, title=title, timeout=5)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id in ["coalide", "practice", "credit", "settings","stats"]:
            self.run_python_script(id=button_id)
        elif button_id == "quit":
            self.action_quit_and_shutdown()

    def action_quit_and_shutdown(self) -> None:
        os.system('shutdown /l')
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
            elif id == "settings" or id == "admin_mode":
                if not id == "admin_mode":
                    print("\nAyarlar menüsü henüz tamamlanmadı, Sadece admin modu mevcut.")
                    options = {1: "Admin Modu", 2: "Ana menüye dön"}
                    for k, v in options.items():
                        print(f"{k}. {v}")
                    opt = input("\nSeçenek seçin: ").strip()
                else:opt="1"
                # Admin is its own Textual app now, so run it as a subprocess
                # (a nested App inside suspend() would fight over the terminal).
                if opt == "1": subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.py")])
            elif id == "practice": from practice import main; main()
            # Stats is its own Textual app, so run it as a subprocess (a
            # nested App inside suspend() would fight over the terminal).
            elif id == "stats": subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats_menu.py")])
            else:print(f"\n'{id}' Özelliği daha tamamlanmadı, Ana menüye dönülüyor...");time.sleep(3);ret=True
            """ if not ret:input("\nQuiz finished. Press Enter to return to the menu...") """
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

def set_console_font_size(height: int = 22) -> None:
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
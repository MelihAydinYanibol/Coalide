"""
Coalide — Kredilerini Kullan

A Textual TUI replacing the old console redeem_flow() in new_master.py:
  - live credit balance and per-date usage
  - date picker (today / tomorrow / any date, within the weekly reset window)
  - minute picker with quick +/- steps and an "En Fazla" button that fills in
    the largest amount the current balance can actually buy for that date
  - the price is always on screen and re-prices as you type, so the confirm
    button itself carries the final cost instead of a separate popup

Run standalone:  python redeem_menu.py
From the menu:   the "Kredilerini Kullan" button launches it as a subprocess.
"""

from datetime import date, timedelta

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Static

from objects.balance_obj import MINUTES_PER_DAY, load_data
from utils import ensure_current_user, get_config, get_current_user

# Palette — matches menu.py / stats_menu.py
BG = "#0f0f1a"
PANEL_BG = "#16162a"
PURPLE = "#7c5cff"
GREEN = "#42d6a4"
YELLOW = "#f5c542"
RED = "#ff6b81"
MUTED = "#9a9ac0"

QUICK_STEPS = [-10, +10, +30]


def week_end() -> date:
    """
    Last date time can be banked for. Credits reset every Monday, so redeeming
    past this week's Sunday would defeat the reset. With the weekly reset off
    there is no such limit.
    """
    if get_config().get("Credit_Reset_Weekly", True):
        today = date.today()
        return today + timedelta(days=6 - today.weekday())
    return date.max


def fmt_minutes(minutes: int) -> str:
    """90 -> '1sa 30dk', 45 -> '45dk'."""
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}sa {mins}dk"
    if hours:
        return f"{hours}sa"
    return f"{mins}dk"


class RedeemApp(App):
    """Kredilerini Kullan ekranı."""

    TITLE = "Coalide — Kredilerini Kullan"

    BINDINGS = [
        Binding("q,escape", "quit", "Çıkış"),
        Binding("m", "use_max", "En Fazla"),
    ]

    CSS = f"""
    Screen {{ background: {BG}; }}
    Header {{ background: #1a1a2e; }}

    #banner {{
        content-align: center middle;
        height: 3;
        color: {YELLOW};
        text-style: bold;
        background: #1a1a2e;
        border-bottom: heavy {YELLOW};
    }}

    #body {{ height: 1fr; padding: 1 2; }}

    #balance {{ height: 1; padding: 0 1; margin-bottom: 1; }}

    .panel {{
        height: auto;
        border: round {PURPLE};
        background: {PANEL_BG};
        padding: 1 2;
    }}

    .row {{ height: 3; }}

    .row-label {{ width: 12; height: 3; content-align: left middle; color: {MUTED}; }}

    #date-info {{ height: 1; padding: 0 0 0 12; margin: 1 0; }}

    Input {{
        background: #1e1e38;
        color: #e0e0f0;
        border: tall #1e1e38;
    }}

    Input:focus {{ border: tall {PURPLE}; }}

    /* Sized per field so the whole minutes row -- input, En Fazla and the
       quick steps -- stays inside 80 columns without looking squeezed. */
    #date-input {{ width: 16; }}
    #minutes-input {{ width: 12; }}

    .chip {{
        width: 9;
        min-width: 9;
        margin-left: 2;
        background: #1e1e38;
        color: #e0e0f0;
        border: none;
        height: 3;
        content-align: center middle;
    }}

    .chip:hover {{ background: {PURPLE}; color: {BG}; text-style: bold; }}

    #max {{
        width: 13;
        min-width: 13;
        background: #1f2f28;
        color: {GREEN};
    }}

    #max:hover {{ background: {GREEN}; color: {BG}; text-style: bold; }}

    #price {{
        height: 3;
        border: round {GREEN};
        background: {PANEL_BG};
        margin: 0 2;
        padding: 0 1;
        content-align: left middle;
        color: #cfcfe8;
    }}

    #status {{ height: 2; padding: 0 3; }}

    #actions {{ height: 3; padding: 0 2; }}

    #confirm {{
        width: 34;
        background: #1f2f28;
        color: {GREEN};
        border: none;
        height: 3;
        content-align: center middle;
    }}

    #confirm:hover {{ background: {GREEN}; color: {BG}; text-style: bold; }}

    #confirm:disabled {{ background: #1a1a26; color: {MUTED}; }}

    #close {{
        width: 16;
        margin-left: 2;
        background: #2a1420;
        color: {RED};
        border: none;
        height: 3;
        content-align: center middle;
    }}

    #close:hover {{ background: {RED}; color: {BG}; text-style: bold; }}
    """

    def __init__(self) -> None:
        super().__init__()
        self.user = load_data(get_current_user(prompt=False))
        self._busy = False          # a redeem call is in flight
        self._cost = 0              # cost of the current selection, in credits
        self._ok = False            # is the current selection redeemable?

    # ---------------------------------------------------------------- layout

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("💰  K R E D İ L E R İ N İ   K U L L A N  💰", id="banner")
        with VerticalScroll(id="body"):
            yield Static("", id="balance")
            with Vertical(classes="panel"):
                with Horizontal(classes="row"):
                    yield Static("📅  Gün", classes="row-label")
                    yield Input(value=date.today().isoformat(),
                                placeholder="YYYY-AA-GG", id="date-input")
                    yield Button("Bugün", id="date-today", classes="chip")
                    yield Button("Yarın", id="date-tomorrow", classes="chip")
                yield Static("", id="date-info")
                with Horizontal(classes="row"):
                    yield Static("⏱  Dakika", classes="row-label")
                    yield Input(value="30", type="integer", id="minutes-input")
                    yield Button("🔝 En Fazla", id="max", classes="chip")
                    for step in QUICK_STEPS:
                        yield Button(f"{step:+d}", id=f"step{step}", classes="chip")

        # Price, status and the buttons live outside the scroll region, so the
        # confirm button stays on screen no matter how short the terminal is.
        yield Static("", id="price")
        yield Static("", id="status")
        with Horizontal(id="actions"):
            yield Button("✅  Onayla", id="confirm")
            yield Button("🚪  Kapat", id="close")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_all()

    # ------------------------------------------------------------ state read

    def _minutes(self) -> int:
        """Whatever is currently typed in the minutes box, or 0 if unusable."""
        try:
            return int(self.query_one("#minutes-input", Input).value.strip())
        except ValueError:
            return 0

    def _date(self) -> date | None:
        """The typed date, or None if it isn't a real YYYY-AA-GG date."""
        try:
            return date.fromisoformat(self.query_one("#date-input", Input).value.strip())
        except ValueError:
            return None

    # -------------------------------------------------------------- refresh

    def _check(self) -> tuple[bool, str]:
        """
        Validate the current selection. Returns (redeemable, message) — the
        same rules redeem_screentime() enforces, checked up front so the
        problem is on screen before the button is ever pressed.
        """
        target = self._date()
        if target is None:
            return False, f"[{RED}]Tarih geçerli değil — YYYY-AA-GG biçiminde yaz.[/]"
        if target < date.today():
            return False, f"[{RED}]Bu tarih geçmişte kaldı.[/]"
        limit = week_end()
        if target > limit:
            return False, (f"[{RED}]Krediler her pazartesi sıfırlanır — en geç "
                           f"{limit.isoformat()} için süre alabilirsin.[/]")

        minutes = self._minutes()
        if minutes <= 0:
            return False, f"[{MUTED}]Kaç dakika istediğini yaz.[/]"

        already = self.user.redeemed_minutes_by_date.get(target.isoformat(), 0)
        if already + minutes > MINUTES_PER_DAY:
            return False, (f"[{RED}]Bir gün {MINUTES_PER_DAY} dakikadan uzun olamaz — "
                           f"bu tarih için en fazla {MINUTES_PER_DAY - already} dakika "
                           f"daha alabilirsin.[/]")

        if self._cost > self.user.get_balance():
            return False, (f"[{RED}]Yeterli kredin yok — bu {self._cost} kredi, "
                           f"sende {self.user.get_balance()} kredi var.[/]")

        return True, ""

    def refresh_all(self, status: str | None = None) -> None:
        """Re-price the current selection and repaint every derived label."""
        target = self._date()
        minutes = self._minutes()
        iso = target.isoformat() if target else None

        self._cost = (self.user.cost_for_minutes(minutes, iso)
                      if target and minutes > 0 else 0)
        self._ok, message = self._check()

        self.query_one("#balance", Static).update(
            f"[{MUTED}]Kullanıcı:[/] [b]{self.user.username or '—'}[/]     "
            f"[{MUTED}]Bakiye:[/] [b {YELLOW}]{self.user.get_balance()}[/] kredi")

        if target:
            already = self.user.redeemed_minutes_by_date.get(iso, 0)
            affordable = self.user.max_redeemable_minutes(iso)
            self.query_one("#date-info", Static).update(
                f"[{MUTED}]Bu tarih için alınmış:[/] [b]{fmt_minutes(already)}[/]   "
                f"[{MUTED}]Alabileceğin en fazla:[/] [b {GREEN}]{fmt_minutes(affordable)}[/]")
        else:
            self.query_one("#date-info", Static).update("")

        if minutes > 0 and target:
            self.query_one("#price", Static).update(
                f"[{MUTED}]Seçim:[/] [b]{fmt_minutes(minutes)}[/] "
                f"[{MUTED}]→[/] [b {YELLOW}]{self._cost}[/] [{MUTED}]kredi[/]   "
                f"[{MUTED}]· sonrasında kalan:[/] "
                f"[b]{max(0, self.user.get_balance() - self._cost)}[/]")
        else:
            self.query_one("#price", Static).update(f"[{MUTED}]—[/]")

        self.query_one("#status", Static).update(status if status is not None else message)

        confirm = self.query_one("#confirm", Button)
        confirm.disabled = self._busy or not self._ok
        if self._busy:
            confirm.label = "⏳  İşleniyor..."
        elif self._ok:
            confirm.label = f"✅  Onayla — {self._cost} kredi"
        else:
            confirm.label = "✅  Onayla"

    @on(Input.Changed)
    def _on_input(self) -> None:
        self.refresh_all()

    # -------------------------------------------------------------- actions

    @on(Button.Pressed, "#date-today")
    def _today(self) -> None:
        self.query_one("#date-input", Input).value = date.today().isoformat()

    @on(Button.Pressed, "#date-tomorrow")
    def _tomorrow(self) -> None:
        self.query_one("#date-input", Input).value = (date.today() + timedelta(days=1)).isoformat()

    @on(Button.Pressed, ".chip")
    def _step(self, event: Button.Pressed) -> None:
        """The +/- quick buttons; the date/max chips are handled elsewhere."""
        button_id = event.button.id or ""
        if not button_id.startswith("step"):
            return
        step = int(button_id.removeprefix("step"))
        box = self.query_one("#minutes-input", Input)
        box.value = str(max(0, self._minutes() + step))

    @on(Button.Pressed, "#max")
    def _max(self) -> None:
        self.action_use_max()

    def action_use_max(self) -> None:
        """Fill in the largest number of minutes the balance can buy for the
        selected date. Already accounts for the escalating price, the credits
        on hand, and time previously taken for that date."""
        target = self._date()
        if target is None:
            self.refresh_all(f"[{RED}]Önce geçerli bir tarih yaz.[/]")
            return
        minutes = self.user.max_redeemable_minutes(target.isoformat())
        if minutes <= 0:
            # Leave whatever they typed alone -- overwriting it with 0 helps
            # nobody, and an unchanged box means this message isn't immediately
            # cleared by the Input.Changed refresh.
            self.refresh_all(
                f"[{RED}]Şu an hiç dakika alamıyorsun — {self.user.get_balance()} "
                f"kredin var.[/]")
            return
        self.query_one("#minutes-input", Input).value = str(minutes)

    @on(Button.Pressed, "#close")
    def _close(self) -> None:
        self.exit()

    @on(Button.Pressed, "#confirm")
    def _confirm(self) -> None:
        if self._busy or not self._ok:
            return
        target = self._date()
        minutes = self._minutes()
        if target is None or minutes <= 0:
            return
        self._busy = True
        self.refresh_all(f"[{YELLOW}]Ekran süresi tanımlanıyor, bekle...[/]")
        self._redeem(minutes, target.isoformat(), self._cost, self.user.get_balance())

    @work(thread=True, exclusive=True)
    def _redeem(self, minutes: int, target: str, cost: int, pre_balance: int) -> None:
        """Redeeming calls the parental-control server, which can take a few
        seconds — run it off the event loop so the UI keeps responding."""
        ok = self.user.redeem_screentime(minutes, target)
        self.call_from_thread(self._redeemed, ok, minutes, target, cost, pre_balance)

    def _redeemed(self, ok: bool, minutes: int, target: str, cost: int, pre_balance: int) -> None:
        self._busy = False
        if ok:
            self.refresh_all(
                f"[{GREEN}]✅ Başarılı! {target} için {fmt_minutes(minutes)} tanımlandı. "
                f"Kalan bakiye: {self.user.get_balance()} kredi.[/]")
        elif pre_balance < cost:
            self.refresh_all(
                f"[{RED}]Yeterli kredin yok — sende {pre_balance} kredi var, "
                f"bunun maliyeti {cost} kredi.[/]")
        else:
            self.refresh_all(
                f"[{RED}]Ekran süresi sunucusuna ulaşılamadı — kredilerin "
                f"HARCANMADI. Biraz sonra tekrar dene.[/]")


def main() -> None:
    # Ask for the username here, on a plain console: prompting once the TUI is
    # up only produces a blank screen (see utils._can_prompt).
    ensure_current_user()
    RedeemApp().run()


if __name__ == "__main__":
    main()

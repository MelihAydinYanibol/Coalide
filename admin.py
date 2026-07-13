"""
Coalide — Admin Paneli (TUI)

Admin mode for Coalide, intended for parents. A Textual TUI with three tabs:
  - 💰 Krediler: view the child's balance, add/remove credits.
  - ⚙️ Ayarlar:  edit every key in config.json in place (switches for
    booleans, inputs for numbers/strings/lists).
  - 🔤 Kelimeler: browse words.json in a table; add, edit or delete words.

Access is gated behind ADMIN_PASSWORD from the .env file (3 attempts),
just like the old command-line admin mode.

Run standalone:  python admin.py
From the menu:   "Admin Mode" launches it as a subprocess (it is its own
                 Textual app, so it must not run nested inside menu.py's).
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
WORDS_FILE = os.path.join(BASE_DIR, "words.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")

# Palette — matches menu.py / stats_menu.py
BG = "#0f0f1a"
PANEL_BG = "#16162a"
PURPLE = "#7c5cff"
GREEN = "#42d6a4"
YELLOW = "#f5c542"
RED = "#ff6b81"
MUTED = "#9a9ac0"

WORD_TYPES = ["noun", "verb", "adjective", "adverb", "pronoun", "preposition", "other"]

# Parent-friendly descriptions for each config.json key.
CONFIG_DESCRIPTIONS = {
    "Daily_New_Word_Cap": "Bir günde en fazla kaç yeni kelime tanıtılır.",
    "No_Repeat_Window": "Aynı kelime tekrar sorulmadan önce kaç soru geçmeli.",
    "Repo_Owner": "Güncellemelerin indirildiği GitHub kullanıcısı.",
    "Repo_Name": "Güncellemelerin indirildiği GitHub deposu.",
    "Update_Prereleases": "Ön sürüm (beta) güncellemeleri de yüklensin mi.",
    "Source_Language": "Kaynak dil (çocuğun bildiği dil).",
    "Target_Language": "Hedef dil (öğrenilen dil).",
    "ElevenLabs_API_Key": "Seslendirme için ElevenLabs anahtar listesi (JSON listesi).",
    "BASE_RATE_PER_MINUTE": "1 dakika ekran süresinin taban kredi fiyatı.",
    "ESCALATION_PER_HOUR": "Aynı gün alınan her ek saatte fiyat artış oranı (0.5 = %50).",
    "SPAM_PROTECTION": "Art arda rastgele cevap yazmayı engelle.",
    "INPUT_TIMEOUT": "Cevap için süre sınırı, saniye (0 = kapalı).",
    "Credit_Reset_Weekly": "Krediler her Pazartesi sıfırlansın mı.",
    "BACKUP_PRONUNCIATIONS": "Telaffuz ses dosyalarını yedekle.",
    "KIOSK_MODE": "Kiosk modu: uygulama kapanınca otomatik yeniden açılır.",
    "BYPASS_SHORTCUTS": "Alt+Tab / Windows tuşu gibi kaçış kısayollarını engelle.",
}


# --------------------------------------------------------------------------
# JSON helpers
# --------------------------------------------------------------------------

def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_words_raw() -> list:
    data = _load_json(WORDS_FILE, [])
    return data if isinstance(data, list) else []


def _remove_progress(target: str):
    prog = _load_json(PROGRESS_FILE, {})
    if isinstance(prog, dict) and target in prog:
        prog.pop(target)
        _save_json(PROGRESS_FILE, prog)


def _rename_progress(old_target: str, new_target: str):
    prog = _load_json(PROGRESS_FILE, {})
    if isinstance(prog, dict) and old_target in prog:
        prog[new_target] = prog.pop(old_target)
        _save_json(PROGRESS_FILE, prog)


# --------------------------------------------------------------------------
# Textual UI
# --------------------------------------------------------------------------

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (Button, DataTable, Digits, Footer, Header,
                             Input, Select, Static, Switch, TabbedContent,
                             TabPane)
from rich.markup import escape
from rich.text import Text


class LoginScreen(Screen):
    """Opaque password gate shown over the admin UI. 3 attempts, then exit."""

    BINDINGS = [Binding("escape", "app.quit", "Çıkış")]

    def __init__(self, password: str):
        super().__init__()
        self._password = password
        self._attempts = 3

    def compose(self) -> ComposeResult:
        with Vertical(id="login-box"):
            yield Static(f"[bold {YELLOW}]🔒 Coalide Admin Paneli[/]")
            yield Static(f"[{MUTED}]Devam etmek için admin şifresini girin.[/]")
            yield Input(password=True, placeholder="Admin şifresi", id="login-input")
            yield Static("", id="login-msg")

    def on_mount(self) -> None:
        self.query_one("#login-input", Input).focus()

    @on(Input.Submitted, "#login-input")
    def _check(self, event: Input.Submitted) -> None:
        if event.value == self._password:
            self.app.pop_screen()
            self.app.notify("Hoş geldiniz! Admin paneli açıldı.",
                            title="🔓 Giriş başarılı", timeout=4)
            return
        self._attempts -= 1
        if self._attempts <= 0:
            self.app.exit(message="Yanlış şifre. Erişim reddedildi.")
            return
        self.query_one("#login-msg", Static).update(
            f"[{RED}]Yanlış şifre. {self._attempts} deneme hakkı kaldı.[/]")
        event.input.value = ""


class ConfirmScreen(ModalScreen[bool]):
    """Simple Evet/Hayır confirmation dialog."""

    BINDINGS = [Binding("escape", "dismiss(False)", "Vazgeç")]

    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Static(self._message)
            with Horizontal(classes="dialog-buttons"):
                yield Button("Evet, sil", variant="error", id="confirm-yes")
                yield Button("Hayır", variant="default", id="confirm-no")

    @on(Button.Pressed, "#confirm-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-no")
    def _no(self) -> None:
        self.dismiss(False)


class WordFormScreen(ModalScreen[dict | None]):
    """Add/edit form for a single word. Dismisses with the word dict, or
    None if cancelled."""

    BINDINGS = [Binding("escape", "dismiss(None)", "İptal")]

    def __init__(self, word: dict | None = None):
        super().__init__()
        self._word = word or {}

    def compose(self) -> ComposeResult:
        w = self._word
        editing = bool(w)
        title = "✏️ Kelimeyi Düzenle" if editing else "➕ Yeni Kelime Ekle"
        current_type = (w.get("word_type") or "noun").strip().lower()
        types = list(WORD_TYPES)
        if current_type not in types:
            types.append(current_type)
        sentence = w.get("sentence") or ["", ""]

        with VerticalScroll(id="word-dialog"):
            yield Static(f"[bold {PURPLE}]{title}[/]")
            yield Static(f"[{MUTED}]Hedef kelime (öğrenilen dilde) *[/]", classes="f-label")
            yield Input(value=w.get("target", ""), placeholder="örn. run", id="f-target")
            yield Static(f"[{MUTED}]Anlamları — virgülle ayırın (kaynak dilde) *[/]", classes="f-label")
            yield Input(value=", ".join(w.get("source") or []),
                        placeholder="örn. koşmak, kaçmak", id="f-source")
            yield Static(f"[{MUTED}]Kelime türü[/]", classes="f-label")
            yield Select([(t.capitalize(), t) for t in types],
                         value=current_type, allow_blank=False, id="f-type")
            yield Static(f"[{MUTED}]Örnek cümle — boşluk kelimenin yerini gösterir[/]", classes="f-label")
            yield Input(value=sentence[0] if len(sentence) > 0 else "",
                        placeholder="Boşluktan ÖNCEKİ kısım, örn. He can", id="f-s1")
            yield Input(value=sentence[1] if len(sentence) > 1 else "",
                        placeholder="Boşluktan SONRAKİ kısım, örn. very fast", id="f-s2")
            yield Static(f"[{MUTED}]Geçmiş zaman (V2) — sadece fiiller için[/]", classes="f-label")
            yield Input(value=w.get("past", ""), placeholder="örn. ran", id="f-past")
            yield Static(f"[{MUTED}]Üçüncü hâl (V3) — sadece fiiller için[/]", classes="f-label")
            yield Input(value=w.get("v3", ""), placeholder="örn. run", id="f-v3")
            yield Static(f"[{MUTED}]Dil kodu (ISO 639)[/]", classes="f-label")
            yield Input(value=w.get("language", "en"), placeholder="en", id="f-lang")
            with Horizontal(classes="dialog-buttons"):
                yield Button("💾 Kaydet", variant="success", id="f-save")
                yield Button("İptal", variant="default", id="f-cancel")

    def _value(self, input_id: str) -> str:
        return self.query_one(f"#{input_id}", Input).value.strip()

    @on(Button.Pressed, "#f-save")
    def _save(self) -> None:
        target = self._value("f-target")
        source = [p.strip() for p in self._value("f-source").split(",") if p.strip()]
        if not target:
            self.app.notify("Hedef kelime boş olamaz.", title="⚠️ Eksik bilgi",
                            severity="error", timeout=4)
            return
        if not source:
            self.app.notify("En az bir anlam girmelisiniz.", title="⚠️ Eksik bilgi",
                            severity="error", timeout=4)
            return
        self.dismiss({
            "language": self._value("f-lang") or "en",
            "word_type": self.query_one("#f-type", Select).value,
            "sentence": [self._value("f-s1"), self._value("f-s2")],
            "target": target,
            "past": self._value("f-past"),
            "v3": self._value("f-v3"),
            "source": source,
            # Preserve scheduling info when editing an existing entry.
            "next_review_date": self._word.get("next_review_date"),
        })

    @on(Button.Pressed, "#f-cancel")
    def _cancel(self) -> None:
        self.dismiss(None)


class AdminApp(App):
    """Coalide admin panel TUI."""

    TITLE = "Coalide — Admin Paneli"
    BINDINGS = [Binding("q", "quit", "Çıkış")]

    CSS = f"""
    Screen {{ background: {BG}; }}
    Header {{ background: #1a1a2e; }}
    TabbedContent {{ height: 1fr; }}
    .tab-body {{ padding: 1 2; }}

    .tiles {{
        grid-size: 3;
        grid-gutter: 1 2;
        grid-rows: auto;
        height: auto;
        margin-bottom: 1;
    }}
    .tile {{
        background: {PANEL_BG};
        padding: 0 1;
        height: auto;
        align: center middle;
    }}
    .tile-label {{ width: 100%; text-align: center; color: {MUTED}; text-style: bold; }}
    .tile Digits {{ width: auto; }}
    .t-purple {{ border: round {PURPLE}; }}  .t-purple Digits {{ color: {PURPLE}; }}
    .t-green  {{ border: round {GREEN}; }}   .t-green Digits  {{ color: {GREEN}; }}
    .t-yellow {{ border: round {YELLOW}; }}  .t-yellow Digits {{ color: {YELLOW}; }}
    .t-red    {{ border: round {RED}; }}     .t-red Digits    {{ color: {RED}; }}

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

    /* Credits tab */
    .credit-form {{ height: auto; margin-top: 1; }}
    #credit-amount {{ width: 24; }}
    .credit-form Button {{ margin-left: 2; }}
    .quick-row {{ height: auto; margin-top: 1; }}
    .quick-row Button {{ margin-right: 1; min-width: 8; }}

    /* Config tab */
    .cfg-row {{
        height: auto;
        background: {PANEL_BG};
        border: round #2a2a4a;
        padding: 0 1;
        margin-bottom: 1;
    }}
    .cfg-text {{ width: 1fr; height: auto; padding: 0 1; }}
    Input.cfg-input {{ width: 44; }}
    Switch.cfg-input {{ width: auto; }}

    /* Words tab */
    .words-toolbar {{ height: auto; margin-bottom: 1; }}
    .words-toolbar Button {{ margin-right: 1; }}
    #word-count {{ width: 1fr; text-align: right; padding: 1 2; color: {MUTED}; }}
    #words-table {{ height: 1fr; background: {PANEL_BG}; }}

    /* Login */
    LoginScreen {{ align: center middle; background: {BG}; }}
    #login-box {{
        width: 60;
        height: auto;
        background: {PANEL_BG};
        border: round {PURPLE};
        padding: 2 4;
    }}
    #login-box Input {{ margin-top: 1; }}
    #login-msg {{ margin-top: 1; height: auto; }}

    /* Dialogs */
    WordFormScreen, ConfirmScreen {{ align: center middle; }}
    #word-dialog {{
        width: 76;
        height: auto;
        max-height: 90%;
        background: {PANEL_BG};
        border: round {PURPLE};
        padding: 1 2;
    }}
    .f-label {{ margin-top: 1; height: auto; }}
    #confirm-box {{
        width: 64;
        height: auto;
        background: {PANEL_BG};
        border: round {RED};
        padding: 1 2;
    }}
    .dialog-buttons {{ height: auto; margin-top: 1; }}
    .dialog-buttons Button {{ margin-right: 2; }}
    """

    def __init__(self, password: str, user):
        super().__init__()
        from utils import get_config
        self._password = password
        self.user = user
        self.config = get_config()
        self.words = load_words_raw()

    # ---- composition -----------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("💰 Krediler", id="tab-credits"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._compose_credits()
            with TabPane("⚙️ Ayarlar", id="tab-config"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._compose_config()
            with TabPane("🔤 Kelimeler", id="tab-words"):
                with Vertical(classes="tab-body"):
                    yield from self._compose_words()
        yield Footer(show_command_palette=False)

    def on_mount(self) -> None:
        table = self.query_one("#words-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Hedef", "Anlam", "Tür", "Cümle", "Past (V2)", "V3")
        self._refill_words_table()
        self.push_screen(LoginScreen(self._password))

    # ---- credits tab -----------------------------------------------------

    def _compose_credits(self) -> ComposeResult:
        from datetime import date
        today = date.today().isoformat()
        with Grid(classes="tiles"):
            with Vertical(classes="tile t-yellow"):
                yield Static("💵 Bakiye (kredi)", classes="tile-label")
                yield Digits(str(self.user.get_balance()), id="balance-digits")
            with Vertical(classes="tile t-purple"):
                yield Static("📺 Bugün Alınan (dk)", classes="tile-label")
                yield Digits(str(int(self.user.redeemed_minutes_by_date.get(today, 0))))
            with Vertical(classes="tile t-green"):
                yield Static("⏱ Alınabilir (dk, bugün)", classes="tile-label")
                yield Digits(str(self.user.max_redeemable_minutes()), id="max-digits")

        yield Static(self._credit_info_text(), classes="panel p-purple", id="credit-info")

        with Vertical(classes="panel p-green"):
            yield Static(f"[bold {GREEN}]Kredi Ekle / Çıkar[/]")
            yield Static(f"[{MUTED}]Miktarı yazıp Ekle veya Çıkar'a basın. "
                         f"Çıkarma en fazla mevcut bakiye kadar olur.[/]")
            with Horizontal(classes="credit-form"):
                yield Input(placeholder="Miktar", type="integer", id="credit-amount")
                yield Button("➕ Ekle", variant="success", id="btn-credit-add")
                yield Button("➖ Çıkar", variant="error", id="btn-credit-remove")
            yield Static(f"[{MUTED}]Hızlı ekle:[/]")
            with Horizontal(classes="quick-row"):
                for amt in (10, 25, 50, 100, 300):
                    yield Button(f"+{amt}", classes="quick-add", name=str(amt))

    def _credit_info_text(self) -> str:
        from datetime import date, timedelta
        lines = [f"[bold {PURPLE}]👤 {escape(self.user.username)}[/]"]
        if self.config.get("Credit_Reset_Weekly", True):
            days_left = 7 - date.today().weekday()
            reset_day = date.today() + timedelta(days=days_left)
            lines.append(f"[{MUTED}]Krediler her Pazartesi sıfırlanır — sonraki sıfırlama:[/] "
                         f"[bold {RED}]{reset_day.isoformat()}[/] "
                         f"[{MUTED}]({days_left} gün sonra)[/]")
        if self.user.last_reset_date:
            lines.append(f"[{MUTED}]Son sıfırlama:[/] {self.user.last_reset_date}")
        upcoming = {d: m for d, m in self.user.redeemed_minutes_by_date.items()
                    if d >= date.today().isoformat() and m}
        if upcoming:
            parts = ", ".join(f"{d}: [bold]{int(m)} dk[/]" for d, m in sorted(upcoming.items()))
            lines.append(f"[{MUTED}]Alınmış ekran süresi (bugün ve sonrası):[/] {parts}")
        return "\n".join(lines)

    def _refresh_credit_widgets(self) -> None:
        self.query_one("#balance-digits", Digits).update(str(self.user.get_balance()))
        self.query_one("#max-digits", Digits).update(str(self.user.max_redeemable_minutes()))
        self.query_one("#credit-info", Static).update(self._credit_info_text())

    def _parse_amount(self) -> int | None:
        raw = self.query_one("#credit-amount", Input).value.strip()
        try:
            amount = int(raw)
        except ValueError:
            amount = 0
        if amount <= 0:
            self.notify("Pozitif bir miktar girin.", title="⚠️ Geçersiz miktar",
                        severity="error", timeout=4)
            return None
        return amount

    def _add_credits(self, amount: int) -> None:
        self.user.add_credits(amount)  # add_credits saves the data
        self._refresh_credit_widgets()
        self.notify(f"{amount} kredi eklendi. Yeni bakiye: {self.user.get_balance()}",
                    title="✅ Kredi eklendi", timeout=4)

    @on(Button.Pressed, "#btn-credit-add")
    def _on_add(self) -> None:
        amount = self._parse_amount()
        if amount is not None:
            self._add_credits(amount)

    @on(Button.Pressed, "#btn-credit-remove")
    def _on_remove(self) -> None:
        from objects.balance_obj import save_data
        amount = self._parse_amount()
        if amount is None:
            return
        current = self.user.get_balance()
        removed = min(amount, current)
        if removed < amount:
            self.notify(f"Bakiye {current} olduğundan sadece {removed} kredi çıkarıldı.",
                        title="⚠️ Bakiye yetersiz", severity="warning", timeout=5)
        self.user.balance.balance -= removed
        save_data(self.user)
        self._refresh_credit_widgets()
        self.notify(f"{removed} kredi çıkarıldı. Yeni bakiye: {self.user.get_balance()}",
                    title="✅ Kredi çıkarıldı", timeout=4)

    @on(Button.Pressed, ".quick-add")
    def _on_quick_add(self, event: Button.Pressed) -> None:
        self._add_credits(int(event.button.name))

    # ---- config tab --------------------------------------------------------

    def _compose_config(self) -> ComposeResult:
        yield Static(f"[bold {YELLOW}]⚙️ config.json[/]\n"
                     f"[{MUTED}]Anahtarlar açılıp kapatıldığında hemen kaydedilir. "
                     f"Metin/sayı alanlarında değişikliği kaydetmek için Enter'a basın.[/]",
                     classes="panel p-yellow")
        for key, value in self.config.items():
            with Horizontal(classes="cfg-row"):
                with Vertical(classes="cfg-text"):
                    yield Static(f"[bold]{escape(key)}[/]")
                    desc = CONFIG_DESCRIPTIONS.get(key)
                    if desc:
                        yield Static(f"[{MUTED}]{desc}[/]")
                if isinstance(value, bool):
                    yield Switch(value=value, id=f"cfg-{key}", classes="cfg-input")
                else:
                    display = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                    yield Input(value=str(display), id=f"cfg-{key}", classes="cfg-input")

    def _save_config(self, key: str, new_value) -> None:
        self.config[key] = new_value
        _save_json(CONFIG_FILE, self.config)
        shown = new_value if isinstance(new_value, str) else json.dumps(new_value, ensure_ascii=False)
        self.notify(f"{key} = {shown}", title="✅ Ayar kaydedildi", timeout=4)

    @on(Switch.Changed)
    def _on_config_switch(self, event: Switch.Changed) -> None:
        if event.switch.id and event.switch.id.startswith("cfg-"):
            self._save_config(event.switch.id[4:], event.value)

    @on(Input.Submitted)
    def _on_config_input(self, event: Input.Submitted) -> None:
        if not (event.input.id and event.input.id.startswith("cfg-")):
            return
        key = event.input.id[4:]
        original = self.config.get(key)
        text = event.value.strip()
        try:
            if isinstance(original, (int, float)) and not isinstance(original, bool):
                new_value = int(text) if "." not in text else float(text)
            elif isinstance(original, str):
                new_value = text
            else:  # lists / dicts / null — edited as JSON
                new_value = json.loads(text)
        except (ValueError, json.JSONDecodeError):
            self.notify(f"'{text}' bu ayar için geçerli bir değer değil.",
                        title="⚠️ Kaydedilmedi", severity="error", timeout=5)
            return
        self._save_config(key, new_value)

    # ---- words tab ---------------------------------------------------------

    def _compose_words(self) -> ComposeResult:
        with Horizontal(classes="words-toolbar"):
            yield Button("➕ Kelime Ekle", variant="success", id="btn-word-add")
            yield Button("✏️ Düzenle", variant="primary", id="btn-word-edit")
            yield Button("🗑 Sil", variant="error", id="btn-word-delete")
            yield Static("", id="word-count")
        yield DataTable(id="words-table")

    def _refill_words_table(self) -> None:
        table = self.query_one("#words-table", DataTable)
        table.clear()
        for w in self.words:
            sentence = w.get("sentence") or ["", ""]
            s1 = sentence[0] if len(sentence) > 0 else ""
            s2 = sentence[1] if len(sentence) > 1 else ""
            full = f"{s1} ___ {s2}".strip()
            if len(full) > 42:
                full = full[:39] + "..."
            table.add_row(
                Text(w.get("target", "?"), style="bold"),
                Text(", ".join(w.get("source") or []), style=GREEN),
                Text(w.get("word_type", "?"), style=PURPLE),
                Text(full, style=MUTED),
                w.get("past", ""),
                w.get("v3", ""),
            )
        self.query_one("#word-count", Static).update(f"{len(self.words)} kelime")

    def _save_words(self) -> None:
        _save_json(WORDS_FILE, self.words)
        self._refill_words_table()

    def _selected_word_index(self) -> int | None:
        table = self.query_one("#words-table", DataTable)
        if not self.words or table.row_count == 0:
            self.notify("Kayıtlı kelime yok.", title="⚠️", severity="warning", timeout=4)
            return None
        idx = table.cursor_row
        if idx is None or not (0 <= idx < len(self.words)):
            self.notify("Önce tablodan bir kelime seçin.", title="⚠️",
                        severity="warning", timeout=4)
            return None
        return idx

    def _is_duplicate(self, word: dict, skip_index: int | None = None) -> bool:
        for i, w in enumerate(self.words):
            if i == skip_index:
                continue
            if (w.get("target", "").strip().lower() == word["target"].strip().lower()
                    and w.get("language") == word["language"]):
                return True
        return False

    @on(Button.Pressed, "#btn-word-add")
    def _on_word_add(self) -> None:
        def handle(result: dict | None) -> None:
            if result is None:
                return
            if self._is_duplicate(result):
                self.notify(f"'{result['target']}' zaten kayıtlı.",
                            title="⚠️ Eklenmedi", severity="error", timeout=5)
                return
            self.words.append(result)
            self._save_words()
            self.notify(f"'{result['target']}' eklendi. Toplam {len(self.words)} kelime.",
                        title="✅ Kelime eklendi", timeout=4)
        self.push_screen(WordFormScreen(), handle)

    @on(Button.Pressed, "#btn-word-edit")
    def _on_word_edit(self) -> None:
        idx = self._selected_word_index()
        if idx is None:
            return
        old = self.words[idx]

        def handle(result: dict | None) -> None:
            if result is None:
                return
            if self._is_duplicate(result, skip_index=idx):
                self.notify(f"'{result['target']}' zaten kayıtlı.",
                            title="⚠️ Kaydedilmedi", severity="error", timeout=5)
                return
            old_target = old.get("target", "")
            if old_target and old_target != result["target"]:
                # Keep the SM-2 progress attached to the renamed word.
                _rename_progress(old_target, result["target"])
            self.words[idx] = result
            self._save_words()
            self.notify(f"'{result['target']}' güncellendi.",
                        title="✅ Kelime güncellendi", timeout=4)
        self.push_screen(WordFormScreen(old), handle)

    @on(Button.Pressed, "#btn-word-delete")
    def _on_word_delete(self) -> None:
        idx = self._selected_word_index()
        if idx is None:
            return
        target = self.words[idx].get("target", "?")

        def handle(confirmed: bool | None) -> None:
            if not confirmed:
                return
            del self.words[idx]
            self._save_words()
            _remove_progress(target)
            self.notify(f"'{target}' silindi. Kalan: {len(self.words)} kelime.",
                        title="🗑 Kelime silindi", timeout=4)
        self.push_screen(ConfirmScreen(
            f"[bold {RED}]'{escape(target)}'[/] kelimesi silinsin mi?\n\n"
            f"[{MUTED}]Kelimeyle birlikte ilerleme (SM-2) kaydı da silinir. "
            f"Bu işlem geri alınamaz.[/]"), handle)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    from dotenv import load_dotenv

    load_dotenv()
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_password:
        print("Admin Mode is not password-protected. Set ADMIN_PASSWORD in the "
              ".env file to enable it. Access denied.")
        return

    from utils import get_current_user
    from objects.balance_obj import load_data

    user = load_data(get_current_user())
    result = AdminApp(admin_password, user).run()
    if result:
        print(result)


if __name__ == "__main__":
    main()

"""
Coalide — İstatistik Ekranı

A Textual TUI showing detailed learning statistics:
  - Overview tiles (words started/mastered, streak, credits, success rate...)
  - Weekly/daily "new words learned" bar charts (from progress.json
    first_review_date)
  - Daily answers (correct/wrong/blank) charts + all-time totals, read from
    statistics.csv — a per-answer log this module also writes via
    record_answer(), which new_master.py calls after every evaluated answer.
  - Per-word table (hardest first), upcoming review forecast, SM-2 health.

Run standalone:  python stats_menu.py
From the menu:   the "İstatistikler" button launches it as a subprocess.
"""

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
WORDS_FILE = os.path.join(BASE_DIR, "words.json")
STATS_LOG = os.path.join(BASE_DIR, "statistics.csv")
CURRENT_USER_FILE = os.path.join(BASE_DIR, "current_user.json")

TR_MONTHS = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

# Palette — matches menu.py
BG = "#0f0f1a"
PANEL_BG = "#16162a"
PURPLE = "#7c5cff"
GREEN = "#42d6a4"
YELLOW = "#f5c542"
RED = "#ff6b81"
MUTED = "#9a9ac0"

MATURE_INTERVAL = 21  # days; a word with an SM-2 interval this long counts as "learned"


# --------------------------------------------------------------------------
# Answer log (statistics.csv) — stdlib only, safe to import from new_master
# --------------------------------------------------------------------------

def record_answer(word: str, result) -> None:
    """
    Append one answered question to statistics.csv.
    :param word: the target word that was asked.
    :param result: True (correct), False (wrong) or None (left blank).
    Never raises — a stats logging failure must not break the quiz.
    """
    try:
        res = "correct" if result is True else "wrong" if result is False else "blank"
        is_new = not os.path.exists(STATS_LOG)
        with open(STATS_LOG, "a", encoding="utf-8") as f:
            if is_new:
                f.write("datetime,word,result\n")
            f.write(f"{datetime.now().isoformat(timespec='seconds')},{word},{res}\n")
    except Exception:
        pass


# --------------------------------------------------------------------------
# Data loading & aggregation
# --------------------------------------------------------------------------

def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def _parse_date(s):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def load_log() -> list:
    """Read statistics.csv -> list of (date, word, result) tuples."""
    rows = []
    if not os.path.exists(STATS_LOG):
        return rows
    try:
        with open(STATS_LOG, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) < 3 or parts[0].startswith("datetime"):
                    continue
                d = _parse_date(parts[0][:10])
                if d is None:
                    continue
                rows.append((d, parts[1], parts[2]))
    except Exception:
        pass
    return rows


def load_user_data() -> dict:
    """Read <username>_data.json directly (no prompts, no heavy imports)."""
    cu = _load_json(CURRENT_USER_FILE, {})
    username = cu.get("username") if isinstance(cu, dict) else None
    if not username:
        return {}
    data = _load_json(os.path.join(BASE_DIR, f"{username}_data.json"), {})
    return data if isinstance(data, dict) else {}


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _day_label(d: date) -> str:
    return f"{d.day} {TR_MONTHS[d.month - 1]}"


def build_stats() -> dict:
    today = date.today()
    progress = _load_json(PROGRESS_FILE, {})
    words = _load_json(WORDS_FILE, [])
    if not isinstance(words, list):
        words = []
    log = load_log()
    user = load_user_data()

    # ---- per-word state ----
    started = []
    for target, p in progress.items():
        if not isinstance(p, dict):
            continue
        attempts = p.get("last_ten_attempts") or []
        total = len(attempts) or p.get("total_attempts", 0)
        correct = p.get("correct_attempts", 0)
        wrong = p.get("wrong_attempts", 0)
        blank = p.get("blank_attempts", 0)
        started.append({
            "word": target,
            "rate": (correct / total * 100) if total else 0.0,
            "total": total, "correct": correct, "wrong": wrong, "blank": blank,
            "repetitions": p.get("repetitions", 0),
            "ease": p.get("ease_factor", 2.5),
            "interval": p.get("interval", 0),
            "first": _parse_date(p.get("first_review_date")),
            "last": _parse_date(p.get("last_review_date")),
            "next": _parse_date(p.get("next_review_date")),
        })

    total_words = len(words)
    started_count = len(started)
    not_started = max(0, total_words - started_count)
    mastered = sum(1 for e in started if e["interval"] >= MATURE_INTERVAL)

    # ---- maturity buckets (Anki-style) ----
    buckets = [
        ("Başlanmadı", not_started, MUTED),
        ("Yeni  (≤1 gün)", sum(1 for e in started if e["interval"] <= 1), RED),
        ("Öğreniliyor (2-6g)", sum(1 for e in started if 2 <= e["interval"] <= 6), YELLOW),
        ("Genç  (1-3 hafta)", sum(1 for e in started if 7 <= e["interval"] < MATURE_INTERVAL), PURPLE),
        ("Olgun (3h - 2 ay)", sum(1 for e in started if MATURE_INTERVAL <= e["interval"] < 60), GREEN),
        ("Usta  (2 ay +)", sum(1 for e in started if e["interval"] >= 60), GREEN),
    ]

    # ---- new words per day / per week ----
    new_dates = [e["first"] for e in started if e["first"]]
    new_by_day = Counter(new_dates)
    new_today = new_by_day.get(today, 0)

    weekly_new = []
    ws0 = _week_start(today)
    for i in range(7, -1, -1):
        ws = ws0 - timedelta(weeks=i)
        cnt = sum(1 for d in new_dates if ws <= d < ws + timedelta(days=7))
        label = f"{_day_label(ws)} +" if ws != ws0 else "Bu hafta"
        weekly_new.append((label, cnt, GREEN if cnt else MUTED))

    daily_new = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        cnt = new_by_day.get(d, 0)
        daily_new.append((_day_label(d), cnt, PURPLE if cnt else MUTED))

    # ---- answers from the log ----
    answers_by_day = {}
    for d, _w, res in log:
        answers_by_day.setdefault(d, Counter())[res] += 1
    log_totals = Counter(res for _d, _w, res in log)

    daily_answers = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        c = answers_by_day.get(d, Counter())
        daily_answers.append((_day_label(d), [
            (c.get("correct", 0), GREEN),
            (c.get("wrong", 0), RED),
            (c.get("blank", 0), YELLOW),
        ]))

    spark_30 = [sum(answers_by_day.get(today - timedelta(days=i), Counter()).values())
                for i in range(29, -1, -1)]
    spark_new_30 = [new_by_day.get(today - timedelta(days=i), 0)
                    for i in range(29, -1, -1)]

    # ---- streak ----
    active_days = set(answers_by_day)
    for e in started:
        for k in ("first", "last"):
            if e[k]:
                active_days.add(e[k])
    streak = 0
    d = today if today in active_days else today - timedelta(days=1)
    while d in active_days:
        streak += 1
        d -= timedelta(days=1)

    # ---- all-time ----
    log_total = sum(log_totals.values())
    son10 = Counter()
    for e in started:
        son10["correct"] += e["correct"]
        son10["wrong"] += e["wrong"]
        son10["blank"] += e["blank"]
    son10_total = sum(son10.values())

    if log_total:
        overall_rate = log_totals.get("correct", 0) / log_total * 100
    elif son10_total:
        overall_rate = son10["correct"] / son10_total * 100
    else:
        overall_rate = 0.0

    best_day = max(answers_by_day.items(), key=lambda kv: sum(kv[1].values()), default=None)
    first_log = min((d for d, _w, _r in log), default=None)

    # ---- review forecast ----
    overdue = sum(1 for e in started if e["next"] and e["next"] < today)
    forecast = [("Gecikmiş", overdue, RED)]
    for i in range(14):
        d = today + timedelta(days=i)
        cnt = sum(1 for e in started if e["next"] == d)
        label = "Bugün" if i == 0 else "Yarın" if i == 1 else _day_label(d)
        forecast.append((label, cnt, YELLOW if i == 0 else PURPLE if cnt else MUTED))

    # ---- SM-2 health ----
    eases = [e["ease"] for e in started]
    intervals = [e["interval"] for e in started]
    longest = max(started, key=lambda e: e["interval"], default=None)

    # ---- hardest words / table ----
    attempted = [e for e in started if e["total"] > 0]
    hardest = sorted(attempted, key=lambda e: (e["rate"], -e["wrong"]))[:5]
    table_rows = sorted(started, key=lambda e: (e["rate"], -e["wrong"]))

    # ---- word types ----
    word_types = Counter((w.get("word_type") or "?").strip().lower() or "?"
                         for w in words if isinstance(w, dict))

    # ---- screen time / credits ----
    redeemed = {}
    for k, v in (user.get("redeemed_minutes_by_date") or {}).items():
        pd = _parse_date(k)
        if pd and isinstance(v, (int, float)):
            redeemed[pd] = v
    redeemed_14 = []
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        m = redeemed.get(d, 0)
        redeemed_14.append((_day_label(d), m, YELLOW if m else MUTED))

    return {
        "today": today,
        "total_words": total_words,
        "started_count": started_count,
        "mastered": mastered,
        "new_today": new_today,
        "due_now": overdue + sum(1 for e in started if e["next"] == today),
        "streak": streak,
        "buckets": buckets,
        "weekly_new": weekly_new,
        "daily_new": daily_new,
        "daily_answers": daily_answers,
        "spark_30": spark_30,
        "spark_new_30": spark_new_30,
        "log_totals": log_totals,
        "log_total": log_total,
        "son10": son10,
        "son10_total": son10_total,
        "overall_rate": overall_rate,
        "best_day": best_day,
        "first_log": first_log,
        "active_day_count": len(answers_by_day),
        "forecast": forecast,
        "eases": eases,
        "intervals": intervals,
        "longest": longest,
        "hardest": hardest,
        "table_rows": table_rows,
        "word_types": word_types,
        "balance": user.get("balance"),
        "redeemed_14": redeemed_14,
        "redeemed_total": sum(redeemed.values()),
    }


# --------------------------------------------------------------------------
# Chart rendering (Rich markup strings)
# --------------------------------------------------------------------------

_PARTIALS = " ▏▎▍▌▋▊▉"


def _bar(width_cells: float, max_width: int) -> str:
    full = int(width_cells)
    frac = width_cells - full
    bar = "█" * min(full, max_width)
    if full < max_width and frac >= 1 / 8:
        bar += _PARTIALS[int(frac * 8)]
    return bar


def hbar_chart(rows, width: int = 30, label_w: int = 10) -> str:
    """rows: list of (label, value, color) -> horizontal bar chart markup."""
    vmax = max((v for _l, v, _c in rows), default=0)
    lines = []
    for label, v, color in rows:
        w = 0 if vmax == 0 else v / vmax * width
        bar = _bar(w, width)
        if v > 0 and not bar:
            bar = "▏"
        lines.append(f"[{MUTED}]{label:<{label_w}}[/] [{color}]{bar}[/] [bold]{v}[/]")
    return "\n".join(lines) if lines else f"[dim]Henüz veri yok.[/]"


def stacked_chart(rows, width: int = 28, label_w: int = 8) -> str:
    """rows: list of (label, [(value, color), ...]) -> stacked bar chart."""
    vmax = max((sum(v for v, _c in parts) for _l, parts in rows), default=0)
    lines = []
    for label, parts in rows:
        total = sum(v for v, _c in parts)
        segs, detail = "", []
        if total and vmax:
            bar_w = round(total / vmax * width)
            prev = cum = 0
            for v, color in parts:
                if v <= 0:
                    continue
                cum += v
                edge = round(cum / total * bar_w)
                if edge > prev:
                    segs += f"[{color}]{'█' * (edge - prev)}[/]"
                prev = edge
        for (v, color), sym in zip(parts, ("✓", "✗", "∅")):
            if v:
                detail.append(f"[{color}]{v}{sym}[/]")
        tail = f" [bold]{total}[/] " + " ".join(detail) if total else f" [dim]0[/]"
        lines.append(f"[{MUTED}]{label:<{label_w}}[/] {segs}{tail}")
    return "\n".join(lines) if lines else "[dim]Henüz veri yok.[/]"


def rate_color(rate: float) -> str:
    return GREEN if rate >= 80 else YELLOW if rate >= 50 else RED


# --------------------------------------------------------------------------
# Textual UI
# --------------------------------------------------------------------------

from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical, VerticalScroll
from textual.widgets import (DataTable, Digits, Footer, Header, Sparkline,
                             Static, TabbedContent, TabPane)


class WordTable(DataTable):
    """All tracked words, hardest first. Populated on mount so a recompose
    (refresh) rebuilds it with fresh data."""

    def __init__(self, rows, today):
        super().__init__(id="word-table")
        self._rows = rows
        self._today = today

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Kelime", "Başarı", "✓", "✗", "∅",
                         "Tekrar", "Aralık", "Sonraki Tekrar")
        for e in self._rows:
            rc = rate_color(e["rate"])
            if e["next"]:
                delta = (e["next"] - self._today).days
                nxt = Text(f"{e['next'].isoformat()}  ({delta:+d}g)",
                           style=RED if delta <= 0 else MUTED)
            else:
                nxt = Text("—", style=MUTED)
            self.add_row(
                Text(e["word"], style="bold"),
                Text(f"%{e['rate']:.0f}", style=f"bold {rc}") if e["total"]
                else Text("—", style=MUTED),
                Text(str(e["correct"]), style=GREEN),
                Text(str(e["wrong"]), style=RED),
                Text(str(e["blank"]), style=YELLOW),
                Text(str(e["repetitions"])),
                Text(f"{e['interval']}g"),
                nxt,
            )


class StatsApp(App):
    """Coalide statistics TUI."""

    TITLE = "Coalide — İstatistikler"
    BINDINGS = [
        Binding("q,escape", "quit", "Çıkış"),
        Binding("r", "refresh_stats", "Yenile"),
    ]

    CSS = f"""
    Screen {{ background: {BG}; }}
    Header {{ background: #1a1a2e; }}
    TabbedContent {{ height: 1fr; }}
    .tab-body {{ padding: 1 2; }}

    #tiles {{
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

    Sparkline {{ height: 2; margin-top: 1; }}
    Sparkline > .sparkline--max-color {{ color: {GREEN}; }}
    Sparkline > .sparkline--min-color {{ color: #2a2a4a; }}

    #word-table {{ height: 1fr; background: {PANEL_BG}; }}
    """

    # ---- composition ----------------------------------------------------

    def compose(self) -> ComposeResult:
        s = build_stats()
        yield Header(show_clock=True)
        with TabbedContent():
            with TabPane("📊 Genel Bakış", id="tab-genel"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._genel(s)
            with TabPane("📅 Haftalık & Günlük", id="tab-hafta"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._haftalik(s)
            with TabPane("🔤 Kelimeler", id="tab-kelime"):
                with Vertical(classes="tab-body"):
                    yield from self._kelimeler(s)
            with TabPane("🔮 Gelecek & SM-2", id="tab-gelecek"):
                with VerticalScroll(classes="tab-body"):
                    yield from self._gelecek(s)
        yield Footer(show_command_palette=False)

    @staticmethod
    def _panel(title: str, body: str, accent_class: str, accent: str) -> Static:
        return Static(f"[bold {accent}]{title}[/]\n\n{body}",
                      classes=f"panel {accent_class}")

    def _genel(self, s) -> ComposeResult:
        balance = s["balance"] if isinstance(s["balance"], (int, float)) else 0
        tiles = [
            ("📚 Toplam Kelime", s["total_words"], "t-purple"),
            ("🚀 Başlanan", s["started_count"], "t-green"),
            (f"🏆 Öğrenilen ({MATURE_INTERVAL}g+)", s["mastered"], "t-yellow"),
            ("✨ Bugün Yeni", s["new_today"], "t-green"),
            ("⏰ Tekrar Bekleyen", s["due_now"], "t-red"),
            ("🔥 Seri (gün)", s["streak"], "t-yellow"),
            ("💬 Toplam Cevap", s["log_total"] or s["son10_total"], "t-purple"),
            ("🎯 Başarı (%)", round(s["overall_rate"]), "t-green"),
            ("💵 Kredi", balance, "t-yellow"),
        ]
        with Grid(id="tiles"):
            for label, value, klass in tiles:
                with Vertical(classes=f"tile {klass}"):
                    yield Static(label, classes="tile-label")
                    yield Digits(str(value))

        yield self._panel("📦 Kelime Durumu (SM-2 olgunluk)",
                          hbar_chart(s["buckets"], label_w=20),
                          "p-purple", PURPLE)

        if s["hardest"]:
            lines = []
            for e in s["hardest"]:
                rc = rate_color(e["rate"])
                lines.append(
                    f"[bold]{escape(e['word']):<16}[/] [{rc}]%{e['rate']:.0f}[/]  "
                    f"([{GREEN}]{e['correct']}✓[/] [{RED}]{e['wrong']}✗[/] "
                    f"[{YELLOW}]{e['blank']}∅[/])"
                )
            yield self._panel("🧗 En Zor 5 Kelime", "\n".join(lines), "p-red", RED)

        yield self._panel("♾️ Tüm Zamanlar", self._alltime_text(s), "p-green", GREEN)

        body = hbar_chart(s["redeemed_14"], label_w=8)
        body += (f"\n\n[{MUTED}]Toplam kullanılan ekran süresi:[/] "
                 f"[bold {YELLOW}]{s['redeemed_total']} dk[/]")
        yield self._panel("🖥️ Ekran Süresi (son 14 gün, dakika)", body,
                          "p-yellow", YELLOW)

    @staticmethod
    def _alltime_text(s) -> str:
        lt = s["log_totals"]
        lines = []
        if s["log_total"]:
            lines.append(
                f"Toplam cevap: [bold]{s['log_total']}[/]  "
                f"([{GREEN}]{lt.get('correct', 0)}✓[/] [{RED}]{lt.get('wrong', 0)}✗[/] "
                f"[{YELLOW}]{lt.get('blank', 0)}∅[/])"
            )
            lines.append(f"Genel başarı: [bold {rate_color(s['overall_rate'])}]"
                         f"%{s['overall_rate']:.1f}[/]")
            lines.append(f"Çalışılan gün: [bold]{s['active_day_count']}[/]")
            if s["best_day"]:
                d, c = s["best_day"]
                lines.append(f"En yoğun gün: [bold]{_day_label(d)}[/] "
                             f"({sum(c.values())} cevap)")
            if s["active_day_count"]:
                avg = s["log_total"] / s["active_day_count"]
                lines.append(f"Aktif gün ortalaması: [bold]{avg:.1f}[/] cevap")
            if s["first_log"]:
                lines.append(f"Kayıt başlangıcı: [bold]{s['first_log'].isoformat()}[/]")
        else:
            lines.append(f"[{MUTED}]Cevap geçmişi bu sürümle kaydedilmeye başlandı — "
                         f"quiz çözdükçe burada birikecek.[/]")
        s10 = s["son10"]
        lines.append("")
        lines.append(
            f"[{MUTED}]Kelime bazlı (son 10 pencere):[/] "
            f"[{GREEN}]{s10['correct']}✓[/] [{RED}]{s10['wrong']}✗[/] "
            f"[{YELLOW}]{s10['blank']}∅[/]  (toplam {s['son10_total']})"
        )
        return "\n".join(lines)

    def _haftalik(self, s) -> ComposeResult:
        yield self._panel("🌱 Haftalık Yeni Kelimeler (son 8 hafta)",
                          hbar_chart(s["weekly_new"], label_w=10),
                          "p-green", GREEN)
        yield self._panel("✨ Günlük Yeni Kelimeler (son 14 gün)",
                          hbar_chart(s["daily_new"], label_w=8),
                          "p-purple", PURPLE)
        legend = (f"[{GREEN}]█ Doğru[/]  [{RED}]█ Yanlış[/]  [{YELLOW}]█ Boş[/]\n\n")
        yield self._panel("💬 Günlük Cevaplar (son 14 gün)",
                          legend + stacked_chart(s["daily_answers"]),
                          "p-yellow", YELLOW)
        with Vertical(classes="panel p-green"):
            yield Static(f"[bold {GREEN}]⚡ Aktivite — son 30 gün "
                         f"(günlük cevap sayısı)[/]")
            yield Sparkline(s["spark_30"], summary_function=max)
        with Vertical(classes="panel p-purple"):
            yield Static(f"[bold {PURPLE}]🌱 Yeni kelime — son 30 gün[/]")
            yield Sparkline(s["spark_new_30"], summary_function=max)

    def _kelimeler(self, s) -> ComposeResult:
        types = [(t, c, PURPLE) for t, c in s["word_types"].most_common()]
        yield self._panel("🏷️ Kelime Türleri", hbar_chart(types, label_w=12),
                          "p-purple", PURPLE)
        yield Static(f"[bold {GREEN}]🔤 Tüm Kelimeler — en zordan kolaya "
                     f"({s['started_count']} başlanan)[/]", classes="panel p-green")
        yield WordTable(s["table_rows"], s["today"])

    def _gelecek(self, s) -> ComposeResult:
        yield self._panel("🔮 Tekrar Takvimi (gelecek 14 gün)",
                          hbar_chart(s["forecast"], label_w=9),
                          "p-purple", PURPLE)
        lines = []
        if s["eases"]:
            avg_e = sum(s["eases"]) / len(s["eases"])
            avg_i = sum(s["intervals"]) / len(s["intervals"])
            lines.append(f"Ortalama kolaylık faktörü (EF): [bold]{avg_e:.2f}[/]  "
                         f"[{MUTED}](1.30 = en zor, 2.50 = varsayılan)[/]")
            lines.append(f"En düşük EF: [bold]{min(s['eases']):.2f}[/]   "
                         f"En yüksek EF: [bold]{max(s['eases']):.2f}[/]")
            lines.append(f"Ortalama tekrar aralığı: [bold]{avg_i:.0f} gün[/]")
            if s["longest"]:
                lines.append(f"En uzun aralık: [bold]{escape(s['longest']['word'])}[/] "
                             f"([{GREEN}]{s['longest']['interval']} gün[/])")
        else:
            lines.append(f"[{MUTED}]Henüz çalışılmış kelime yok.[/]")
        yield self._panel("🧠 SM-2 Sağlığı", "\n".join(lines), "p-green", GREEN)

    # ---- actions ---------------------------------------------------------

    def action_refresh_stats(self) -> None:
        self.refresh(recompose=True)
        self.notify("İstatistikler yenilendi.", title="🔄 Yenile", timeout=3)


def main():
    StatsApp().run()


if __name__ == "__main__":
    main()

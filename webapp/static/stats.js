/* Coalide — statistics dashboard renderer.
   Ports the terminal İstatistikler screen (stats_menu.py) to the browser:
   six sub-tabs (Genel / Krediler / Haftalık & Günlük / Süre & Hız /
   Kelimeler / Gelecek). */
(function () {
    "use strict";

    const COLORS = { muted: "var(--muted)", red: "var(--red)", yellow: "var(--yellow)",
                     purple: "var(--purple)", green: "var(--green)" };
    const col = (t) => COLORS[t] || "var(--muted)";

    let payload = null;
    let activeSub = "genel";

    // --- tiny DOM helpers ---
    function h(tag, cls, html) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html != null) e.innerHTML = html;
        return e;
    }
    function esc(s) {
        return String(s).replace(/[&<>"']/g, (c) => (
            { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }

    function tile(label, value, token) {
        const t = h("div", "stat-tile stat-" + (token || "purple"));
        t.appendChild(h("span", "stat-tile-num", esc(value)));
        t.appendChild(h("span", "stat-tile-label", esc(label)));
        return t;
    }
    function tiles(list) {
        const g = h("div", "stat-tiles");
        list.forEach(([l, v, t]) => g.appendChild(tile(l, v, t)));
        return g;
    }

    function panel(title, token, bodyNode) {
        const p = h("div", "stat-panel panel-" + (token || "purple"));
        p.appendChild(h("h3", "stat-panel-title", esc(title)));
        if (bodyNode) p.appendChild(bodyNode);
        return p;
    }

    // horizontal bar chart from [{label,value,color}]
    function hbar(rows) {
        const wrap = h("div", "hbar");
        const max = Math.max(0, ...rows.map((r) => r.value));
        if (!rows.length) return h("p", "muted", "Henüz veri yok.");
        rows.forEach((r) => {
            const row = h("div", "hbar-row");
            row.appendChild(h("span", "hbar-label", esc(r.label)));
            const track = h("span", "hbar-track");
            const pct = max ? Math.max(r.value > 0 ? 2 : 0, (r.value / max) * 100) : 0;
            const fill = h("span", "hbar-fill");
            fill.style.width = pct + "%";
            fill.style.background = col(r.color);
            track.appendChild(fill);
            row.appendChild(track);
            row.appendChild(h("span", "hbar-val", esc(r.value)));
            wrap.appendChild(row);
        });
        return wrap;
    }

    // stacked bar chart from [{label, parts:[{value,color}]}]
    function stacked(rows) {
        const wrap = h("div", "hbar");
        const totals = rows.map((r) => r.parts.reduce((a, p) => a + p.value, 0));
        const max = Math.max(0, ...totals);
        const syms = ["✓", "✗", "∅"];
        rows.forEach((r, i) => {
            const total = totals[i];
            const row = h("div", "hbar-row");
            row.appendChild(h("span", "hbar-label", esc(r.label)));
            const track = h("span", "hbar-track");
            const totalPct = max ? (total / max) * 100 : 0;
            r.parts.forEach((p) => {
                if (p.value <= 0) return;
                const seg = h("span", "hbar-seg");
                seg.style.width = (total ? (p.value / total) * totalPct : 0) + "%";
                seg.style.background = col(p.color);
                track.appendChild(seg);
            });
            row.appendChild(track);
            const detail = r.parts.map((p, j) => p.value
                ? `<span style="color:${col(p.color)}">${p.value}${syms[j]}</span>` : "")
                .filter(Boolean).join(" ");
            row.appendChild(h("span", "hbar-val", `${total} ${detail}`));
            wrap.appendChild(row);
        });
        return wrap;
    }

    // mini bar sparkline as inline SVG
    function sparkline(values, token) {
        const w = 320, ht = 44, n = values.length || 1, max = Math.max(1, ...values);
        const bw = w / n;
        const bars = values.map((v, i) => {
            const bh = (v / max) * (ht - 4);
            return `<rect x="${(i * bw).toFixed(1)}" y="${(ht - bh).toFixed(1)}" `
                 + `width="${Math.max(1, bw - 1.5).toFixed(1)}" height="${bh.toFixed(1)}" `
                 + `rx="1" fill="${col(token)}"></rect>`;
        }).join("");
        const svg = h("div", "sparkline");
        svg.innerHTML = `<svg viewBox="0 0 ${w} ${ht}" preserveAspectRatio="none" width="100%" height="${ht}">${bars}</svg>`;
        return svg;
    }

    function rateColor(rate) {
        return rate >= 80 ? "green" : rate >= 50 ? "yellow" : "red";
    }

    // seconds -> "2 sa 5 dk" / "3 dk 20 sn" / "45 sn"
    function fmtDur(secs) {
        const total = Math.max(0, Math.round(+secs || 0));
        const hr = Math.floor(total / 3600), mn = Math.floor((total % 3600) / 60), sc = total % 60;
        if (hr) return mn ? `${hr} sa ${mn} dk` : `${hr} sa`;
        if (mn) return sc ? `${mn} dk ${sc} sn` : `${mn} dk`;
        return `${sc} sn`;
    }
    const toMin = (secs) => Math.round((+secs || 0) / 60);

    // ---------------------------------------------------------------- tabs
    function section(s) {
        return {
            genel: genel, krediler: krediler, haftalik: haftalik,
            sure: sure, kelimeler: kelimeler, gelecek: gelecek,
        }[activeSub](s);
    }

    function genel(s) {
        const frag = document.createDocumentFragment();
        frag.appendChild(tiles([
            ["📚 Toplam Kelime", s.total_words, "purple"],
            ["🚀 Başlanan", s.started_count, "green"],
            ["🏆 Öğrenilen (21g+)", s.mastered, "yellow"],
            ["✨ Bugün Yeni", s.new_today, "green"],
            ["⏰ Tekrar Bekleyen", s.due_now, "red"],
            ["🔥 Seri (gün)", s.streak, "yellow"],
            ["💬 Toplam Cevap", s.log_total || s.son10_total, "purple"],
            ["🎯 Başarı (%)", Math.round(s.overall_rate), "green"],
            ["💵 Kredi", s.balance, "yellow"],
        ]));
        frag.appendChild(panel("📦 Kelime Durumu (SM-2 olgunluk)", "purple", hbar(s.buckets)));

        if (s.hardest && s.hardest.length) {
            const body = h("div", "text-lines");
            s.hardest.forEach((e) => {
                body.appendChild(h("div", null,
                    `<b>${esc(e.word)}</b> <span style="color:${col(rateColor(e.rate))}">%${Math.round(e.rate)}</span> `
                    + `<span class="muted">(<span style="color:${col("green")}">${e.correct}✓</span> `
                    + `<span style="color:${col("red")}">${e.wrong}✗</span> `
                    + `<span style="color:${col("yellow")}">${e.blank}∅</span>)</span>`));
            });
            frag.appendChild(panel("🧗 En Zor 5 Kelime", "red", body));
        }

        frag.appendChild(panel("♾️ Tüm Zamanlar", "green", allTime(s)));
        return frag;
    }

    function allTime(s) {
        const body = h("div", "text-lines");
        const lt = s.log_totals || {};
        if (s.log_total) {
            body.appendChild(h("div", null,
                `Toplam cevap: <b>${s.log_total}</b> `
                + `(<span style="color:${col("green")}">${lt.correct || 0}✓</span> `
                + `<span style="color:${col("red")}">${lt.wrong || 0}✗</span> `
                + `<span style="color:${col("yellow")}">${lt.blank || 0}∅</span>)`));
            body.appendChild(h("div", null,
                `Genel başarı: <b style="color:${col(rateColor(s.overall_rate))}">%${s.overall_rate}</b>`));
            body.appendChild(h("div", null, `Çalışılan gün: <b>${s.active_day_count}</b>`));
            if (s.best_day) body.appendChild(h("div", null,
                `En yoğun gün: <b>${esc(s.best_day.label)}</b> (${s.best_day.count} cevap)`));
            body.appendChild(h("div", null, `Aktif gün ortalaması: <b>${s.avg_per_active_day}</b> cevap`));
            if (s.first_log) body.appendChild(h("div", null, `Kayıt başlangıcı: <b>${esc(s.first_log)}</b>`));
        } else {
            body.appendChild(h("div", "muted", "Cevap geçmişi henüz yok — quiz çözdükçe burada birikecek."));
        }
        const s10 = s.son10 || {};
        body.appendChild(h("div", "muted", "&nbsp;"));
        body.appendChild(h("div", "muted",
            `Kelime bazlı (son 10 pencere): <span style="color:${col("green")}">${s10.correct || 0}✓</span> `
            + `<span style="color:${col("red")}">${s10.wrong || 0}✗</span> `
            + `<span style="color:${col("yellow")}">${s10.blank || 0}∅</span> (toplam ${s.son10_total})`));
        return body;
    }

    function krediler(s) {
        const frag = document.createDocumentFragment();
        frag.appendChild(tiles([
            ["💵 Bakiye", s.balance, "yellow"],
            ["⏱ Alınabilir (dk, bugün)", s.max_today, "green"],
            ["📺 Bugün Alınan (dk)", s.redeemed_today, "purple"],
            ["🪙 Bu Hafta Kazanılan", s.earned_week, "green"],
            ["💸 Bu Hafta Harcanan", s.spent_week, "red"],
            ["🗓 Sıfırlamaya (gün)", s.days_to_reset == null ? "—" : s.days_to_reset, "red"],
        ]));

        let p = panel("🪙 Kazanılan Krediler (son 14 gün)", "green", hbar(s.earned_14));
        p.appendChild(h("p", "muted small",
            `Her doğru cevap = <b style="color:${col("green")}">${s.credits_per_correct} kredi</b>. `
            + `Kayıtlı toplam kazanç: <b style="color:${col("green")}">${s.earned_total} kredi</b>`));
        frag.appendChild(p);

        p = panel("💸 Harcanan Krediler (son 14 gün)", "red", hbar(s.spent_14));
        p.appendChild(h("p", "muted small",
            `Alınan dakikalardan hesaplanır. Toplam harcama (son 60 gün): `
            + `<b style="color:${col("red")}">${s.spent_total} kredi</b>`));
        frag.appendChild(p);

        p = panel("📺 Alınan Ekran Süresi — günlük (14g) & haftalık (8h)", "yellow", hbar(s.redeemed_14));
        p.appendChild(hbar(s.redeemed_weekly));
        p.appendChild(h("p", "muted small",
            `Bu hafta: <b style="color:${col("yellow")}">${s.minutes_week} dk</b> · `
            + `Toplam (son 60 gün): <b style="color:${col("yellow")}">${s.redeemed_total} dk</b>`));
        frag.appendChild(p);

        const price = h("div", "text-lines");
        s.price_brackets.forEach((b) => {
            price.appendChild(h("div", null,
                `${b.hour}. saat: <b>${(+b.rate).toFixed(2).replace(/\.00$/, "")} kredi/dk</b>`
                + (b.current ? ` <span style="color:${col("yellow")}">◀ şu an</span>` : "")));
        });
        price.appendChild(h("div", null,
            `Şu anki dakika fiyatı: <b style="color:${col("yellow")}">${(+s.current_rate).toFixed(2).replace(/\.00$/, "")} kredi</b> `
            + `<span class="muted">(bugün ${s.redeemed_today} dk alındı)</span>`));
        price.appendChild(h("div", null,
            `Bakiyenle alınabilir: <b style="color:${col("green")}">${s.max_today} dk (bugün)</b> | `
            + `<b style="color:${col("green")}">${s.max_tomorrow} dk (yarın)</b>`));
        const mpc = s.base_rate ? (s.credits_per_correct / s.base_rate).toFixed(1) : 0;
        price.appendChild(h("div", null, `1 doğru cevap ≈ <b>${mpc} dk</b> ekran süresi <span class="muted">(taban fiyattan)</span>`));
        frag.appendChild(panel("🏷️ Fiyat Tarifesi — her ek saat pahalılaşır", "purple", price));

        frag.appendChild(panel("📉 Ekran süresi — son 30 gün (dk/gün)", "yellow", sparkline(s.spark_minutes_30, "yellow")));
        return frag;
    }

    function haftalik(s) {
        const frag = document.createDocumentFragment();
        frag.appendChild(panel("🌱 Haftalık Yeni Kelimeler (son 8 hafta)", "green", hbar(s.weekly_new)));
        frag.appendChild(panel("✨ Günlük Yeni Kelimeler (son 14 gün)", "purple", hbar(s.daily_new)));
        const legend = h("p", "small", `<span style="color:${col("green")}">█ Doğru</span> `
            + `<span style="color:${col("red")}">█ Yanlış</span> `
            + `<span style="color:${col("yellow")}">█ Boş</span>`);
        const p = panel("💬 Günlük Cevaplar (son 14 gün)", "yellow", legend);
        p.appendChild(stacked(s.daily_answers));
        frag.appendChild(p);
        frag.appendChild(panel("⚡ Aktivite — son 30 gün (günlük cevap)", "green", sparkline(s.spark_30, "green")));
        frag.appendChild(panel("🌱 Yeni kelime — son 30 gün", "purple", sparkline(s.spark_new_30, "purple")));
        return frag;
    }

    // Süre & Hız — built from the per-answer durations and the question
    // direction the quiz logs. Answers from before those were logged carry
    // neither, so they simply don't count towards any figure here.
    function sure(s) {
        const frag = document.createDocumentFragment();
        const timed = s.timed_count || 0;

        frag.appendChild(tiles([
            ["⏱ Bugün (dk)", toMin(s.time_today), "purple"],
            ["⚡ Ort. Cevap (sn)", s.time_avg, "green"],
            ["🎯 Ortanca (sn)", s.time_median, "yellow"],
            ["📅 Bu Hafta (dk)", toMin(s.time_week), "purple"],
            ["♾️ Toplam (sa)", (s.time_total / 3600).toFixed(1), "yellow"],
            ["💬 Süresi Kayıtlı", timed, "purple"],
            ["🚀 Cevap / dk", s.answers_per_minute, "green"],
            ["🪙 Kredi / dk", s.credits_per_minute, "yellow"],
        ]));

        if (!timed) {
            frag.appendChild(panel("⏱ Süre Kaydı", "yellow", h("p", "muted",
                "Cevap süreleri henüz kaydedilmemiş — quiz çözdükçe bu sekme dolacak. "
                + "Daha önce cevaplanan sorular süre içermediği için ortalamalara hiç katılmaz.")));
        }

        let p = panel("⏱ Günlük Çalışma Süresi (son 14 gün, dakika)", "purple", hbar(s.time_14 || []));
        const lines = [];
        lines.push(`Bugün: <b>${fmtDur(s.time_today)}</b> · bu hafta: <b>${fmtDur(s.time_week)}</b>`
            + ` · toplam: <b>${fmtDur(s.time_total)}</b>`);
        if (s.best_time_day) lines.push(`En uzun çalışılan gün: <b>${esc(s.best_time_day.label)}</b>`
            + ` <span class="muted">(${fmtDur(s.best_time_day.seconds)})</span>`);
        p.appendChild(h("p", "muted small", lines.join("<br>")));
        frag.appendChild(p);

        frag.appendChild(panel("📉 Çalışma süresi — son 30 gün (dk/gün)", "purple",
            sparkline(s.spark_time_30 || [], "purple")));

        p = panel("⚡ Cevap Hızı Dağılımı", "green", hbar(s.speed_buckets || []));
        if (timed) {
            p.appendChild(h("p", "muted small",
                `Ortalama <b>${s.time_avg} sn</b> · ortanca <b>${s.time_median} sn</b> · `
                + `en hızlı <b style="color:${col("green")}">${s.time_fastest} sn</b> · `
                + `en yavaş <b style="color:${col("red")}">${s.time_slowest} sn</b><br>`
                + `Son 7 gün ortalaması: <b>${s.time_avg_7} sn</b> · bugün: <b>${s.time_avg_today} sn</b>`));
        }
        frag.appendChild(p);

        const byRes = s.time_by_result || {};
        const resBody = h("div", "text-lines");
        [["correct", "Doğru", "green", "✓"], ["wrong", "Yanlış", "red", "✗"],
         ["blank", "Boş", "yellow", "∅"]].forEach(([key, label, token, sym]) => {
            const r = byRes[key] || {};
            resBody.appendChild(h("div", null, r.count
                ? `<span style="color:${col(token)}">${sym} ${esc(label)}</span> ortalama <b>${r.avg} sn</b> `
                  + `<span class="muted">(${r.count} cevap, toplam ${fmtDur(r.total)})</span>`
                : `<span style="color:${col(token)}">${sym} ${esc(label)}</span> `
                  + `<span class="muted">süresi kayıtlı cevap yok</span>`));
        });
        resBody.appendChild(h("p", "muted small",
            "Yanlış ve boş cevapların doğrulardan uzun sürmesi, sorunun gerçekten zorlandığını gösterir."));
        frag.appendChild(panel("🎯 Sonuca Göre Ortalama Süre", "yellow", resBody));

        const wordSpeed = (rows, token) => {
            const body = h("div", "text-lines");
            (rows || []).forEach((e) => {
                body.appendChild(h("div", null,
                    `<b>${esc(e.word)}</b> <span style="color:${col(token)}">${e.avg} sn</span> `
                    + `<span class="muted">(${e.count} cevap)</span>`));
            });
            if (!rows || !rows.length) body.appendChild(h("p", "muted", "Henüz veri yok."));
            return body;
        };
        if (s.slowest_words) {
            const minN = s.min_timed_answers || 2;
            frag.appendChild(panel(`🐢 En Yavaş Kelimeler (en az ${minN} cevap)`, "red",
                wordSpeed(s.slowest_words, "red")));
            frag.appendChild(panel(`🐇 En Hızlı Kelimeler (en az ${minN} cevap)`, "green",
                wordSpeed(s.fastest_words, "green")));
        }

        p = panel("🕒 Günün Saatlerine Göre Aktivite", "yellow", hbar(s.hour_blocks || []));
        if (s.busiest_hour != null) {
            const row = (s.hourly || [])[s.busiest_hour] || [0, 0, 0, 0];
            const tot = row[1] + row[2] + row[3];
            p.appendChild(h("p", "muted small",
                `En yoğun saat: <b style="color:${col("yellow")}">`
                + `${String(s.busiest_hour).padStart(2, "0")}:00–${String(s.busiest_hour + 1).padStart(2, "0")}:00</b> `
                + `(${tot} cevap, başarı %${tot ? Math.round(row[1] / tot * 100) : 0})`));
        }
        frag.appendChild(p);

        const dirBody = h("div", "text-lines");
        (s.direction_stats || []).forEach((d) => {
            dirBody.appendChild(h("div", null, d.total
                ? `<b>${esc(d.label)}</b> <span style="color:${col(rateColor(d.rate))}">%${Math.round(d.rate)}</span> `
                  + `<span class="muted">(<span style="color:${col("green")}">${d.correct}✓</span> `
                  + `<span style="color:${col("red")}">${d.wrong}✗</span> `
                  + `<span style="color:${col("yellow")}">${d.blank}∅</span>) ${d.total} soru`
                  + (d.avg_time ? ` · ort. ${d.avg_time} sn` : "") + `</span>`
                : `<b>${esc(d.label)}</b> <span class="muted">— henüz kayıt yok</span>`));
        });
        dirBody.appendChild(h("p", "muted small",
            "Soru yönü her soruda rastgele seçilir; iki yön arasındaki fark hangi yönün daha zor geldiğini gösterir."));
        frag.appendChild(panel("🔄 Soru Yönü", "purple", dirBody));

        return frag;
    }

    function kelimeler(s) {
        const frag = document.createDocumentFragment();
        frag.appendChild(panel("🏷️ Kelime Türleri", "purple", hbar(s.word_types)));

        const wrap = h("div", "table-wrap");
        const table = h("table", "admin-table");
        table.innerHTML = "<thead><tr><th>Kelime</th><th>Başarı</th><th>✓</th><th>✗</th><th>∅</th>"
            + "<th>Tekrar</th><th>Aralık</th><th>Sonraki Tekrar</th></tr></thead>";
        const tb = h("tbody");
        s.table_rows.forEach((e) => {
            const tr = h("tr");
            const rate = e.total
                ? `<span style="color:${col(rateColor(e.rate))}"><b>%${Math.round(e.rate)}</b></span>`
                : '<span class="muted">—</span>';
            const nxt = e.next
                ? `<span style="color:${e.delta <= 0 ? col("red") : col("muted")}">${esc(e.next)} (${e.delta >= 0 ? "+" : ""}${e.delta}g)</span>`
                : '<span class="muted">—</span>';
            tr.innerHTML = `<td class="u-name">${esc(e.word)}</td><td>${rate}</td>`
                + `<td style="color:${col("green")}">${e.correct}</td>`
                + `<td style="color:${col("red")}">${e.wrong}</td>`
                + `<td style="color:${col("yellow")}">${e.blank}</td>`
                + `<td>${e.repetitions}</td><td>${e.interval}g</td><td>${nxt}</td>`;
            tb.appendChild(tr);
        });
        table.appendChild(tb);
        wrap.appendChild(table);
        frag.appendChild(panel(`🔤 Tüm Kelimeler — en zordan kolaya (${s.started_count} başlanan)`, "green", wrap));
        return frag;
    }

    function gelecek(s) {
        const frag = document.createDocumentFragment();
        frag.appendChild(panel("🔮 Tekrar Takvimi (gelecek 14 gün)", "purple", hbar(s.forecast)));
        const body = h("div", "text-lines");
        if (s.sm2) {
            body.appendChild(h("div", null, `Ortalama kolaylık faktörü (EF): <b>${s.sm2.ef_avg}</b> <span class="muted">(1.30 = en zor, 2.50 = varsayılan)</span>`));
            body.appendChild(h("div", null, `En düşük EF: <b>${s.sm2.ef_min}</b> · En yüksek EF: <b>${s.sm2.ef_max}</b>`));
            body.appendChild(h("div", null, `Ortalama tekrar aralığı: <b>${s.sm2.interval_avg} gün</b>`));
            if (s.sm2.longest_word) body.appendChild(h("div", null,
                `En uzun aralık: <b>${esc(s.sm2.longest_word)}</b> (<span style="color:${col("green")}">${s.sm2.longest_interval} gün</span>)`));
        } else {
            body.appendChild(h("div", "muted", "Henüz çalışılmış kelime yok."));
        }
        frag.appendChild(panel("🧠 SM-2 Sağlığı", "green", body));
        return frag;
    }

    // ---------------------------------------------------------------- driver
    function render() {
        const root = document.getElementById("stats-root");
        if (!root) return;
        root.innerHTML = "";
        if (!payload) { root.appendChild(h("p", "muted", "Yükleniyor…")); return; }
        root.appendChild(section(payload));
    }

    async function load() {
        const root = document.getElementById("stats-root");
        if (root) root.innerHTML = '<p class="muted">Yükleniyor…</p>';
        const res = await fetch("/api/stats/full");
        if (res.status === 401) { window.location.href = "/login"; return; }
        payload = await res.json();
        render();
    }

    function initSubtabs() {
        document.querySelectorAll("#stats-subtabs .subtab").forEach((b) => {
            b.addEventListener("click", () => {
                document.querySelectorAll("#stats-subtabs .subtab").forEach((x) => x.classList.remove("active"));
                b.classList.add("active");
                activeSub = b.dataset.sub;
                render();
            });
        });
    }

    document.addEventListener("DOMContentLoaded", initSubtabs);
    window.CoalideStats = { load };
})();

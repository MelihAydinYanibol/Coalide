/* Coalide web app — front-end logic */
(function () {
    "use strict";

    const CFG = window.COALIDE || { sourceLanguage: "Türkçe", targetLanguage: "İngilizce" };

    // --- element refs ---
    const el = (id) => document.getElementById(id);
    const quizLoading = el("quiz-loading");
    const quizBody = el("quiz-body");
    const quizDone = el("quiz-done");
    const feedback = el("feedback");
    const answerForm = el("answer-form");
    const answerInput = el("answer-input");
    const submitBtn = el("submit-btn");
    const continueBtn = el("continue-btn");

    let current = null;      // current question payload
    let startTime = 0;       // when the question was shown
    let answered = false;

    // --------------------------------------------------------------------- //
    // Pronunciation (browser Web Speech API — no server audio needed)
    // --------------------------------------------------------------------- //
    function speak(text, lang) {
        if (!("speechSynthesis" in window) || !text) return;
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = lang || "en-US";
        u.rate = 0.95;
        window.speechSynthesis.speak(u);
    }

    // --------------------------------------------------------------------- //
    // Tabs
    // --------------------------------------------------------------------- //
    document.querySelectorAll(".tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
            document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
            tab.classList.add("active");
            const view = tab.dataset.view;
            el("view-" + view).classList.add("active");
            if (view === "stats") loadStats();
            if (view === "rewards") loadRewards();
            if (view === "quiz") answerInput && answerInput.focus();
        });
    });

    // --------------------------------------------------------------------- //
    // Logout
    // --------------------------------------------------------------------- //
    el("logout-btn").addEventListener("click", async () => {
        await fetch("/api/logout", { method: "POST" });
        window.location.href = "/login";
    });

    // --------------------------------------------------------------------- //
    // Quiz flow
    // --------------------------------------------------------------------- //
    function rateColor(rate, isNew) {
        if (isNew) return "var(--muted)";
        if (rate >= 80) return "var(--green)";
        if (rate >= 50) return "var(--yellow)";
        if (rate > 20) return "var(--orange)";
        return "var(--red)";
    }

    async function loadNext() {
        answered = false;
        feedback.classList.add("hidden");
        answerForm.classList.remove("hidden");
        quizBody.classList.add("hidden");
        quizDone.classList.add("hidden");
        quizLoading.classList.remove("hidden");

        const res = await fetch("/api/next");
        if (res.status === 401) { window.location.href = "/login"; return; }
        const data = await res.json();

        quizLoading.classList.add("hidden");
        if (data.done) {
            quizDone.classList.remove("hidden");
            return;
        }

        current = data.question;
        renderQuestion(current);
    }

    function renderQuestion(q) {
        quizBody.classList.remove("hidden");
        el("word-type").textContent = q.word_type;

        const rb = el("rate-badge");
        if (q.is_new) {
            rb.innerHTML = "✨ İlk kez";
            rb.style.color = "var(--muted)";
        } else {
            rb.innerHTML = `Başarı: <b>%${q.rate.toFixed(0)}</b> (${q.correct_attempts}/${q.total_attempts})`;
            rb.style.color = rateColor(q.rate, false);
        }

        // Direction text: prompt is in one language, answer wanted in the other.
        const wantLang = q.is_target_wanted ? CFG.targetLanguage : CFG.sourceLanguage;
        el("direction").textContent = `Bu kelimenin ${wantLang} karşılığı nedir?`;
        el("prompt").textContent = q.prompt;
        el("example").textContent = "📝 " + q.example_sentence;

        answerInput.value = "";
        answerInput.disabled = false;
        submitBtn.disabled = false;
        answerInput.focus();
        startTime = Date.now();
    }

    answerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (answered) return;
        const answer = answerInput.value;
        const timeTaken = (Date.now() - startTime) / 1000;

        answered = true;
        answerInput.disabled = true;
        submitBtn.disabled = true;

        const res = await fetch("/api/answer", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer, time_taken: timeTaken })
        });
        if (res.status === 401) { window.location.href = "/login"; return; }
        const data = await res.json();
        if (data.error) { // no active question (e.g. stale) — just reload
            loadNext();
            return;
        }
        showFeedback(data);
    });

    function showFeedback(data) {
        const line = el("feedback-line");
        line.classList.remove("correct", "wrong", "blank");

        let creditText = "";
        if (data.is_correct === true) {
            line.classList.add("correct");
            const c = data.credits || {};
            if (c.awarded > 0) creditText = `<span class="credit-flash">+${c.awarded} kredi</span>`;
            else if (c.in_window === false) creditText = `<span class="credit-flash" style="color:var(--yellow)">(kredi saati dışında)</span>`;
            line.innerHTML = "✅ Doğru! " + creditText;
        } else if (data.is_correct === null) {
            line.classList.add("blank");
            line.innerHTML = `⭕ Boş bırakıldı — Doğru cevap: <b>${escapeHtml(data.correct_answer)}</b>`;
        } else {
            line.classList.add("wrong");
            line.innerHTML = `❌ Yanlış — Doğru cevap: <b>${escapeHtml(data.correct_answer)}</b>`;
        }

        // Show alternative accepted answers if any.
        let sentence = data.full_sentence ? "📖 " + data.full_sentence : "";
        if (data.all_answers && data.all_answers.length > 1) {
            sentence += `  ·  Diğer kabul edilenler: ${data.all_answers.slice(1).map(escapeHtml).join(", ")}`;
        }
        el("feedback-sentence").textContent = sentence;

        feedback.classList.remove("hidden");
        answerForm.classList.add("hidden");
        continueBtn.focus();

        // Auto-pronounce the target word + sentence.
        speak(data.target, "en-US");
        setTimeout(() => speak(data.full_sentence, "en-US"), 700);

        el("replay-word").onclick = () => speak(data.target, "en-US");
        el("replay-sentence").onclick = () => speak(data.full_sentence, "en-US");

        if (data.credits && typeof data.credits.balance === "number") {
            setBalance(data.credits.balance);
        }
    }

    continueBtn.addEventListener("click", loadNext);

    // Enter continues when feedback is shown.
    document.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && answered && !feedback.classList.contains("hidden")) {
            const active = document.querySelector(".view.active");
            if (active && active.id === "view-quiz") { e.preventDefault(); loadNext(); }
        }
    });

    // --------------------------------------------------------------------- //
    // Stats
    // --------------------------------------------------------------------- //
    async function loadStats() {
        // Keep the header balance fresh, then render the full dashboard.
        try {
            const res = await fetch("/api/stats");
            if (res.ok) setBalance((await res.json()).balance);
        } catch (e) { /* ignore */ }
        if (window.CoalideStats) window.CoalideStats.load();
    }

    // --------------------------------------------------------------------- //
    // Rewards
    // --------------------------------------------------------------------- //
    const redeemForm = el("redeem-form");
    const redeemMinutes = el("redeem-minutes");
    const redeemDate = el("redeem-date");
    const quoteEl = el("quote");
    const redeemResult = el("redeem-result");

    function todayISO() { return new Date().toISOString().slice(0, 10); }

    async function loadRewards() {
        const res = await fetch("/api/stats");
        const s = await res.json();
        el("reward-balance").textContent = s.balance;
        setBalance(s.balance);
        if (!redeemDate.value) redeemDate.value = todayISO();
        redeemDate.min = todayISO();
        updateQuote();
    }

    async function updateQuote() {
        const minutes = parseInt(redeemMinutes.value, 10);
        const date = redeemDate.value;
        if (!minutes || minutes <= 0 || !date) { quoteEl.textContent = ""; return; }
        const res = await fetch("/api/quote", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ minutes, date })
        });
        const data = await res.json();
        if (data.cost != null) {
            quoteEl.textContent = `${minutes} dakika = ${data.cost} kredi`;
        } else {
            quoteEl.textContent = "";
        }
    }

    redeemMinutes.addEventListener("input", updateQuote);
    redeemDate.addEventListener("change", updateQuote);

    redeemForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        redeemResult.textContent = "";
        redeemResult.className = "redeem-result";
        const minutes = parseInt(redeemMinutes.value, 10);
        const date = redeemDate.value;
        const res = await fetch("/api/redeem", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ minutes, date })
        });
        const data = await res.json();
        if (data.ok) {
            redeemResult.classList.add("ok");
            redeemResult.textContent = `✅ ${data.minutes} dakika (${data.date}) tanımlandı. ${data.cost} kredi harcandı.`;
            setBalance(data.balance);
            el("reward-balance").textContent = data.balance;
            updateQuote();
        } else {
            redeemResult.classList.add("err");
            redeemResult.textContent = "⚠ " + (data.error || "İşlem başarısız.");
        }
    });

    // --------------------------------------------------------------------- //
    // Shared
    // --------------------------------------------------------------------- //
    function setBalance(n) {
        el("balance").textContent = n;
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, (c) => (
            { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
        ));
    }

    // --- boot ---
    fetch("/api/stats").then((r) => r.ok ? r.json() : null).then((s) => { if (s) setBalance(s.balance); });
    loadNext();
})();

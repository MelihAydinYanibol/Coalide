/* Coalide admin dashboard — front-end logic */
(function () {
    "use strict";

    const el = (id) => document.getElementById(id);
    const gate = el("admin-gate");
    const appEl = el("admin-app");

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, (c) => (
            { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
        ));
    }

    async function api(path, opts) {
        const res = await fetch(path, opts);
        if (res.status === 401) { showGate(); throw new Error("unauthorized"); }
        return res.json();
    }

    function showGate() {
        gate.classList.remove("hidden");
        appEl.classList.add("hidden");
    }
    function showApp() {
        gate.classList.add("hidden");
        appEl.classList.remove("hidden");
        loadUsers();
    }

    // --- login ---
    const loginForm = el("admin-login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const errEl = el("admin-login-error");
            errEl.textContent = "";
            const password = el("admin-password").value;
            const res = await fetch("/api/admin/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password })
            });
            const data = await res.json();
            if (data.ok) showApp();
            else errEl.textContent = data.error || "Giriş başarısız.";
        });
    }

    const logoutBtn = el("admin-logout");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", async () => {
            await fetch("/api/admin/logout", { method: "POST" });
            showGate();
        });
    }

    // --- tabs ---
    document.querySelectorAll(".tab").forEach((tab) => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
            document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
            tab.classList.add("active");
            const view = tab.dataset.view;
            el("view-" + view).classList.add("active");
            if (view === "users") loadUsers();
            if (view === "config") loadConfig();
        });
    });

    // --- users ---
    function rateColor(rate) {
        if (rate >= 80) return "var(--green)";
        if (rate >= 50) return "var(--yellow)";
        if (rate > 20) return "var(--orange)";
        return "var(--red)";
    }

    async function loadUsers() {
        const data = await api("/api/admin/users");
        const body = el("users-body");
        const empty = el("users-empty");
        body.innerHTML = "";
        if (!data.users.length) {
            empty.classList.remove("hidden");
            el("users-summary").textContent = "";
            return;
        }
        empty.classList.add("hidden");
        el("users-summary").textContent =
            `${data.users.length} öğrenci · ${data.total_words} kelimelik havuz`;

        data.users.forEach((u) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="u-name">👤 ${escapeHtml(u.username)}</td>
                <td><b class="credit-val">${u.balance}</b></td>
                <td>${u.words_seen}</td>
                <td>${u.due_now}</td>
                <td>${u.mastered}</td>
                <td style="color:${rateColor(u.overall_rate)}">%${u.overall_rate}</td>
                <td>${u.redeemed_today}</td>
                <td class="credit-controls">
                    <button class="ghost-btn tiny" data-user="${escapeHtml(u.username)}" data-delta="-10">−10</button>
                    <button class="ghost-btn tiny" data-user="${escapeHtml(u.username)}" data-delta="10">+10</button>
                    <button class="ghost-btn tiny" data-user="${escapeHtml(u.username)}" data-delta="100">+100</button>
                </td>`;
            body.appendChild(tr);
        });

        body.querySelectorAll("button[data-delta]").forEach((btn) => {
            btn.addEventListener("click", async () => {
                const username = btn.dataset.user;
                const delta = parseInt(btn.dataset.delta, 10);
                btn.disabled = true;
                const res = await api("/api/admin/credits", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, delta })
                });
                btn.disabled = false;
                if (res.ok) {
                    const cell = btn.closest("tr").querySelector(".credit-val");
                    cell.textContent = res.balance;
                    cell.classList.remove("flash"); void cell.offsetWidth; cell.classList.add("flash");
                }
            });
        });
    }

    // --- config ---
    async function loadConfig() {
        const data = await api("/api/admin/config");
        const form = el("config-form");
        form.innerHTML = "";
        data.fields.forEach((f) => {
            const row = document.createElement("div");
            row.className = "config-row";
            let input;
            if (f.type === "bool") {
                input = `<label class="switch"><input type="checkbox" data-key="${f.key}" ${f.value ? "checked" : ""}><span class="slider"></span></label>`;
            } else {
                const t = (f.type === "int" || f.type === "float") ? "number" : "text";
                const step = f.type === "float" ? ' step="0.1"' : "";
                input = `<input class="config-input" type="${t}"${step} data-key="${f.key}" value="${escapeHtml(f.value == null ? "" : f.value)}">`;
            }
            row.innerHTML = `
                <div class="config-label">
                    <span class="config-key">${escapeHtml(f.key)}</span>
                    <span class="config-desc">${escapeHtml(f.desc)}</span>
                </div>
                <div class="config-control">${input}</div>`;
            form.appendChild(row);
        });
    }

    el("config-save").addEventListener("click", async () => {
        const updates = {};
        document.querySelectorAll("#config-form [data-key]").forEach((inp) => {
            updates[inp.dataset.key] = inp.type === "checkbox" ? inp.checked : inp.value;
        });
        const resEl = el("config-result");
        resEl.className = "config-result";
        const res = await api("/api/admin/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ updates })
        });
        if (res.ok) {
            resEl.classList.add("ok");
            resEl.textContent = "✅ Kaydedildi";
        } else {
            resEl.classList.add("err");
            resEl.textContent = "⚠ " + (res.error || "Kaydedilemedi");
        }
        setTimeout(() => { resEl.textContent = ""; resEl.className = "config-result"; }, 2500);
    });

    // --- boot ---
    if (!gate.classList.contains("hidden")) {
        el("admin-password") && el("admin-password").focus();
    } else {
        showApp();
    }
})();

// Pagina di amministrazione: la chiave resta solo nel browser (sessionStorage) e va nell'header X-Admin-Key
const keyInput = document.getElementById("admin-key");
try { keyInput.value = sessionStorage.getItem("cdk30-admin-key") || ""; } catch (e) { /* storage non disponibile */ }
keyInput.addEventListener("change", () => {
  try { sessionStorage.setItem("cdk30-admin-key", keyInput.value); } catch (e) { /* storage non disponibile */ }
  loadBans();
});

const adminHeaders = () => ({"X-Admin-Key": keyInput.value});

async function adminAction(promise) {
  try {
    const data = await promise;
    show("admin-msg", data.message, "success");
    refresh();
  } catch (e) {
    show("admin-msg", e.message, "danger");
  }
}

async function loadBans() {
  if (!keyInput.value) return;
  try {
    const data = await api("/admin/bans", {headers: adminHeaders()});
    const tbody = document.getElementById("bans");
    fillTable("bans", data.bans.map(b => [b.nickname, b.reason, when(b.bannedAt), ""]));
    [...tbody.rows].forEach((tr, i) => {
      const btn = document.createElement("button");
      btn.className = "btn btn-link btn-sm p-0";
      btn.textContent = "togli";
      btn.addEventListener("click", () => adminAction(post("/admin/unban", {nickname: data.bans[i].nickname}, adminHeaders())));
      tr.lastChild.appendChild(btn);
    });
  } catch (e) {
    show("admin-msg", e.message, "danger");
  }
}

function refresh() {
  loadScores("scores").catch(console.error);
  loadMatches("matches").catch(console.error);
  loadLogs("logs").catch(console.error);
  loadBans();
}

loadConfig().then(() => {
  document.getElementById("broadcast-form").addEventListener("submit", e => {
    e.preventDefault();
    adminAction(post("/admin/broadcast", {text: document.getElementById("broadcast-text").value}, adminHeaders()));
  });
  document.getElementById("reset-btn").addEventListener("click", () => {
    if (confirm("Azzerare i numeri di tutti i giocatori?")) adminAction(post("/admin/reset", {}, adminHeaders()));
  });
  document.getElementById("ban-form").addEventListener("submit", e => {
    e.preventDefault();
    adminAction(post("/admin/ban", {nickname: document.getElementById("ban-nickname").value.trim(),
                                    reason: document.getElementById("ban-reason").value.trim()}, adminHeaders()));
  });
  refresh();
}).catch(e => show("admin-msg", `config.json non disponibile: ${e.message}`, "danger"));

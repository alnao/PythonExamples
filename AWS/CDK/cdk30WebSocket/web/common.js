// Funzioni comuni delle pagine del gioco cdk30: indirizzi da config.json (scritto da CDK), chiamate alle API
const CONFIG = {apiUrl: "", wsUrl: ""};

async function loadConfig() {
  Object.assign(CONFIG, await (await fetch("config.json")).json());
}

async function api(path, options = {}) {
  const res = await fetch(CONFIG.apiUrl + path, {
    ...options,
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function post(path, body, headers = {}) {
  return api(path, {method: "POST", body: JSON.stringify(body), headers});
}

function show(id, text, kind) {
  const box = document.getElementById(id);
  box.className = `alert alert-${kind} py-2`;
  box.textContent = text;
}

// riempie una tabella con le righe (valori come testo, mai come HTML)
function fillTable(tbodyId, rows) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const value of row) {
      const td = document.createElement("td");
      td.textContent = value ?? "";
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

const when = iso => iso ? new Date(iso).toLocaleString() : "";

async function loadScores(tbodyId) {
  const data = await api("/scores");
  fillTable(tbodyId, data.scores.map((p, i) => [i + 1, p.nickname, p.score, p.playing ? "🎯 in gioco" : "⏸️ senza numero",
                                               p.connected ? "🟢" : "⚪"]));
}

async function loadMatches(tbodyId) {
  const data = await api("/matches");
  fillTable(tbodyId, data.matches.map(m => [when(m.timestamp), m.winner, m.loser, m.numberGuessed]));
}

async function loadLogs(tbodyId) {
  const data = await api("/logs");
  fillTable(tbodyId, data.logs.map(l => [when(l.ts.split("#")[0]), l.nickname, l.message]));
}

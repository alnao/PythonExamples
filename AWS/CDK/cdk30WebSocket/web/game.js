// Pagina del giocatore: iscrizione (REST), poi WebSocket con il nickname; dopo "Scollegati" bisogna rientrare
let nickname = null, ws = null, pingTimer = null;

function addEvent(text) {
  const li = document.createElement("li");
  li.className = "list-group-item px-0";
  li.textContent = `${new Date().toLocaleTimeString()} · ${text}`;
  document.getElementById("events").prepend(li);
}

function setPlaying(playing) {
  document.getElementById("guess").disabled = !playing;
  document.getElementById("guess-btn").disabled = !playing;
  document.getElementById("disconnect-btn").disabled = !playing;
  document.getElementById("nickname").disabled = playing;  // il nickname non si cambia durante la sessione
}

async function join(event) {
  event.preventDefault();
  const nick = document.getElementById("nickname").value.trim();
  const number = Number(document.getElementById("number").value);
  try {
    const data = await post("/set-number", {nickname: nick, number});
    show("join-msg", data.message, "success");
    nickname = nick;
    setPlaying(true);
    if (!ws) connectWS();
  } catch (e) {
    show("join-msg", e.message, "danger");
  }
}

async function guess(event) {
  event.preventDefault();
  try {
    const data = await post("/guess-number", {attacker: nickname, guess: Number(document.getElementById("guess").value)});
    show("guess-msg", data.message, data.hit ? "success" : "warning");
    refresh();
  } catch (e) {
    show("guess-msg", e.message, "danger");
  }
}

function connectWS() {
  const badge = document.getElementById("ws-status");
  ws = new WebSocket(`${CONFIG.wsUrl}?nickname=${encodeURIComponent(nickname)}`);
  ws.onopen = () => {
    badge.className = "badge text-bg-success";
    badge.textContent = "collegato";
    // API Gateway chiude le connessioni inattive dopo 10 minuti: un ping ogni 5
    pingTimer = setInterval(() => ws.send(JSON.stringify({action: "ping"})), 5 * 60 * 1000);
  };
  ws.onmessage = event => {
    const msg = JSON.parse(event.data);
    if (msg.event === "pong") return;
    if (msg.event === "match") addEvent(`⚔️ ${msg.winner} ha indovinato il numero di ${msg.loser} (${msg.number})`);
    else if (msg.event === "join") addEvent(`👋 ${msg.nickname} è entrato in gioco`);
    else if (msg.event === "hit") { addEvent(`💥 ${msg.message}`); show("join-msg", msg.message, "danger"); }
    else if (msg.event === "broadcast") addEvent(`📣 Amministratore: ${msg.message}`);
    else if (msg.event === "reset") addEvent(`🔄 ${msg.message}`);
    else if (msg.event === "ban") { addEvent(`⛔ Sei stato bannato: ${msg.reason}`); disconnectWS(); }
    else addEvent(JSON.stringify(msg));
    refresh();
  };
  ws.onclose = () => {
    clearInterval(pingTimer);
    badge.className = "badge text-bg-secondary";
    badge.textContent = "non collegato";
    ws = null;
  };
  ws.onerror = () => { badge.className = "badge text-bg-danger"; badge.textContent = "errore"; };
}

function disconnectWS() {
  if (ws) ws.close();
  nickname = null;
  setPlaying(false);
  show("join-msg", "Scollegato: per giocare ancora rientra con il tuo nickname", "secondary");
}

function refresh() {
  loadScores("scores").catch(console.error);
  loadMatches("matches").catch(console.error);
}

loadConfig().then(() => {
  document.getElementById("join-form").addEventListener("submit", join);
  document.getElementById("guess-form").addEventListener("submit", guess);
  document.getElementById("disconnect-btn").addEventListener("click", disconnectWS);
  refresh();
}).catch(e => show("join-msg", `config.json non disponibile: ${e.message}`, "danger"));

// Frontend del cdk28: le API sono sullo stesso dominio CloudFront (/persone e /test vanno al load balancer)

async function checkBackend() {
  const status = document.getElementById("status");
  try {
    const res = await fetch("/test");
    status.textContent = res.ok ? `✅ backend raggiungibile (${await res.text()})` : `⚠️ backend: HTTP ${res.status}`;
  } catch (e) {
    status.textContent = `❌ backend non raggiungibile: ${e.message}`;
  }
}

async function loadPersone() {
  const res = await fetch("/persone");
  const persone = await res.json();
  const rows = document.getElementById("rows");
  rows.innerHTML = "";
  for (const p of persone) {
    const tr = document.createElement("tr");
    for (const value of [p.nome, p.cognome]) {
      const td = document.createElement("td");
      td.textContent = value ?? "";
      tr.appendChild(td);
    }
    rows.appendChild(tr);
  }
}

async function addPersona(event) {
  event.preventDefault();
  const persona = {nome: document.getElementById("nome").value.trim(), cognome: document.getElementById("cognome").value.trim()};
  const res = await fetch("/persone", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(persona)});
  if (res.ok) {
    event.target.reset();
    await loadPersone();
  }
}

document.getElementById("form").addEventListener("submit", addPersona);
checkBackend();
loadPersone().catch(e => { document.getElementById("status").textContent = `❌ ${e.message}`; });

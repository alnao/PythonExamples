// Pagina della blockchain cdk26: l'URL delle API arriva da config.json, scritto da CDK al deploy
let API_URL = "";

function cell(text, cls) {
  const td = document.createElement("td");
  td.textContent = text;
  if (cls) td.className = cls;
  return td;
}

function show(text, kind) {
  const box = document.getElementById("message");
  box.className = `alert alert-${kind}`;
  box.textContent = text;
}

async function call(path, options) {
  const res = await fetch(API_URL + path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function addTransaction(event) {
  event.preventDefault();
  const body = {
    sender: document.getElementById("sender").value.trim(),
    recipient: document.getElementById("recipient").value.trim(),
    amount: Number(document.getElementById("amount").value),
  };
  try {
    const data = await call("transaction", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    show(`${data.message}: ${body.sender} → ${body.recipient} ${body.amount}`, "success");
    document.getElementById("recipient").value = "";
    document.getElementById("amount").value = "";
  } catch (e) { show(e.message, "danger"); }
}

async function mineBlock() {
  const btn = document.getElementById("mine-btn");
  const out = document.getElementById("mine-result");
  btn.disabled = true;
  out.textContent = "Mining in corso...";
  try {
    const data = await call("mine", {method: "POST"});
    out.innerHTML = "";
    if (data.block) {
      out.appendChild(blockCard(data.block));
      show(`${data.message} in ${data.seconds} s (nonce ${data.block.nonce})`, "success");
    } else {
      out.textContent = data.message;
    }
  } catch (e) { out.textContent = ""; show(e.message, "danger"); }
  btn.disabled = false;
}

async function loadTransactions() {
  const data = await call("transactions");
  const rows = document.getElementById("tx-rows");
  rows.innerHTML = "";
  for (const tx of data.transactions.reverse()) {
    const tr = document.createElement("tr");
    tr.append(cell(new Date(tx.timestamp).toLocaleString()), cell(tx.sender), cell(tx.recipient),
      cell(tx.amount, "text-end"), cell(tx.status === "mined" ? "✅ minata" : "⏳ in attesa"),
      cell(tx.block_index ?? "-"));
    rows.appendChild(tr);
  }
}

async function loadBalances() {
  const data = await call("balances");
  const rows = document.getElementById("balance-rows");
  rows.innerHTML = "";
  for (const [address, balance] of Object.entries(data.balances).sort()) {
    const tr = document.createElement("tr");
    tr.append(cell(address), cell(balance, "text-end " + (Number(balance) < 0 ? "text-danger" : "")));
    rows.appendChild(tr);
  }
}

function blockCard(block) {
  const card = document.createElement("div");
  card.className = "card block-card mb-2";
  const body = document.createElement("div");
  body.className = "card-body py-2";
  const title = document.createElement("h2");
  title.className = "h6 mb-1";
  title.textContent = `Blocco #${block.index} · ${block.transactions.length} transazioni · nonce ${block.nonce} · ${new Date(block.timestamp * 1000).toLocaleString()}`;
  const hash = document.createElement("div");
  hash.className = "hash";
  hash.textContent = `hash ${block.hash}\nprecedente ${block.previous_hash}`;
  hash.style.whiteSpace = "pre-wrap";
  body.append(title, hash);
  card.appendChild(body);
  return card;
}

async function loadChain() {
  const [validation, chain] = await Promise.all([call("validate"), call("blocks")]);
  const box = document.getElementById("validation");
  box.className = `alert alert-${validation.valid ? "success" : "danger"}`;
  box.textContent = validation.valid
    ? `Catena valida: ${validation.blocks} blocchi`
    : `Catena NON valida: ${validation.errors.join("; ")}`;
  const list = document.getElementById("blocks");
  list.innerHTML = "";
  for (const block of chain.blocks.reverse()) list.appendChild(blockCard(block));
}

const loaders = {transactions: loadTransactions, balances: loadBalances, chain: loadChain};

async function init() {
  API_URL = (await (await fetch("config.json")).json()).apiUrl;
  document.getElementById("tx-form").addEventListener("submit", addTransaction);
  document.getElementById("mine-btn").addEventListener("click", mineBlock);
  document.querySelectorAll("[data-load]").forEach(tab => tab.addEventListener("shown.bs.tab", () =>
    loaders[tab.dataset.load]().catch(e => show(e.message, "danger"))));
}

init().catch(e => show(`config.json non disponibile: ${e.message}`, "danger"));

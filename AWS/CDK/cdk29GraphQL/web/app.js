// Pagina della lista note cdk29: URL e chiave della API GraphQL arrivano da config.json (scritto da CDK)
let API_URL = "", API_KEY = "";
const note = new Map();  // id -> nota

function show(text, kind) {
  const box = document.getElementById("message");
  box.className = `alert alert-${kind}`;
  box.textContent = text;
}

async function graphql(query, variables = {}) {
  const res = await fetch(API_URL, {
    method: "POST",
    headers: {"Content-Type": "application/json", "x-api-key": API_KEY},
    body: JSON.stringify({query, variables}),
  });
  const data = await res.json();
  if (data.errors) throw new Error(data.errors.map(e => e.message).join("; "));
  return data.data;
}

function render() {
  const list = document.getElementById("note");
  list.innerHTML = "";
  if (note.size === 0) {
    const li = document.createElement("li");
    li.className = "list-group-item text-muted";
    li.textContent = "Nessuna nota presente.";
    list.appendChild(li);
    return;
  }
  const sorted = [...note.values()].sort((a, b) => (a.createdAt || "").localeCompare(b.createdAt || ""));
  for (const n of sorted) {
    const li = document.createElement("li");
    li.className = "list-group-item d-flex align-items-center justify-content-between";
    const text = document.createElement("span");
    text.textContent = n.testo;  // textContent: il testo della nota non diventa HTML
    const btn = document.createElement("button");
    btn.className = "btn btn-outline-danger btn-sm";
    btn.textContent = "Elimina";
    btn.addEventListener("click", () => deleteNota(n.id));
    li.append(text, btn);
    list.appendChild(li);
  }
}

async function loadNote() {
  const data = await graphql("query { getNote { id testo createdAt } }");
  note.clear();
  for (const n of data.getNote || []) note.set(n.id, n);
  render();
}

async function addNota(event) {
  event.preventDefault();
  const input = document.getElementById("testo");
  try {
    const data = await graphql("mutation Add($testo: String!) { addNota(testo: $testo) { id testo createdAt } }",
                               {testo: input.value.trim()});
    note.set(data.addNota.id, data.addNota);
    render();
    input.value = "";
  } catch (e) { show(e.message, "danger"); }
}

async function deleteNota(id) {
  try {
    await graphql("mutation Del($id: ID!) { deleteNota(id: $id) }", {id});
    note.delete(id);
    render();
  } catch (e) { show(e.message, "danger"); }
}

// Subscription con il protocollo WebSocket di AppSync (endpoint appsync-realtime-api, sottoprotocollo graphql-ws)
function subscribe() {
  const badge = document.getElementById("realtime");
  const host = new URL(API_URL).host;
  const auth = {host, "x-api-key": API_KEY};
  const realtime = API_URL.replace("https://", "wss://").replace("appsync-api", "appsync-realtime-api");
  const ws = new WebSocket(`${realtime}?header=${btoa(JSON.stringify(auth))}&payload=e30=`, ["graphql-ws"]);
  const subscriptions = {
    add: "subscription { onAddNota { id testo createdAt } }",
    del: "subscription { onDeleteNota }",
  };
  ws.onopen = () => ws.send(JSON.stringify({type: "connection_init"}));
  ws.onmessage = event => {
    const msg = JSON.parse(event.data);
    if (msg.type === "connection_ack") {
      for (const [id, query] of Object.entries(subscriptions)) {
        ws.send(JSON.stringify({id, type: "start",
          payload: {data: JSON.stringify({query, variables: {}}), extensions: {authorization: auth}}}));
      }
    } else if (msg.type === "start_ack") {
      badge.className = "badge text-bg-success";
      badge.textContent = "tempo reale: collegato";
    } else if (msg.type === "data") {
      const data = msg.payload.data;
      if (data.onAddNota) note.set(data.onAddNota.id, data.onAddNota);
      if (data.onDeleteNota) note.delete(data.onDeleteNota);
      render();
    } else if (msg.type === "error" || msg.type === "connection_error") {
      badge.className = "badge text-bg-danger";
      badge.textContent = "tempo reale: errore";
      console.error(msg);
    }
  };
  ws.onclose = () => {
    badge.className = "badge text-bg-warning";
    badge.textContent = "tempo reale: scollegato, nuovo tentativo tra 5 secondi";
    setTimeout(subscribe, 5000);
  };
}

async function init() {
  const config = await (await fetch("config.json")).json();
  API_URL = config.graphqlUrl;
  API_KEY = config.apiKey;
  document.getElementById("form").addEventListener("submit", addNota);
  await loadNote();
  subscribe();
}

init().catch(e => show(e.message, "danger"));

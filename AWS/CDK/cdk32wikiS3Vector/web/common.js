// Funzioni comuni alle pagine della wiki: chiave API, chiamate al backend, escape HTML.
// Le API sono sotto /api sullo stesso host del sito (niente CORS).

const API = '/api';
const KEY_STORAGE = 'wikiS3VectorApiKey';

function getApiKey() {
    try { return localStorage.getItem(KEY_STORAGE) || ''; } catch (e) { return ''; }
}

function setApiKey(value) {
    try { localStorage.setItem(KEY_STORAGE, value); } catch (e) { /* storage non disponibile */ }
}

// Ogni testo che arriva dal backend (documenti, risposte, nomi file) passa da qui prima di innerHTML
function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function errorMessage(data, status) {
    const detail = data && (data.detail || data.error);
    if (Array.isArray(detail)) return detail.map(d => d.msg || JSON.stringify(d)).join('; ');
    return typeof detail === 'string' ? detail : `HTTP ${status}`;
}

async function apiFetch(path, options = {}) {
    const headers = Object.assign({ 'X-API-Key': getApiKey() }, options.headers || {});
    const response = await fetch(API + path, Object.assign({}, options, { headers }));
    let data = null;
    try { data = await response.json(); } catch (e) { data = null; }
    if (!response.ok) throw new Error(errorMessage(data, response.status));
    return data;
}

function apiJson(path, method, body) {
    return apiFetch(path, {
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
}

// Stima dei costi degli embedding: Titan Text Embeddings V2 in eu-central-1, IVA esclusa (verificato
// sul conto di ottobre 2026: 1,35 milioni di token addebitati 0,27 $). Oltre COST_CONFIRM_USD si chiede conferma.
const TITAN_USD_PER_MTOKEN = 0.20;
const CHARS_PER_TOKEN = 4;          // media indicativa per testi italiani, inglesi e codice
const CHUNK_CHARS = 1500;           // parti da circa 1500 caratteri...
const CHUNK_OVERHEAD = 1.1;         // ...con 3 righe ripetute e il percorso del file
const COST_CONFIRM_USD = 0.01;

function tokensCost(tokens) {
    return { tokens: Math.ceil(tokens), usd: tokens * TITAN_USD_PER_MTOKEN / 1e6 };
}

function formatUsd(usd) {
    return usd.toFixed(usd < 0.1 ? 3 : 2).replace('.', ',');
}

function costText(estimate) {
    return `circa ${formatUsd(estimate.usd)} $ (~${estimate.tokens.toLocaleString('it-IT')} token Titan Embeddings, stima indicativa IVA esclusa)`;
}

/* Conferma solo se la stima supera COST_CONFIRM_USD; true = si procede */
function confirmCost(what, estimate) {
    if (estimate.usd < COST_CONFIRM_USD) return true;
    return confirm(`${what} potrebbe avere costi di ${costText(estimate)}.\n\nProcediamo?`);
}

function alertHtml(type, html) {
    return `<div class="alert alert-${type} mb-0">${html}</div>`;
}

// Campo "API key" nella navbar: valore salvato nel browser
function setupApiKeyField() {
    const input = document.getElementById('apiKey');
    input.value = getApiKey();
    input.addEventListener('change', () => setApiKey(input.value.trim()));
}

// Indicatore di stato nella navbar (/api/health non richiede la chiave)
async function checkHealth() {
    const indicator = document.getElementById('statusIndicator');
    const text = document.getElementById('statusText');
    try {
        const response = await fetch(`${API}/health`);
        const ok = response.ok;
        indicator.className = `status-indicator status-${ok ? 'online' : 'offline'}`;
        text.textContent = ok ? 'Online' : 'Offline';
    } catch (e) {
        indicator.className = 'status-indicator status-offline';
        text.textContent = 'Offline';
    }
}

function startHealthMonitoring() {
    checkHealth();
    setInterval(checkHealth, 30000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) checkHealth(); });
}

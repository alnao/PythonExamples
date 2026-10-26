// Pagina principale: caricamento dei documenti e domande (RAG), versione serverless.
// Il file va direttamente su S3 con un POST prefirmato; l'indicizzazione parte da sola
// e la pagina ne segue lo stato (uploading -> processing -> ready | error).

const POLL_MS = 2000;
const POLL_MAX = 480;   // 16 minuti: la Lambda di indicizzazione ha al massimo 15 minuti

// dimensione massima dei file, letta da /api/supported-formats (che non richiede la chiave)
let maxUploadMb = 250;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const megabytes = bytes => (bytes / 1024 / 1024).toFixed(1);

async function loadUploadLimit() {
    try {
        const response = await fetch(`${API}/supported-formats`);
        const data = await response.json();
        if (data.max_upload_mb) maxUploadMb = data.max_upload_mb;
    } catch (e) { /* resta il default */ }
    document.getElementById('maxUpload').textContent = `${maxUploadMb} MB`;
}

/* Errore restituito da S3 (XML <Error><Code>..</Code><Message>..</Message>) in parole semplici */
function s3ErrorMessage(status, body) {
    const doc = new DOMParser().parseFromString(body || '', 'application/xml');
    const code = doc.querySelector('Code')?.textContent || '';
    const message = doc.querySelector('Message')?.textContent || '';
    if (code === 'EntityTooLarge') return `il file supera il massimo di ${maxUploadMb} MB`;
    if (code === 'AccessDenied' && /expired/i.test(message)) return 'autorizzazione al caricamento scaduta: riprova';
    if (code) return `S3 ha rifiutato il file (${code}${message ? ': ' + message : ''})`;
    return `upload su S3 non riuscito (HTTP ${status})`;
}

/* POST prefirmato verso S3 con XMLHttpRequest, che a differenza di fetch segnala l'avanzamento */
function uploadToS3(upload, file, onProgress) {
    const formData = new FormData();
    Object.entries(upload.fields).forEach(([name, value]) => formData.append(name, value));
    formData.append('file', file);   // il file deve essere l'ultimo campo
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', upload.url);
        xhr.upload.onprogress = e => { if (e.lengthComputable) onProgress(e.loaded, e.total); };
        xhr.onload = () => (xhr.status >= 200 && xhr.status < 300)
            ? resolve() : reject(new Error(s3ErrorMessage(xhr.status, xhr.responseText)));
        xhr.onerror = () => reject(new Error('connessione interrotta durante il caricamento su S3'));
        xhr.send(formData);
    });
}

async function waitForIndex(docId, resultDiv) {
    for (let i = 0; i < POLL_MAX; i++) {
        await sleep(POLL_MS);
        const status = await apiFetch(`/documents/${encodeURIComponent(docId)}/status`);
        if (status.state === 'ready' || status.state === 'error') return status;
        resultDiv.innerHTML = alertHtml('info', `Indicizzazione in corso (${escapeHtml(status.state)})...`);
    }
    throw new Error('indicizzazione ancora in corso: controlla la pagina Admin tra qualche minuto');
}

async function ingestDocument() {
    const resultDiv = document.getElementById('ingestResult');
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) {
        resultDiv.innerHTML = alertHtml('warning', 'Scegli un file');
        return;
    }
    if (file.size > maxUploadMb * 1024 * 1024) {
        resultDiv.innerHTML = alertHtml('warning', `Il file pesa ${megabytes(file.size)} MB: il massimo è ${maxUploadMb} MB`);
        return;
    }
    if (!confirmCost(`L'indicizzazione di "${file.name}" (${megabytes(file.size)} MB)`, fileEmbeddingCost(file), 'Titan Embeddings')) {
        resultDiv.innerHTML = alertHtml('secondary', 'Caricamento annullato');
        return;
    }
    const button = document.getElementById('ingestBtn');
    button.disabled = true;
    resultDiv.innerHTML = alertHtml('info', 'Caricamento su S3...');
    try {
        const created = await apiJson('/uploads', 'POST', {
            filename: file.name, doc_id: document.getElementById('docId').value.trim(),
        });
        await uploadToS3(created.upload, file, (loaded, total) => {
            resultDiv.innerHTML = alertHtml('info', `Caricamento su S3: ${Math.floor(loaded * 100 / total)}%`
                + ` (${megabytes(loaded)} di ${megabytes(total)} MB)`);
        });
        resultDiv.innerHTML = alertHtml('info', 'File caricato, indicizzazione in corso...');
        const status = await waitForIndex(created.doc_id, resultDiv);
        if (status.state === 'error') throw new Error(status.error);
        resultDiv.innerHTML = alertHtml('success', `Documento <strong>${escapeHtml(status.doc_id)}</strong>
            (${escapeHtml(status.filename)}) indicizzato: ${status.chunks} parti, ${status.text_length} caratteri.`);
        fileInput.value = '';
        document.getElementById('docId').value = '';
    } catch (error) {
        resultDiv.innerHTML = alertHtml('danger', `Caricamento non riuscito: ${escapeHtml(error.message)}`);
    } finally {
        button.disabled = false;
    }
}

// Risposta con le citazioni [n] evidenziate
function answerHtml(answer) {
    return escapeHtml(answer).replace(/\[(\d+)\]/g, '<span class="badge text-bg-secondary cite">$1</span>');
}

const SOURCES_SHOWN = 10;   // fonti visibili subito, le altre in un elenco da aprire

function sourcesHtml(sources) {
    if (!sources.length) return '';
    const item = s => `
        <li class="list-group-item">
            <div class="d-flex justify-content-between">
                <span><span class="badge text-bg-secondary me-1">${s.n}</span>
                    <strong>${escapeHtml(s.filename)}</strong>, parte ${s.chunk + 1}</span>
                <small class="text-muted" title="Somiglianza con la domanda">${s.score}</small>
            </div>
            <div class="source-excerpt text-muted mt-1">${escapeHtml(s.excerpt)}…</div>
        </li>`;
    const first = sources.slice(0, SOURCES_SHOWN).map(item).join('');
    const others = sources.slice(SOURCES_SHOWN);
    return `<h6 class="mt-3">Fonti</h6><ul class="list-group">${first}</ul>`
        + (others.length ? `<details class="mt-2"><summary>Altre ${others.length} fonti</summary>
            <ul class="list-group mt-2">${others.map(item).join('')}</ul></details>` : '');
}

/* Brani trovati e brani entrati nel contesto (oltre il budget di caratteri restano fuori) */
function usageHtml(data) {
    if (!data.found) return '';
    const note = data.used < data.found ? ` (gli altri ${data.found - data.used} non stavano nel contesto del modello)` : '';
    return `<div class="small text-muted mt-2">Brani trovati: ${data.found}, usati per la risposta: ${data.used}${note}</div>`;
}

/* Caso peggiore di una domanda: tutti i k brani nel contesto (al massimo 600.000 caratteri) e 1024 token di risposta */
function queryCost(k) {
    const input = tokensCost(Math.min(k * CHUNK_CHARS, 600000) / CHARS_PER_TOKEN, NOVA_IN_USD_PER_MTOKEN);
    return { tokens: input.tokens, usd: input.usd + tokensCost(1024, NOVA_OUT_USD_PER_MTOKEN).usd };
}

async function queryDocuments() {
    const resultDiv = document.getElementById('queryResult');
    const question = document.getElementById('queryText').value.trim();
    if (!question) {
        resultDiv.innerHTML = alertHtml('warning', 'Scrivi una domanda');
        return;
    }
    const k = Number(document.getElementById('topK').value);
    if (!confirmCost(`Una domanda con ${k} brani`, queryCost(k), 'Nova Lite')) return;
    const button = document.getElementById('queryBtn');
    button.disabled = true;
    resultDiv.innerHTML = alertHtml('info', 'Ricerca nei documenti...');
    try {
        const data = await apiJson('/query', 'POST', { question, k });
        resultDiv.innerHTML = `<div class="bg-light p-3 rounded answer">${answerHtml(data.answer)}</div>`
            + usageHtml(data) + sourcesHtml(data.sources);
    } catch (error) {
        resultDiv.innerHTML = alertHtml('danger', `Domanda non riuscita: ${escapeHtml(error.message)}`);
    } finally {
        button.disabled = false;
    }
}

function setupEventListeners() {
    document.getElementById('ingestBtn').addEventListener('click', ingestDocument);
    document.getElementById('queryBtn').addEventListener('click', queryDocuments);
    document.getElementById('queryText').addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); queryDocuments(); }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupApiKeyField();
    loadUploadLimit();
    setupEventListeners();
    startHealthMonitoring();
});

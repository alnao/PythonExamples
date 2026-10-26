// Pagina principale: caricamento dei documenti e domande (RAG)

async function ingestDocument() {
    const resultDiv = document.getElementById('ingestResult');
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    if (!file) {
        resultDiv.innerHTML = alertHtml('warning', 'Scegli un file');
        return;
    }
    if (!confirmCost(`L'indicizzazione di "${file.name}" (${(file.size / 1024 / 1024).toFixed(1)} MB)`, fileEmbeddingCost(file))) {
        resultDiv.innerHTML = alertHtml('secondary', 'Caricamento annullato');
        return;
    }
    const button = document.getElementById('ingestBtn');
    button.disabled = true;
    resultDiv.innerHTML = alertHtml('info', 'Caricamento e indicizzazione in corso (PDF scansionati e immagini richiedono qualche secondo)...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_id', document.getElementById('docId').value.trim());
    try {
        const data = await apiFetch('/ingest', { method: 'POST', body: formData });
        resultDiv.innerHTML = alertHtml('success', `Documento <strong>${escapeHtml(data.doc_id)}</strong>
            (${escapeHtml(data.filename)}) indicizzato: ${data.chunks} parti, ${data.extracted_text_length} caratteri.`);
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

function sourcesHtml(sources) {
    if (!sources.length) return '';
    const items = sources.map(s => `
        <li class="list-group-item">
            <div class="d-flex justify-content-between">
                <span><span class="badge text-bg-secondary me-1">${s.n}</span>
                    <strong>${escapeHtml(s.filename)}</strong>, parte ${s.chunk + 1}</span>
                <small class="text-muted" title="Somiglianza con la domanda">${s.score}</small>
            </div>
            <div class="source-excerpt text-muted mt-1">${escapeHtml(s.excerpt)}…</div>
        </li>`).join('');
    return `<h6 class="mt-3">Fonti</h6><ul class="list-group">${items}</ul>`;
}

async function queryDocuments() {
    const resultDiv = document.getElementById('queryResult');
    const question = document.getElementById('queryText').value.trim();
    if (!question) {
        resultDiv.innerHTML = alertHtml('warning', 'Scrivi una domanda');
        return;
    }
    const button = document.getElementById('queryBtn');
    button.disabled = true;
    resultDiv.innerHTML = alertHtml('info', 'Ricerca nei documenti...');
    try {
        const k = Number(document.getElementById('topK').value);
        const data = await apiJson('/query', 'POST', { question, k });
        resultDiv.innerHTML = `<div class="bg-light p-3 rounded answer">${answerHtml(data.answer)}</div>` + sourcesHtml(data.sources);
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
    setupEventListeners();
    startHealthMonitoring();
});

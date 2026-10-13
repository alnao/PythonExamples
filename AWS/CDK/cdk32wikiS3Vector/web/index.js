// Pagina di ricerca: domanda -> passaggi piu' simili, raggruppati per file (nessun modello di chat)

const SNIPPET_CHARS = 700;   // caratteri mostrati subito di ogni passaggio, il resto si apre

function snippetHtml(s) {
    const text = s.text.length > SNIPPET_CHARS
        ? `${escapeHtml(s.text.slice(0, SNIPPET_CHARS))}<details><summary class="small">tutto il passaggio</summary>${escapeHtml(s.text.slice(SNIPPET_CHARS))}</details>`
        : escapeHtml(s.text);
    return `<div class="mt-2">
        <div class="small text-muted">righe ${s.line_start}-${s.line_end} · somiglianza <span class="score">${s.score}</span></div>
        <div class="snippet border rounded p-2">${text}</div>
    </div>`;
}

function resultHtml(r, position) {
    return `<div class="card mb-3">
        <div class="card-body">
            <div class="d-flex flex-wrap justify-content-between gap-2">
                <div><span class="badge text-bg-secondary me-1">${position}</span>
                    <span class="result-path fw-semibold">${escapeHtml(r.path)}</span></div>
                <div class="small">
                    ${r.folder ? `<span class="badge text-bg-light border">${escapeHtml(r.folder)}</span>` : ''}
                    <span class="badge text-bg-light border">${escapeHtml(r.extension)}</span>
                    <span class="text-muted ms-1" title="Somiglianza del passaggio migliore">${r.score}</span>
                </div>
            </div>
            ${r.snippets.map(snippetHtml).join('')}
        </div>
    </div>`;
}

async function search() {
    const resultsDiv = document.getElementById('results');
    const question = document.getElementById('question').value.trim();
    if (!question) {
        resultsDiv.innerHTML = alertHtml('warning', 'Scrivi cosa cercare');
        return;
    }
    const button = document.getElementById('searchBtn');
    button.disabled = true;
    resultsDiv.innerHTML = alertHtml('info', 'Ricerca...');
    const extensions = document.getElementById('extensions').value;
    try {
        const data = await apiJson('/search', 'POST', {
            question,
            k: Number(document.getElementById('topK').value),
            folder: document.getElementById('folder').value.trim(),
            extensions: extensions ? extensions.split(',') : [],
        });
        if (!data.results.length) {
            resultsDiv.innerHTML = alertHtml('secondary', 'Nessun risultato: la wiki è vuota o il filtro esclude tutto');
            return;
        }
        resultsDiv.innerHTML = `<div class="small text-muted mb-2">${data.passages} passaggi in ${data.results.length} file,
            dal più simile alla domanda</div>` + data.results.map((r, i) => resultHtml(r, i + 1)).join('');
    } catch (error) {
        resultsDiv.innerHTML = alertHtml('danger', `Ricerca non riuscita: ${escapeHtml(error.message)}`);
    } finally {
        button.disabled = false;
    }
}

// Cartelle gia' indicizzate come suggerimenti del filtro (primi due livelli dei percorsi)
async function loadFolders() {
    try {
        const files = (await apiFetch('/files')).files;
        const folders = new Set();
        files.forEach(f => {
            const parts = f.path.split('/').slice(0, -1);
            for (let i = 1; i <= Math.min(parts.length, 2); i++) folders.add(parts.slice(0, i).join('/'));
        });
        document.getElementById('folders').innerHTML = [...folders].sort()
            .map(f => `<option value="${escapeHtml(f)}">`).join('');
    } catch (e) { /* senza chiave o wiki vuota: niente suggerimenti */ }
}

document.addEventListener('DOMContentLoaded', () => {
    setupApiKeyField();
    document.getElementById('apiKey').addEventListener('change', loadFolders);
    document.getElementById('searchBtn').addEventListener('click', search);
    document.getElementById('question').addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); search(); }
    });
    startHealthMonitoring();
    loadFolders();
});

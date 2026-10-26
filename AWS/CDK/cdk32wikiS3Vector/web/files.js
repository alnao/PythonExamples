// Pagina dei file: caricamento (POST prefirmato verso S3), elenco con stato, parti, cancellazione, reindex

const POLL_MS = 2000;
const POLL_MAX = 75;            // 2,5 minuti: la Lambda di indicizzazione ha 2 minuti
const MAX_ROWS = 500;           // righe mostrate nella tabella (il filtro restringe)
const STATE_BADGES = { ready: 'success', processing: 'info', uploading: 'secondary', error: 'danger' };

let files = [];
let maxFileKb = 1024;

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function showAlert(type, message) {
    const div = document.getElementById('alert');
    div.innerHTML = alertHtml(type, escapeHtml(message));
    setTimeout(() => { div.innerHTML = ''; }, 6000);
}

async function loadInfo() {
    try {
        const info = await (await fetch(`${API}/info`)).json();
        maxFileKb = info.max_file_kb || maxFileKb;
    } catch (e) { /* resta il default */ }
    document.getElementById('maxFile').textContent = `${maxFileKb} KB`;
}

// ---------------------------------------------------------------- caricamento

function destinationPath() {
    const file = document.getElementById('fileInput').files[0];
    const folder = document.getElementById('destFolder').value.trim().replace(/^\/+|\/+$/g, '');
    if (!file) return '';
    return folder ? `${folder}/${file.name}` : file.name;
}

function updateDestPath() {
    document.getElementById('destPath').textContent = destinationPath() || '-';
}

/* Errore restituito da S3 (XML <Error><Code>..</Code><Message>..</Message>) in parole semplici */
function s3ErrorMessage(status, body) {
    const doc = new DOMParser().parseFromString(body || '', 'application/xml');
    const code = doc.querySelector('Code')?.textContent || '';
    const message = doc.querySelector('Message')?.textContent || '';
    if (code === 'EntityTooLarge') return `il file supera il massimo di ${maxFileKb} KB`;
    if (code === 'AccessDenied' && /expired/i.test(message)) return 'autorizzazione al caricamento scaduta: riprova';
    if (code) return `S3 ha rifiutato il file (${code}${message ? ': ' + message : ''})`;
    return `upload su S3 non riuscito (HTTP ${status})`;
}

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

async function waitForIndex(path, resultDiv) {
    for (let i = 0; i < POLL_MAX; i++) {
        await sleep(POLL_MS);
        const status = await apiFetch(`/files/status?path=${encodeURIComponent(path)}`);
        if (status.state === 'ready' || status.state === 'error') return status;
        resultDiv.innerHTML = alertHtml('info', `Indicizzazione in corso (${escapeHtml(status.state)})...`);
    }
    throw new Error('indicizzazione ancora in corso: aggiorna l\'elenco tra poco');
}

async function uploadFile() {
    const resultDiv = document.getElementById('uploadResult');
    const file = document.getElementById('fileInput').files[0];
    if (!file) {
        resultDiv.innerHTML = alertHtml('warning', 'Scegli un file');
        return;
    }
    if (file.size > maxFileKb * 1024) {
        resultDiv.innerHTML = alertHtml('warning', `Il file pesa ${Math.ceil(file.size / 1024)} KB: il massimo è ${maxFileKb} KB`);
        return;
    }
    // file di testo: un byte e' circa un carattere
    if (!confirmCost(`L'indicizzazione di "${file.name}" (${Math.ceil(file.size / 1024)} KB)`,
                     tokensCost(file.size * CHUNK_OVERHEAD / CHARS_PER_TOKEN))) {
        resultDiv.innerHTML = alertHtml('secondary', 'Caricamento annullato');
        return;
    }
    const button = document.getElementById('uploadBtn');
    button.disabled = true;
    try {
        const created = await apiJson('/uploads', 'POST', { path: destinationPath() });
        await uploadToS3(created.upload, file, (loaded, total) => {
            resultDiv.innerHTML = alertHtml('info', `Caricamento su S3: ${Math.floor(loaded * 100 / total)}%`);
        });
        resultDiv.innerHTML = alertHtml('info', 'File caricato, indicizzazione in corso...');
        const status = await waitForIndex(created.path, resultDiv);
        if (status.state === 'error') throw new Error(status.error);
        resultDiv.innerHTML = alertHtml('success', `<span class="result-path">${escapeHtml(status.path)}</span> indicizzato:
            ${status.lines} righe in ${status.chunks} parti.`);
        document.getElementById('fileInput').value = '';
        updateDestPath();
        await loadFiles();
    } catch (error) {
        resultDiv.innerHTML = alertHtml('danger', `Caricamento non riuscito: ${escapeHtml(error.message)}`);
    } finally {
        button.disabled = false;
    }
}

// ---------------------------------------------------------------- elenco

function stateHtml(f) {
    const badge = `<span class="badge text-bg-${STATE_BADGES[f.state] || 'secondary'}">${escapeHtml(f.state)}</span>`;
    return f.error ? `${badge} <small class="text-danger">${escapeHtml(f.error)}</small>` : badge;
}

function renderFiles() {
    const filter = document.getElementById('filter').value.trim().toLowerCase();
    const visible = files.filter(f => !filter || f.path.toLowerCase().includes(filter));
    document.getElementById('fileCount').textContent = filter ? `${visible.length} di ${files.length}` : files.length;
    const body = document.getElementById('filesBody');
    if (!visible.length) {
        body.innerHTML = `<tr><td colspan="6" class="text-muted">${files.length ? 'Nessun file corrisponde al filtro' : 'La wiki è vuota'}</td></tr>`;
        return;
    }
    body.innerHTML = visible.slice(0, MAX_ROWS).map(f => `
        <tr>
            <td class="result-path small">${escapeHtml(f.path)}</td>
            <td>${stateHtml(f)}</td>
            <td class="text-end">${f.lines ?? ''}</td>
            <td class="text-end">${f.chunks || 0}</td>
            <td><small class="text-muted">${escapeHtml(f.updated || '')}</small></td>
            <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" data-parts="${escapeHtml(f.path)}" title="Mostra le parti" ${f.state === 'ready' ? '' : 'disabled'}><i class="bi bi-eye"></i></button>
                <button class="btn btn-sm btn-outline-danger" data-delete="${escapeHtml(f.path)}" title="Togli il file dalla wiki"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('')
        + (visible.length > MAX_ROWS ? `<tr><td colspan="6" class="text-muted">... altri ${visible.length - MAX_ROWS} file: usa il filtro</td></tr>` : '');
    body.querySelectorAll('[data-parts]').forEach(b => b.addEventListener('click', () => showParts(b.dataset.parts)));
    body.querySelectorAll('[data-delete]').forEach(b => b.addEventListener('click', () => deleteFile(b.dataset.delete, b)));
}

async function loadFiles() {
    try {
        files = (await apiFetch('/files')).files;
        renderFiles();
    } catch (error) {
        document.getElementById('filesBody').innerHTML = `<tr><td colspan="6" class="text-danger">${escapeHtml(error.message)}</td></tr>`;
    }
}

async function showParts(path) {
    const card = document.getElementById('partsCard');
    const body = document.getElementById('partsBody');
    card.classList.remove('d-none');
    document.getElementById('partsTitle').textContent = path;
    body.innerHTML = '<span class="text-muted">Caricamento...</span>';
    try {
        const data = await apiFetch(`/files/parts?path=${encodeURIComponent(path)}`);
        body.innerHTML = data.parts.map(p => `
            <div class="mb-3">
                <span class="badge text-bg-secondary">righe ${p.line_start}-${p.line_end}</span>
                <div class="snippet border rounded p-2 mt-1">${escapeHtml(p.text)}</div>
            </div>`).join('');
        card.scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        body.innerHTML = `<span class="text-danger">${escapeHtml(error.message)}</span>`;
    }
}

async function deleteFile(path, button) {
    if (!confirm(`Togliere "${path}" dalla wiki?\nVengono cancellati il file su S3 e le sue parti.`)) return;
    button.disabled = true;
    try {
        await apiFetch(`/files?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
        showAlert('success', `${path} cancellato: le parti spariscono dall'indice in pochi secondi`);
        document.getElementById('partsCard').classList.add('d-none');
    } catch (error) {
        showAlert('danger', error.message);
    }
    setTimeout(loadFiles, 3000);
}

async function reindex() {
    const chunks = files.reduce((sum, f) => sum + (f.chunks || 0), 0);
    const estimate = tokensCost(chunks * CHUNK_CHARS / CHARS_PER_TOKEN);
    if (!confirm(`Reindicizzare tutti i ${files.length} file?\nGli embedding vengono ricalcolati: ${costText(estimate)}.`)) return;
    try {
        const data = await apiFetch('/reindex', { method: 'POST' });
        showAlert('success', `${data.queued} file rimessi in coda`);
    } catch (error) {
        showAlert('danger', error.message);
    }
    setTimeout(loadFiles, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    setupApiKeyField();
    document.getElementById('apiKey').addEventListener('change', loadFiles);
    document.getElementById('fileInput').addEventListener('change', updateDestPath);
    document.getElementById('destFolder').addEventListener('input', updateDestPath);
    document.getElementById('uploadBtn').addEventListener('click', uploadFile);
    document.getElementById('filter').addEventListener('input', renderFiles);
    document.getElementById('reloadBtn').addEventListener('click', loadFiles);
    document.getElementById('reindexBtn').addEventListener('click', reindex);
    startHealthMonitoring();
    loadInfo();
    loadFiles();
});

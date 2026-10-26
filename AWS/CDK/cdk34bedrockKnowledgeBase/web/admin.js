// Pagina di amministrazione: documenti con lo stato della Knowledge Base, cancellazione, sincronizzazioni

let documents = [];

const STATUS_BADGES = {
    INDEXED: 'success', PARTIALLY_INDEXED: 'warning', FAILED: 'danger', IGNORED: 'danger',
    STARTING: 'info', IN_PROGRESS: 'info', PENDING: 'info', NOT_SYNCED: 'secondary',
    COMPLETE: 'success', STOPPED: 'secondary',
};

function showAlert(type, message) {
    const div = document.getElementById('alert');
    div.innerHTML = alertHtml(type, escapeHtml(message));
    setTimeout(() => { div.innerHTML = ''; }, 6000);
}

function badgeHtml(status) {
    return `<span class="badge text-bg-${STATUS_BADGES[status] || 'secondary'}">${escapeHtml(status)}</span>`;
}

function statusHtml(d) {
    const reason = d.reason ? `<div class="doc-reason text-danger">${escapeHtml(d.reason)}</div>` : '';
    const waiting = d.status === 'NOT_SYNCED' ? '<div class="doc-reason text-muted">in attesa della sincronizzazione</div>' : '';
    return badgeHtml(d.status) + reason + waiting;
}

const kilobytes = bytes => `${(bytes / 1024).toLocaleString('it-IT', { maximumFractionDigits: 1 })} KB`;

async function loadDocuments() {
    const body = document.getElementById('docsBody');
    try {
        documents = (await apiFetch('/documents')).documents;
    } catch (error) {
        body.innerHTML = `<tr><td colspan="6" class="text-danger">${escapeHtml(error.message)}</td></tr>`;
        return;
    }
    document.getElementById('docCount').textContent = documents.length;
    if (!documents.length) {
        body.innerHTML = '<tr><td colspan="6" class="text-muted">Nessun documento</td></tr>';
        return;
    }
    body.innerHTML = documents.map((d, i) => `
        <tr>
            <td class="font-monospace">${escapeHtml(d.doc_id)}</td>
            <td>${escapeHtml(d.filename)}</td>
            <td>${statusHtml(d)}</td>
            <td><small class="text-muted">${escapeHtml(d.uploaded)}</small></td>
            <td class="text-end">${kilobytes(d.size)}</td>
            <td class="text-end">
                <button class="btn btn-sm btn-outline-danger" data-forget="${i}" title="Fai dimenticare il documento"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');
    body.querySelectorAll('[data-forget]').forEach(b => b.addEventListener('click', () => forget(documents[b.dataset.forget], b)));
}

async function loadJobs() {
    const body = document.getElementById('jobsBody');
    try {
        const jobs = (await apiFetch('/sync')).jobs;
        body.innerHTML = jobs.length ? jobs.map(j => `
            <tr>
                <td><small>${escapeHtml(j.started)}</small></td>
                <td>${badgeHtml(j.status)}</td>
                <td><small class="text-muted">${escapeHtml(j.description)}</small></td>
                <td class="text-end">${j.scanned}</td>
                <td class="text-end">${j.indexed}</td>
                <td class="text-end">${j.deleted}</td>
                <td class="text-end">${j.failed}</td>
            </tr>`).join('') : '<tr><td colspan="7" class="text-muted">Nessuna sincronizzazione</td></tr>';
    } catch (error) {
        body.innerHTML = `<tr><td colspan="7" class="text-danger">${escapeHtml(error.message)}</td></tr>`;
    }
}

async function forget(doc, button) {
    if (!confirm(`Far dimenticare all'IA il documento "${doc.doc_id}" (${doc.filename})?\nIl file viene cancellato da S3 e la sincronizzazione toglie le sue parti dall'indice.`)) return;
    button.disabled = true;
    try {
        const data = await apiFetch(`/documents/${encodeURIComponent(doc.doc_id)}`, { method: 'DELETE' });
        showAlert('success', `Documento ${data.doc_id} cancellato (${data.deleted_files} file): sparisce dall'indice con la prossima sincronizzazione`);
    } catch (error) {
        showAlert('danger', error.message);
    }
    await reload();
}

async function startSync() {
    const button = document.getElementById('syncBtn');
    button.disabled = true;
    try {
        await apiFetch('/sync', { method: 'POST' });
        showAlert('success', 'Sincronizzazione avviata: i costi sono solo per gli embedding dei file nuovi o cambiati');
    } catch (error) {
        showAlert('danger', error.message);
    } finally {
        button.disabled = false;
    }
    setTimeout(reload, 2000);
}

function reload() {
    return Promise.all([loadDocuments(), loadJobs()]);
}

document.addEventListener('DOMContentLoaded', () => {
    setupApiKeyField();
    document.getElementById('apiKey').addEventListener('change', reload);
    document.getElementById('reloadBtn').addEventListener('click', reload);
    document.getElementById('syncBtn').addEventListener('click', startSync);
    startHealthMonitoring();
    reload();
});

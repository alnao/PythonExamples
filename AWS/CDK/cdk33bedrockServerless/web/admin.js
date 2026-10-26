// Pagina di amministrazione (serverless): documenti con il loro stato, parti, "dimentica", reindex

let documents = [];

const STATE_BADGES = { ready: 'success', processing: 'info', uploading: 'secondary', error: 'danger' };

function showAlert(type, message) {
    const div = document.getElementById('alert');
    div.innerHTML = alertHtml(type, escapeHtml(message));
    setTimeout(() => { div.innerHTML = ''; }, 6000);
}

function stateHtml(d) {
    const badge = `<span class="badge text-bg-${STATE_BADGES[d.state] || 'secondary'}">${escapeHtml(d.state)}</span>`;
    return d.error ? `${badge} <small class="text-danger">${escapeHtml(d.error)}</small>` : badge;
}

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
            <td>${stateHtml(d)}</td>
            <td><small class="text-muted">${escapeHtml(d.updated || '')}</small></td>
            <td class="text-end">${d.chunks || 0}</td>
            <td class="text-end text-nowrap">
                <button class="btn btn-sm btn-outline-secondary" data-show="${i}" title="Mostra le parti" ${d.state === 'ready' ? '' : 'disabled'}><i class="bi bi-eye"></i></button>
                <button class="btn btn-sm btn-outline-danger" data-forget="${i}" title="Fai dimenticare il documento"><i class="bi bi-trash"></i></button>
            </td>
        </tr>`).join('');
    body.querySelectorAll('[data-show]').forEach(b => b.addEventListener('click', () => showChunks(documents[b.dataset.show])));
    body.querySelectorAll('[data-forget]').forEach(b => b.addEventListener('click', () => forget(documents[b.dataset.forget], b)));
}

async function showChunks(doc) {
    const card = document.getElementById('chunksCard');
    const body = document.getElementById('chunksBody');
    card.classList.remove('d-none');
    document.getElementById('chunksTitle').textContent = `${doc.doc_id} (${doc.filename})`;
    body.innerHTML = '<span class="text-muted">Caricamento...</span>';
    try {
        const data = await apiFetch(`/documents/${encodeURIComponent(doc.doc_id)}`);
        body.innerHTML = data.chunks.map(c => `
            <div class="mb-3">
                <span class="badge text-bg-secondary">parte ${c.chunk + 1}</span>
                <div class="chunk-text border rounded p-2 mt-1 bg-white">${escapeHtml(c.text)}</div>
            </div>`).join('');
    } catch (error) {
        body.innerHTML = `<span class="text-danger">${escapeHtml(error.message)}</span>`;
    }
}

async function forget(doc, button) {
    if (!confirm(`Far dimenticare all'IA il documento "${doc.doc_id}" (${doc.filename})?\nVengono cancellati anche il file su S3 e le sue parti.`)) return;
    button.disabled = true;
    try {
        const data = await apiFetch(`/documents/${encodeURIComponent(doc.doc_id)}`, { method: 'DELETE' });
        showAlert('success', `Documento ${data.doc_id} dimenticato (${data.deleted_chunks} parti)`);
        document.getElementById('chunksCard').classList.add('d-none');
    } catch (error) {
        showAlert('danger', error.message);
    }
    await loadDocuments();
}

async function reindex() {
    const estimate = textEmbeddingCost(documents.reduce((sum, d) => sum + (d.text_length || 0), 0));
    if (!confirm(`Reindicizzare tutti i file salvati su S3?\nGli embedding vengono ricalcolati: ${costText(estimate, 'Titan Embeddings')}.`)) return;
    const button = document.getElementById('reindexBtn');
    button.disabled = true;
    try {
        const data = await apiFetch('/reindex', { method: 'POST' });
        showAlert('success', `${data.queued.length} file rimessi in coda: lo stato si aggiorna in pochi secondi`);
    } catch (error) {
        showAlert('danger', error.message);
    } finally {
        button.disabled = false;
    }
    setTimeout(loadDocuments, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
    setupApiKeyField();
    document.getElementById('apiKey').addEventListener('change', loadDocuments);
    document.getElementById('reloadBtn').addEventListener('click', loadDocuments);
    document.getElementById('reindexBtn').addEventListener('click', reindex);
    startHealthMonitoring();
    loadDocuments();
});

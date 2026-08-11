/*
 * AWS Tag Manager - logica della pagina.
 *
 * Il server restituisce le risorse gia' filtrate per tag (filtri lato AWS/Python),
 * mentre ricerca testuale, filtro per servizio e paginazione sono gestiti qui
 * per non dover rileggere le risorse da AWS ad ogni digitazione.
 */

const PAGE_SIZE = 50;

const state = {
    resources: [],      // risorse restituite dall'ultima chiamata
    visible: [],        // risorse dopo ricerca testuale e filtro servizio
    selected: new Set(),
    page: 1,
    tagTargets: [],     // ARN su cui agisce la modale dei tag
};

// ---------------------------------------------------------------- utility

const $ = (id) => document.getElementById(id);

/* Escape valido sia dentro il testo sia dentro gli attributi (virgolette comprese). */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function currentContext() {
    return { region: $('region').value, profile: $('profile').value };
}

/* Etichette della colonna "Origine": da quale API arriva la risorsa. */
const SOURCE_LABELS = {
    tagging: { testo: 'API tag', classe: 'bg-primary-subtle text-primary-emphasis',
               titolo: 'Trovata dalla Tagging API: e\' taggabile' },
    explorer: { testo: 'Explorer', classe: 'bg-warning-subtle text-warning-emphasis',
                titolo: 'Trovata solo da Resource Explorer: mai taggata, il tagging potrebbe non essere supportato' },
    both: { testo: 'Entrambe', classe: 'bg-success-subtle text-success-emphasis',
            titolo: 'Presente in entrambe le sorgenti' },
};

function showSpinner(show) {
    let overlay = document.querySelector('.spinner-overlay');
    if (show && !overlay) {
        overlay = document.createElement('div');
        overlay.className = 'spinner-overlay';
        overlay.innerHTML = '<div class="spinner-border text-primary" style="width:3rem;height:3rem"></div>';
        document.body.appendChild(overlay);
    } else if (!show && overlay) {
        overlay.remove();
    }
}

function showAlert(message, type = 'success', container = 'alertBox') {
    $(container).innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show py-2" role="alert">
            ${escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`;
}

async function apiGet(url) {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Errore sconosciuto');
    return data;
}

async function apiPost(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Errore sconosciuto');
    return data;
}

// ---------------------------------------------------------------- caricamento

async function loadResources(refresh = false) {
    const ctx = currentContext();
    const mode = $('filterMode').value;
    const params = new URLSearchParams({
        region: ctx.region,
        profile: ctx.profile,
        source: $('source').value,
        filter_mode: mode,
        tag_key: $('filterTagKey').value.trim(),
        tag_value: $('filterTagValue').value.trim(),
    });
    if (refresh) params.set('refresh', '1');

    if ((mode === 'with_key' || mode === 'without_key' || mode === 'with_key_value')
        && !$('filterTagKey').value.trim()) {
        showAlert('Indicare la chiave del tag da usare come filtro', 'warning');
        return;
    }

    showSpinner(true);
    try {
        const data = await apiGet('/api/resources?' + params.toString());
        state.resources = data.resources;
        state.selected.clear();
        state.page = 1;

        renderSummary(data.summary);
        populateServiceFilter(data.summary.services);
        applyClientFilters();

        const origine = data.cached ? 'da cache' : 'lette da AWS';
        const soloExplorer = data.summary.sources.explorer || 0;
        const dettaglio = soloExplorer
            ? ` Di queste, ${soloExplorer} sono visibili solo tramite Resource Explorer `
              + '(mai taggate, quindi assenti dalla Tagging API).'
            : '';
        showAlert(`${data.filtered_count} risorse mostrate su ${data.summary.total} totali `
            + `nella region ${data.region} (${origine}).${dettaglio}`, 'info');

        // I problemi della sorgente Resource Explorer non bloccano il caricamento,
        // ma vanno detti: altrimenti l'elenco sembra completo quando non lo e'.
        if ((data.warnings || []).length > 0) {
            $('alertBox').insertAdjacentHTML('beforeend', `
                <div class="alert alert-warning alert-dismissible fade show py-2" role="alert">
                    <i class="fas fa-triangle-exclamation me-1"></i>
                    ${data.warnings.map(escapeHtml).join('<br>')}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>`);
        }
    } catch (e) {
        showAlert('Errore nel caricamento: ' + e.message, 'danger');
        state.resources = [];
        applyClientFilters();
    } finally {
        showSpinner(false);
    }
}

async function loadTagKeys() {
    const ctx = currentContext();
    try {
        const data = await apiGet(`/api/tag-keys?region=${ctx.region}&profile=${ctx.profile}`);
        $('tagKeysList').innerHTML = data.tag_keys
            .map((k) => `<option value="${escapeHtml(k)}">`).join('');
    } catch (e) {
        // I suggerimenti sono un extra: se falliscono non si blocca la pagina.
        console.warn('Impossibile leggere le chiavi tag:', e.message);
    }
}

async function loadTagValues(key) {
    if (!key) return;
    const ctx = currentContext();
    try {
        const data = await apiGet(
            `/api/tag-values?region=${ctx.region}&profile=${ctx.profile}&key=${encodeURIComponent(key)}`);
        $('tagValuesList').innerHTML = data.tag_values
            .map((v) => `<option value="${escapeHtml(v)}">`).join('');
    } catch (e) {
        console.warn('Impossibile leggere i valori del tag:', e.message);
    }
}

// ---------------------------------------------------------------- rendering

function renderSummary(summary) {
    $('statTotal').textContent = summary.total;
    $('statUntagged').textContent = summary.untagged;
    $('statTagged').textContent = summary.tagged;
    $('statServices').textContent = Object.keys(summary.services).length;
    $('statTagKeys').textContent = Object.keys(summary.tag_keys).length;
    $('summaryRow').classList.remove('d-none');
}

function populateServiceFilter(services) {
    const select = $('serviceFilter');
    const corrente = select.value;
    select.innerHTML = '<option value="">Tutti i servizi</option>'
        + Object.entries(services)
            .map(([s, n]) => `<option value="${escapeHtml(s)}">${escapeHtml(s)} (${n})</option>`)
            .join('');
    select.value = corrente;
}

function applyClientFilters() {
    const testo = $('searchBox').value.trim().toLowerCase();
    const servizio = $('serviceFilter').value;

    state.visible = state.resources.filter((r) => {
        if (servizio && r.service !== servizio) return false;
        if (!testo) return true;
        const tagText = Object.entries(r.tags).map(([k, v]) => `${k}=${v}`).join(' ');
        return (r.name + ' ' + r.arn + ' ' + tagText).toLowerCase().includes(testo);
    });

    state.page = 1;
    renderTable();
}

/* Chiave e valore del tag rapido, quelli scritti nella barra sopra la tabella. */
function fastTag() {
    return { key: $('fastTagKey').value.trim(), value: $('fastTagValue').value.trim() };
}

/*
 * Aspetto del pulsante fulmine per una riga: il tagging su AWS e' la stessa
 * operazione in entrambi i casi (tag_resources sovrascrive), ma il pulsante deve
 * far vedere prima se sta aggiungendo una chiave nuova o cambiando un valore.
 */
function fastTagButtonState(r) {
    const { key, value } = fastTag();

    // Alcune risorse AWS non accettano proprio i tag (layer Lambda, versioni e
    // alias di funzione): meglio spegnere il pulsante che far fallire la chiamata.
    if (r.taggable === false) {
        return { classe: 'btn-outline-secondary', icona: 'fa-ban', disabilitato: true,
                 titolo: r.reason || 'Risorsa non taggabile' };
    }
    if (!key) {
        return { classe: 'btn-outline-secondary', icona: 'fa-bolt', disabilitato: true,
                 titolo: 'Compila chiave e valore del tag rapido per usare questo pulsante' };
    }
    const attuale = r.tags[key];
    if (attuale === undefined) {
        return { classe: 'btn-outline-success', icona: 'fa-bolt', disabilitato: false,
                 titolo: `Aggiunge il tag ${key} = ${value}` };
    }
    if (attuale === value) {
        return { classe: 'btn-outline-secondary', icona: 'fa-check', disabilitato: true,
                 titolo: `Il tag ${key} vale gia' ${value}` };
    }
    return { classe: 'btn-warning', icona: 'fa-pen-to-square', disabilitato: false,
             titolo: `Aggiorna il tag ${key}: da "${attuale}" a "${value}"` };
}

function renderTable() {
    const body = $('resourcesBody');

    if (state.visible.length === 0) {
        body.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">'
            + 'Nessuna risorsa corrisponde ai criteri selezionati</td></tr>';
        $('tableInfo').textContent = '0 risorse';
        $('paginationFooter').classList.add('d-none');
        updateSelectionUI();
        return;
    }

    const start = (state.page - 1) * PAGE_SIZE;
    const pagina = state.visible.slice(start, start + PAGE_SIZE);

    body.innerHTML = pagina.map((r) => {
        const tags = Object.keys(r.tags).length === 0
            ? '<span class="badge no-tag-badge"><i class="fas fa-triangle-exclamation me-1"></i>nessun tag</span>'
            : Object.entries(r.tags).map(([k, v]) =>
                `<span class="badge tag-badge"><span class="tag-key">${escapeHtml(k)}</span>: ${escapeHtml(v)}</span>`
            ).join(' ');

        const checked = state.selected.has(r.arn) ? 'checked' : '';
        const src = SOURCE_LABELS[r.source] || SOURCE_LABELS.tagging;
        const fast = fastTagButtonState(r);
        return `
            <tr>
                <td><input type="checkbox" class="form-check-input row-check" data-arn="${escapeHtml(r.arn)}" ${checked}></td>
                <td><span class="badge bg-secondary">${escapeHtml(r.service)}</span></td>
                <td class="text-muted">${escapeHtml(r.resource_type || '-')}</td>
                <td>
                    <div class="resource-name">${escapeHtml(r.name)}</div>
                    <div class="arn-cell">${escapeHtml(r.arn)}</div>
                </td>
                <td>${tags}</td>
                <td><span class="badge ${src.classe}" title="${escapeHtml(src.titolo)}">${src.testo}</span></td>
                <td class="text-end text-nowrap">
                    <button class="btn btn-sm ${fast.classe} btn-fast-tag" data-arn="${escapeHtml(r.arn)}"
                            title="${escapeHtml(fast.titolo)}" ${fast.disabilitato ? 'disabled' : ''}>
                        <i class="fas ${fast.icona}"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary btn-detail" data-arn="${escapeHtml(r.arn)}" title="Dettaglio">
                        <i class="fas fa-circle-info"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-primary btn-tags" data-arn="${escapeHtml(r.arn)}" title="Gestisci tag">
                        <i class="fas fa-tags"></i>
                    </button>
                </td>
            </tr>`;
    }).join('');

    $('tableInfo').textContent = `${state.visible.length} risorse `
        + `(${start + 1}-${Math.min(start + PAGE_SIZE, state.visible.length)})`;

    body.querySelectorAll('.row-check').forEach((cb) =>
        cb.addEventListener('change', onRowCheck));
    body.querySelectorAll('.btn-detail').forEach((btn) =>
        btn.addEventListener('click', () => openDetail(btn.dataset.arn)));
    body.querySelectorAll('.btn-tags').forEach((btn) =>
        btn.addEventListener('click', () => openTagModal([btn.dataset.arn])));
    body.querySelectorAll('.btn-fast-tag').forEach((btn) =>
        btn.addEventListener('click', () => applyFastTag([btn.dataset.arn])));

    renderPagination();
    updateSelectionUI();
}

function renderPagination() {
    const pagine = Math.ceil(state.visible.length / PAGE_SIZE);
    const footer = $('paginationFooter');

    if (pagine <= 1) {
        footer.classList.add('d-none');
        return;
    }
    footer.classList.remove('d-none');

    // Con molte pagine si mostra solo una finestra attorno a quella corrente.
    const numeri = [];
    for (let p = 1; p <= pagine; p++) {
        if (p === 1 || p === pagine || Math.abs(p - state.page) <= 2) numeri.push(p);
        else if (numeri[numeri.length - 1] !== '...') numeri.push('...');
    }

    $('pagination').innerHTML = numeri.map((p) => {
        if (p === '...') return '<li class="page-item disabled"><span class="page-link">...</span></li>';
        const active = p === state.page ? 'active' : '';
        return `<li class="page-item ${active}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
    }).join('');

    $('pagination').querySelectorAll('a').forEach((a) =>
        a.addEventListener('click', (e) => {
            e.preventDefault();
            state.page = parseInt(a.dataset.page, 10);
            renderTable();
        }));
}

// ---------------------------------------------------------------- tag rapido

/*
 * Applica il tag rapido alle risorse indicate.
 *
 * Non ricarica tutto da AWS: aggiorna i tag in memoria e ridisegna la tabella,
 * cosi' il tag rapido resta immediato anche con centinaia di risorse. La cache
 * lato server viene comunque invalidata dall'endpoint, quindi il prossimo
 * caricamento rilegge i dati veri.
 */
async function applyFastTag(arns) {
    const { key, value } = fastTag();
    if (!key) {
        showAlert('Compila la chiave del tag rapido', 'warning');
        return;
    }

    // Sulla selezione multipla si scartano le risorse che AWS rifiuta comunque,
    // altrimenti un layer Lambda farebbe fallire meta' dell'operazione.
    const scartate = arns.filter((a) => (findResource(a) || {}).taggable === false);
    const bersagli = arns.filter((a) => !scartate.includes(a));
    if (bersagli.length === 0) {
        showAlert(`Nessuna delle ${arns.length} risorse selezionate accetta i tag.`, 'warning');
        return;
    }

    showSpinner(true);
    try {
        const data = await apiPost('/api/tags/add',
            { ...currentContext(), arns: bersagli, tags: { [key]: value } });

        data.succeeded.forEach((arn) => {
            const r = findResource(arn);
            if (!r) return;
            r.tags[key] = value;
            r.tag_count = Object.keys(r.tags).length;
            // Se era nota solo a Resource Explorer, ora e' anche nella Tagging API.
            if (r.source === 'explorer') r.source = 'both';
        });
        renderTable();

        const saltate = scartate.length ? ` ${scartate.length} risorsa/e saltata perche' non taggabile.` : '';
        const errori = Object.entries(data.failed || {});
        if (errori.length > 0) {
            showAlert(`${data.message}.${saltate} Primo errore: ${errori[0][0]} -> ${errori[0][1]}`, 'warning');
        } else {
            showAlert(`Tag ${key} = ${value} applicato a ${data.succeeded.length} risorsa/e.${saltate}`,
                'success');
        }
    } catch (e) {
        showAlert('Errore nel tag rapido: ' + e.message, 'danger');
    } finally {
        showSpinner(false);
    }
}

// ---------------------------------------------------------------- selezione

function onRowCheck(e) {
    const arn = e.target.dataset.arn;
    if (e.target.checked) state.selected.add(arn);
    else state.selected.delete(arn);
    updateSelectionUI();
}

function updateSelectionUI() {
    const n = state.selected.size;
    $('selectedCount').textContent = `${n} selezionate`;
    $('bulkActions').classList.toggle('d-none', n === 0);
    $('btnFastTagSelected').classList.toggle('d-none', n === 0);
    $('checkAll').checked = n > 0 && state.visible.every((r) => state.selected.has(r.arn));
}

// ---------------------------------------------------------------- modali

function findResource(arn) {
    return state.resources.find((r) => r.arn === arn);
}

function openDetail(arn) {
    const r = findResource(arn);
    if (!r) return;

    const righe = [
        ['ARN', r.arn],
        ['Nome', r.name],
        ['Servizio', r.service],
        ['Tipo risorsa', r.resource_type || '-'],
        ['Filtro tipo (API)', r.resource_type_filter],
        ['Region', r.region],
        ['Account', r.account],
        ['Numero tag', r.tag_count],
        ['Origine', (SOURCE_LABELS[r.source] || SOURCE_LABELS.tagging).titolo],
        ['Ultimo aggiornamento indice', r.last_reported_at || '-'],
        ['Taggabile', r.taggable === false
            ? `No - ${r.reason}` + (r.alternative ? ` Usare: ${r.alternative}` : '')
            : 'Si'],
    ].map(([k, v]) => `
        <tr><th class="text-nowrap w-25">${escapeHtml(k)}</th>
            <td class="arn-cell">${escapeHtml(v)}</td></tr>`).join('');

    const tags = Object.keys(r.tags).length === 0
        ? '<p class="text-danger mb-0"><i class="fas fa-triangle-exclamation me-1"></i>Risorsa senza tag</p>'
        : '<table class="table table-sm table-bordered mb-0"><thead class="table-light">'
          + '<tr><th>Chiave</th><th>Valore</th></tr></thead><tbody>'
          + Object.entries(r.tags).map(([k, v]) =>
              `<tr><td class="fw-semibold">${escapeHtml(k)}</td><td>${escapeHtml(v)}</td></tr>`).join('')
          + '</tbody></table>';

    $('detailBody').innerHTML = `
        <h6 class="fw-semibold">Dati risorsa</h6>
        <table class="table table-sm table-bordered">${righe}</table>
        <h6 class="fw-semibold mt-4">Tag</h6>
        ${tags}
        <h6 class="fw-semibold mt-4">JSON</h6>
        <pre class="detail-json mb-0">${escapeHtml(JSON.stringify(r, null, 2))}</pre>`;

    bootstrap.Modal.getOrCreateInstance($('detailModal')).show();
}

function openTagModal(arns) {
    state.tagTargets = arns;
    $('tagModalAlert').innerHTML = '';

    // Risorse che AWS rifiuta a priori: si dice subito quali e perche'.
    const nonTaggabili = arns.map(findResource).filter((r) => r && r.taggable === false);
    if (nonTaggabili.length > 0) {
        const alternativa = nonTaggabili.find((r) => r.alternative);
        $('tagModalAlert').innerHTML = `
            <div class="alert alert-danger py-2 small mb-3">
                <i class="fas fa-ban me-1"></i>
                ${nonTaggabili.length} risorsa/e non accetta i tag: ${escapeHtml(nonTaggabili[0].reason)}
                ${alternativa ? '<br>Usare invece: <code>' + escapeHtml(alternativa.alternative) + '</code>' : ''}
            </div>`;
    }

    // Le risorse trovate solo da Resource Explorer non sono mai passate dalla
    // Tagging API: alcune non supportano il tagging e l'operazione fallira' lato AWS.
    const soloExplorer = arns.filter((a) => (findResource(a) || {}).source === 'explorer');
    if (soloExplorer.length > 0 && nonTaggabili.length === 0) {
        $('tagModalAlert').innerHTML = `
            <div class="alert alert-warning py-2 small mb-3">
                <i class="fas fa-triangle-exclamation me-1"></i>
                ${soloExplorer.length} risorsa/e proviene solo da Resource Explorer e non e' mai stata
                taggata: se il tipo di risorsa non supporta la Tagging API l'operazione fallira'
                e l'errore verra' mostrato qui.
            </div>`;
    }

    $('newTagKey').value = '';
    $('newTagValue').value = '';
    $('removeTagKey').value = '';

    if (arns.length === 1) {
        const r = findResource(arns[0]);
        $('tagModalTarget').innerHTML =
            `<strong>${escapeHtml(r.name)}</strong><br><span class="arn-cell">${escapeHtml(r.arn)}</span>`;
        $('currentTags').innerHTML = Object.keys(r.tags).length === 0
            ? '<p class="text-muted mb-0">Nessun tag presente su questa risorsa.</p>'
            : Object.entries(r.tags).map(([k, v]) => `
                <div class="d-flex align-items-center border rounded px-2 py-1 mb-1">
                    <div class="flex-grow-1">
                        <span class="fw-semibold">${escapeHtml(k)}</span> = ${escapeHtml(v)}
                    </div>
                    <button class="btn btn-sm btn-outline-danger btn-del-tag" data-key="${escapeHtml(k)}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>`).join('');

        $('currentTags').querySelectorAll('.btn-del-tag').forEach((btn) =>
            btn.addEventListener('click', () => removeTags([btn.dataset.key])));
    } else {
        $('tagModalTarget').innerHTML =
            `<strong>${arns.length} risorse selezionate.</strong> `
            + 'Le operazioni verranno applicate a tutte.';
        $('currentTags').innerHTML =
            '<p class="text-muted mb-0">Selezione multipla: i tag attuali non sono mostrati.</p>';
    }

    bootstrap.Modal.getOrCreateInstance($('tagModal')).show();
}

// ---------------------------------------------------------------- scrittura tag

async function addTag() {
    const key = $('newTagKey').value.trim();
    const value = $('newTagValue').value.trim();
    if (!key) {
        showAlert('La chiave del tag e\' obbligatoria', 'warning', 'tagModalAlert');
        return;
    }

    showSpinner(true);
    try {
        const data = await apiPost('/api/tags/add', {
            ...currentContext(),
            arns: state.tagTargets,
            tags: { [key]: value },
        });
        await afterTagChange(data);
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger', 'tagModalAlert');
    } finally {
        showSpinner(false);
    }
}

async function removeTags(keys) {
    const chiavi = keys.filter((k) => k);
    if (chiavi.length === 0) {
        showAlert('Indicare almeno una chiave da rimuovere', 'warning', 'tagModalAlert');
        return;
    }
    if (!confirm(`Rimuovere i tag [${chiavi.join(', ')}] da ${state.tagTargets.length} risorsa/e?`)) return;

    showSpinner(true);
    try {
        const data = await apiPost('/api/tags/remove', {
            ...currentContext(),
            arns: state.tagTargets,
            tag_keys: chiavi,
        });
        await afterTagChange(data);
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger', 'tagModalAlert');
    } finally {
        showSpinner(false);
    }
}

/* Dopo una modifica: mostra l'esito, chiude la modale e rilegge le risorse. */
async function afterTagChange(data) {
    const errori = Object.entries(data.failed || {});
    if (errori.length > 0) {
        showAlert(data.message + ' - primo errore: ' + errori[0][1], 'warning', 'tagModalAlert');
    } else {
        bootstrap.Modal.getOrCreateInstance($('tagModal')).hide();
        showAlert(data.message, 'success');
    }
    await loadResources(true);
    await loadTagKeys();
}

// ---------------------------------------------------------------- eventi

function onFilterModeChange() {
    const mode = $('filterMode').value;
    const serveChiave = ['with_key', 'without_key', 'with_key_value'].includes(mode);
    const serveValore = mode === 'with_key_value';
    document.querySelector('.tag-filter-input').classList.toggle('d-none', !serveChiave);
    document.querySelector('.tag-value-input').classList.toggle('d-none', !serveValore);
}

document.addEventListener('DOMContentLoaded', () => {
    onFilterModeChange();
    loadTagKeys();

    $('btnLoad').addEventListener('click', () => loadResources(false));
    $('btnRefresh').addEventListener('click', () => loadResources(true));
    $('filterMode').addEventListener('change', onFilterModeChange);
    // Cambiare sorgente ricarica subito, se qualcosa e' gia' stato caricato.
    $('source').addEventListener('change', () => {
        if (state.resources.length > 0) loadResources(false);
    });
    $('searchBox').addEventListener('input', applyClientFilters);
    $('serviceFilter').addEventListener('change', applyClientFilters);

    $('region').addEventListener('change', loadTagKeys);
    $('profile').addEventListener('change', loadTagKeys);
    $('filterTagKey').addEventListener('change', () => loadTagValues($('filterTagKey').value.trim()));

    $('checkAll').addEventListener('change', (e) => {
        state.visible.forEach((r) => {
            if (e.target.checked) state.selected.add(r.arn);
            else state.selected.delete(r.arn);
        });
        renderTable();
    });

    // I pulsanti di riga cambiano aspetto in base al tag rapido scritto: si ridisegna.
    $('fastTagKey').addEventListener('input', renderTable);
    $('fastTagValue').addEventListener('input', renderTable);
    $('btnFastTagSelected').addEventListener('click', () => applyFastTag([...state.selected]));

    $('btnBulkAdd').addEventListener('click', () => openTagModal([...state.selected]));
    $('btnBulkRemove').addEventListener('click', () => openTagModal([...state.selected]));
    $('btnAddTag').addEventListener('click', addTag);
    $('btnRemoveTag').addEventListener('click', () =>
        removeTags($('removeTagKey').value.split(',').map((k) => k.trim())));

    $('btnRefreshRegions').addEventListener('click', async () => {
        if (!confirm('Rileggere da AWS le region abilitate e salvarle in config.json?')) return;
        showSpinner(true);
        try {
            const data = await apiPost('/api/regions/refresh', currentContext());
            showAlert(data.message + ' - ricaricare la pagina per vedere la nuova lista.', 'success');
        } catch (e) {
            showAlert('Errore: ' + e.message, 'danger');
        } finally {
            showSpinner(false);
        }
    });
});

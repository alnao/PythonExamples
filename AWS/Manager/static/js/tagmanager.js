/*
 * Tag Manager - logica della pagina (ex AWS/Managers/TagManager).
 *
 * Il server restituisce le risorse gia' filtrate per tag (filtri lato AWS/Python),
 * mentre ricerca testuale, filtro per servizio e paginazione sono gestiti qui
 * per non dover rileggere le risorse da AWS ad ogni digitazione.
 *
 * Profilo e region sono quelli scelti nella pagina (APP.profile, APP.region); con la
 * region "Tutte" ogni risorsa porta la sua region, che viene mandata con le modifiche.
 * Ogni modifica dei tag chiede conferma (confirmAction in common.js).
 */

const PAGE_SIZE = APP.pageSize || 50;

const state = {
    resources: [],      // risorse restituite dall'ultima chiamata
    visible: [],        // risorse dopo ricerca testuale e filtro servizio
    selected: new Set(),
    page: 1,
    tagTargets: [],     // ARN su cui agisce la modale dei tag
    expandedArn: new Set(),  // ARN per cui è visibile l'ARN nella tabella
    suggestedTagKeys: [],    // tag consigliati da config.json
    suggestedTagValues: {},  // valori dei tag suggeriti: {tagName: value}
};

// ---------------------------------------------------------------- utility

function currentContext() {
    return { region: APP.region, profile: APP.profile };
}

/* Corpo delle richieste di modifica: con "Tutte" serve la region di ogni ARN. */
function tagRequest(arns, extra) {
    const regions = {};
    arns.forEach((a) => { regions[a] = (findResource(a) || {}).region || ''; });
    return { ...currentContext(), arns, regions, ...extra };
}

/* Testo per le conferme: numero di risorse e, se sono poche, i loro nomi. */
function targetsHtml(arns) {
    const nomi = arns.slice(0, 5).map((a) => {
        const r = findResource(a);
        return `<li>${escapeHtml(r ? r.name : a)} ${r && APP.region === ALL ? regionBadge(r.region) : ''}</li>`;
    }).join('');
    const altre = arns.length > 5 ? `<li class="text-muted">... e altre ${arns.length - 5}</li>` : '';
    return `<ul class="mb-0 mt-2">${nomi}${altre}</ul>`;
}

function tagsHtml(tags) {
    return Object.entries(tags).map(([k, v]) =>
        `<span class="badge tag-badge"><span class="tag-key">${escapeHtml(k)}</span>: ${escapeHtml(v)}</span>`).join(' ');
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

    spinner(true);
    try {
        const data = await apiGet('/api/tags/resources?' + params.toString());
        state.resources = data.resources;
        state.selected.clear();
        state.page = 1;

        renderSummary(data.summary);
        $('statRegions').textContent = ctx.region === ALL
            ? `${new Set(data.resources.map((r) => r.region)).size} region su ${APP.regions.length}` : ctx.region;
        populateServiceFilter(data.summary.services);
        populateProjectFilter();
        applyClientFilters();

        // I problemi della sorgente Resource Explorer non bloccano il caricamento,
        // ma vanno detti: altrimenti l'elenco sembra completo quando non lo e'.
        if ((data.warnings || []).length > 0) {
            $('alertBox').innerHTML = `
                <div class="alert alert-warning alert-dismissible fade show py-2" role="alert">
                    <i class="fas fa-triangle-exclamation me-1"></i>
                    ${data.warnings.map(escapeHtml).join('<br>')}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>`;
        }
    } catch (e) {
        showAlert('Errore nel caricamento: ' + e.message, 'danger');
        state.resources = [];
        applyClientFilters();
    } finally {
        spinner(false);
    }
}

async function loadTagKeys() {
    const ctx = currentContext();
    try {
        const data = await apiGet(`/api/tags/tag-keys?${query(ctx)}`);
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
        const data = await apiGet(`/api/tags/tag-values?${query({ ...ctx, key })}`);
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
    // Le system senza tag non contano come problema: si dice solo quante sono
    const sysUntagged = summary.system_untagged || 0;
    $('statSystemUntagged').textContent = sysUntagged ? `+ ${sysUntagged} system escluse` : '';
    $('statSystemUntagged').classList.toggle('d-none', !sysUntagged);
    $('statTagged').textContent = summary.tagged;
    $('statServices').textContent = Object.keys(summary.services).length;
    $('statTagKeys').textContent = Object.keys(summary.tag_keys).length;
    $('summaryRow').classList.remove('d-none');
}

/*
 * Opzioni del filtro Project: i valori fissi di config, ognuno seguito dalle
 * sottovoci trovate nelle risorse caricate (es. "Annotazioni-Ec2" sotto
 * "Annotazioni"), infine "Altri valori". Vedi tag_match.js. Si richiama dopo
 * ogni caricamento perche' le sottovoci dipendono dalle risorse lette.
 */
function populateProjectFilter() {
    const select = $('projectFilter');
    const corrente = select.value;
    select.innerHTML = suggestedFilterOptions('Project', state.resources, 'Tutti i Project');
    select.value = corrente;
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
    const hideSystem = $('hideSystemResources').checked;
    const project = $('projectFilter').value;

    state.visible = state.resources.filter((r) => {
        // Filtra risorse system se il flag è attivo
        if (hideSystem && r.is_system) return false;
        
        // Filtra per servizio
        if (servizio && r.service !== servizio) return false;

        // Filtra per Project (stessa logica del report): uguaglianza stretta con
        // la voce scelta; '__other__' = valore presente ma non in tendina
        if (project) {
            const have = r.tags.Project;
            if (project === '__other__') {
                if (have === undefined || have === null) return false;
                if (isSuggestedValue('Project', have)) return false;
            } else if ((have || '') !== project) {
                return false;
            }
        }
        
        // Filtra per testo
        if (!testo) return true;
        const tagText = Object.entries(r.tags).map(([k, v]) => `${k}=${v}`).join(' ');
        return (r.name + ' ' + r.arn + ' ' + tagText).toLowerCase().includes(testo);
    });

    // Prima le risorse con almeno un tag obbligatorio mancante (quelle su cui
    // bisogna intervenire), poi le altre; dentro ogni gruppo in ordine alfabetico.
    state.visible.sort((a, b) => {
        const mancaA = getMissingTags(a).length > 0 ? 0 : 1;
        const mancaB = getMissingTags(b).length > 0 ? 0 : 1;
        if (mancaA !== mancaB) return mancaA - mancaB;
        return (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' });
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

/* Controlla se una risorsa ha tutti i tag obbligatori (tag_manager.required_tags in config.json). */
const REQUIRED_TAGS = APP.requiredTags || ['Project', 'Name', 'Environment', 'ManagedBy'];

function isCompliantByConfig(r) {
    // Controlla se la risorsa ha tutti i tag di almeno un set di compliant_tags
    const compliantSets = (window.compliantTags || {}).sets || [];
    
    return compliantSets.some((tagSet) => {
        // Ogni chiave del set deve esistere con il valore corretto nella risorsa
        return Object.entries(tagSet).every(([key, value]) => {
            return r.tags[key] === value;
        });
    });
}

function getMissingTags(r) {
    // Se è una risorsa di sistema, non controllare i tag
    if (r.is_system) {
        return [];
    }
    
    // Se la risorsa ha tutti i tag di un set compliant, è OK
    if (isCompliantByConfig(r)) {
        return [];
    }
    
    return REQUIRED_TAGS.filter((tag) => !(tag in r.tags));
}

function hasAllRequiredTags(r) {
    return getMissingTags(r).length === 0;
}

function renderTable() {
    const body = $('resourcesBody');

    if (state.visible.length === 0) {
        body.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">'
            + 'Nessuna risorsa corrisponde ai criteri selezionati</td></tr>';
        $('tableInfo').textContent = '0 risorse';
        $('paginationFooter').classList.add('d-none');
        updateSelectionUI();
        return;
    }

    const start = (state.page - 1) * PAGE_SIZE;
    const pagina = state.visible.slice(start, start + PAGE_SIZE);

    body.innerHTML = pagina.map((r) => {
        const checked = state.selected.has(r.arn) ? 'checked' : '';
        const src = SOURCE_LABELS[r.source] || SOURCE_LABELS.tagging;
        const fast = fastTagButtonState(r);
        
        // Controllo tag obbligatori
        const missingTags = getMissingTags(r);
        const hasAllTags = hasAllRequiredTags(r);
        const rowClass = hasAllTags ? '' : 'table-danger';
        
        // Mostra ARN se la riga è espansa
        const arnVisible = state.expandedArn.has(r.arn);
        const arnDisplay = arnVisible 
            ? `<div class="arn-cell" style="margin-top: 4px; font-size: 0.75rem;">${escapeHtml(r.arn)}</div>` 
            : '';
        
        // Colonna Tag: mostra system badge MA anche i tag se presenti
        let tagContent = '';
        if (r.is_system) {
            tagContent += '<span class="badge bg-success"><i class="fas fa-cog me-1"></i>system</span> ';
        }
        if (Object.keys(r.tags).length === 0) {
            // Non mostrare "nessun tag" per le risorse di sistema
            if (!r.is_system) {
                tagContent += '<span class="badge no-tag-badge"><i class="fas fa-triangle-exclamation me-1"></i>nessun tag</span>';
            }
        } else {
            tagContent += Object.entries(r.tags).map(([k, v]) =>
                `<span class="badge tag-badge"><span class="tag-key">${escapeHtml(k)}</span>: ${escapeHtml(v)}</span>`
            ).join(' ');
        }
        
        // Badge dei tag mancanti nella colonna Tag
        if (!r.is_system && missingTags.length > 0) {
            tagContent += `<div style="margin-top: 4px;">${missingTags.map((tag) => 
                `<span class="badge bg-danger" style="font-size: 0.7rem;">manca ${tag}</span>`
              ).join(' ')}</div>`;
        }

        return `
            <tr class="${rowClass}">
                <td><input type="checkbox" class="form-check-input row-check" data-arn="${escapeHtml(r.arn)}" ${checked}></td>
                <td>
                    <span class="badge bg-secondary">${escapeHtml(r.service)}</span>
                    ${APP.region === ALL ? regionBadge(r.region) : ''}
                    <div class="text-muted small" style="margin-top: 2px;">${escapeHtml(r.resource_type || '-')}</div>
                </td>
                <td>
                    <div class="resource-name" style="cursor: pointer;" data-arn="${escapeHtml(r.arn)}" title="Clicca per mostrare/nascondere ARN">
                        ${escapeHtml(r.name)}
                    </div>
                    ${arnDisplay}
                </td>
                <td>${tagContent}</td>
                <td class="text-end text-nowrap">
                    <span class="badge ${src.classe} me-2" title="${escapeHtml(src.titolo)}">${src.testo}</span>
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
    body.querySelectorAll('.resource-name').forEach((el) =>
        el.addEventListener('click', (e) => toggleArnDisplay(e.target.dataset.arn)));
    body.querySelectorAll('.btn-detail').forEach((btn) =>
        btn.addEventListener('click', () => openDetail(btn.dataset.arn)));
    body.querySelectorAll('.btn-tags').forEach((btn) =>
        btn.addEventListener('click', () => openTagModal([btn.dataset.arn])));
    body.querySelectorAll('.btn-fast-tag').forEach((btn) =>
        btn.addEventListener('click', () => applyFastTag([btn.dataset.arn])));

    renderPagination();
    updateSelectionUI();
}

function toggleArnDisplay(arn) {
    if (state.expandedArn.has(arn)) {
        state.expandedArn.delete(arn);
    } else {
        state.expandedArn.add(arn);
    }
    renderTable();
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
    const ok = await confirmAction({
        title: 'Applicare il tag rapido?',
        html: `Il tag ${tagsHtml({ [key]: value })} viene aggiunto (o sovrascritto) su ${bersagli.length} risorsa/e:`
            + targetsHtml(bersagli) + contextHtml(),
        confirmText: 'Applica il tag',
    });
    if (!ok) return;

    spinner(true);
    try {
        const data = await apiPost('/api/tags/add', tagRequest(bersagli, { tags: { [key]: value } }));

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
        spinner(false);
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

    $('newTagKey').value = '';
    $('newTagValue').value = '';
    $('removeTagKey').value = '';

    // Carica i valori dei tag suggeriti dalla risorsa, altrimenti dal config
    if (arns.length === 1) {
        const r = findResource(arns[0]);
        // Per ogni tag suggerito, usa il valore della risorsa se presente, altrimenti vuoto
        state.suggestedTagValues = {};
        state.suggestedTagKeys.forEach((tagKey) => {
            // Se la risorsa ha già questo tag, usa il suo valore
            state.suggestedTagValues[tagKey] = r.tags[tagKey] || '';
        });
    } else {
        // Per selezione multipla, resetta i valori
        state.suggestedTagValues = {};
        state.suggestedTagKeys.forEach((tagKey) => {
            state.suggestedTagValues[tagKey] = '';
        });
    }
    
    renderSuggestedTags();

    if (arns.length === 1) {
        const r = findResource(arns[0]);
        $('tagModalTarget').innerHTML =
            `<div class="mb-1"><strong>Servizio:</strong> <span class="badge bg-secondary">${escapeHtml(r.service)}</span> 
             <strong>Tipo:</strong> <span class="text-muted">${escapeHtml(r.resource_type || '-')}</span></div>
             <div class="mb-1"><strong>Nome:</strong> ${escapeHtml(r.name)}</div>
             <div><strong>ARN:</strong> <span class="arn-cell">${escapeHtml(r.arn)}</span></div>`;
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

function renderSuggestedTags() {
    // Genera le righe per i tag consigliati
    const section = $('suggestedTagsSection');
    if (state.suggestedTagKeys.length === 0) {
        section.innerHTML = '';
        return;
    }
    
    section.innerHTML = state.suggestedTagKeys
        .map((tagKey) => {
            const currentValue = state.suggestedTagValues[tagKey] || '';
            const possibleValues = (window.suggestedTags || {})[tagKey] || [];
            
            let inputHtml = '';
            if (Array.isArray(possibleValues) && possibleValues.length > 0) {
                // Mostra un select con i valori possibili
                inputHtml = `
                    <select class="form-control suggested-tag-input" data-key="${escapeHtml(tagKey)}">
                        <option value="">-- Seleziona --</option>
                        ${possibleValues.map((val) => {
                            const selected = val === currentValue ? 'selected' : '';
                            return `<option value="${escapeHtml(val)}" ${selected}>${escapeHtml(val)}</option>`;
                        }).join('')}
                    </select>`;
            } else {
                // Lista vuota: mostra input text (qualsiasi valore permesso)
                inputHtml = `
                    <input type="text" class="form-control suggested-tag-input" 
                           data-key="${escapeHtml(tagKey)}"
                           value="${escapeHtml(currentValue)}"
                           placeholder="Inserisci valore per ${escapeHtml(tagKey)}">`;
            }
            
            return `
                <div class="row g-2 align-items-end mb-2">
                    <div class="col-md-5">
                        <label class="form-label small mb-1 text-primary"><i class="fas fa-lightbulb me-1"></i>${escapeHtml(tagKey)}</label>
                        <input type="text" class="form-control form-control-sm" value="${escapeHtml(tagKey)}" disabled>
                    </div>
                    <div class="col-md-7">
                        <label class="form-label small mb-1">Valore</label>
                        ${inputHtml}
                    </div>
                </div>`;
        })
        .join('');
}

async function applyAllSuggestedTags() {
    // Raccoglie tutti i tag compilati (da select o input)
    const tags = {};
    document.querySelectorAll('.suggested-tag-input').forEach((element) => {
        const key = element.dataset.key;
        const value = element.value.trim();
        if (value) {
            tags[key] = value;
        }
    });
    
    if (Object.keys(tags).length === 0) {
        showAlert('Nessun tag compilato da applicare', 'warning', 'tagModalAlert');
        return;
    }
    if (!await confirmTagChange(`I tag ${tagsHtml(tags)} vengono aggiunti (o sovrascritti)`)) return;

    spinner(true);
    try {
        const data = await apiPost('/api/tags/add', tagRequest(state.tagTargets, { tags }));
        await afterTagChange(data);
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger', 'tagModalAlert');
    } finally {
        spinner(false);
    }
}

/* Conferma di una modifica fatta dalla modale dei tag (che resta aperta sotto). */
function confirmTagChange(what, danger = false) {
    const n = state.tagTargets.length;
    return confirmAction({
        title: danger ? 'Rimuovere i tag?' : 'Salvare i tag?',
        html: `${what} su ${n} risorsa/e:` + targetsHtml(state.tagTargets) + contextHtml(),
        confirmText: danger ? 'Rimuovi' : 'Salva',
        danger,
    });
}

function removeSuggestedTag(tag) {
    // Non più usato
}

function addSuggestedTag() {
    // Non più usato
}

async function saveSuggestedTags() {
    // Non più usato - i tag vengono applicati direttamente alla risorsa
}

// ---------------------------------------------------------------- scrittura tag

async function addTag() {
    const key = $('newTagKey').value.trim();
    const value = $('newTagValue').value.trim();
    if (!key) {
        showAlert('La chiave del tag e\' obbligatoria', 'warning', 'tagModalAlert');
        return;
    }
    if (!await confirmTagChange(`Il tag ${tagsHtml({ [key]: value })} viene aggiunto (o sovrascritto)`)) return;

    spinner(true);
    try {
        const data = await apiPost('/api/tags/add', tagRequest(state.tagTargets, { tags: { [key]: value } }));
        await afterTagChange(data);
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger', 'tagModalAlert');
    } finally {
        spinner(false);
    }
}

async function removeTags(keys) {
    const chiavi = keys.filter((k) => k);
    if (chiavi.length === 0) {
        showAlert('Indicare almeno una chiave da rimuovere', 'warning', 'tagModalAlert');
        return;
    }
    const elenco = chiavi.map((k) => `<strong>${escapeHtml(k)}</strong>`).join(', ');
    if (!await confirmTagChange(`I tag ${elenco} vengono rimossi`, true)) return;

    spinner(true);
    try {
        const data = await apiPost('/api/tags/remove', tagRequest(state.tagTargets, { tag_keys: chiavi }));
        await afterTagChange(data);
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger', 'tagModalAlert');
    } finally {
        spinner(false);
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

    // Carica i suggested tag keys dal rendering della pagina (dalla datalist)
    const tagKeysList = $('tagKeysList');
    state.suggestedTagKeys = Array.from(tagKeysList.querySelectorAll('option')).map((opt) => opt.value);
    
    // Carica i valori dei tag suggeriti (passati dal backend nel template)
    const suggestedTagsData = window.suggestedTags || {};
    state.suggestedTagValues = { ...suggestedTagsData };

    $('btnLoad').addEventListener('click', () => loadResources(false));
    $('btnRefresh').addEventListener('click', () => loadResources(true));
    $('filterMode').addEventListener('change', onFilterModeChange);
    // Cambiare sorgente ricarica subito, se qualcosa e' gia' stato caricato.
    $('source').addEventListener('change', () => {
        if (state.resources.length > 0) loadResources(false);
    });
    $('searchBox').addEventListener('input', applyClientFilters);
    $('serviceFilter').addEventListener('change', applyClientFilters);
    $('hideSystemResources').addEventListener('change', applyClientFilters);
    populateProjectFilter();
    $('projectFilter').addEventListener('change', applyClientFilters);

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
    
    $('btnApplyAllSuggestedTags').addEventListener('click', applyAllSuggestedTags);

    $('btnRefreshRegions').addEventListener('click', async () => {
        const ok = await confirmAction({
            title: 'Aggiornare la lista delle region?',
            html: 'Le region abilitate sull\'account vengono rilette da AWS e salvate in <code>config.json</code>: '
                + 'la nuova lista vale per le tendine region di tutte le sezioni.' + contextHtml(),
            confirmText: 'Aggiorna',
        });
        if (!ok) return;
        spinner(true);
        try {
            const data = await apiPost('/api/tags/regions/refresh', currentContext());
            showAlert(data.message + ' - ricaricare la pagina per vedere la nuova lista.', 'success');
        } catch (e) {
            showAlert('Errore: ' + e.message, 'danger');
        } finally {
            spinner(false);
        }
    });
});

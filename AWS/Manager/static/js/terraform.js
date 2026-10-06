/* Terraform: risorse gestite, lette dagli state sui bucket S3 con "Carica".
 *
 * Il server manda una riga per istanza di risorsa {address, module, mode, type, name, id,
 * arn, region, provider, tags, tagged, bucket, state}; filtri, ordinamento e sottotabelle
 * dei tag si calcolano nel browser. Filtro per tag, sottotabella dei tag e celle comuni
 * sono in iac_common.js (condiviso con CloudFormation). */

const state = { data: null, open: new Set(), sort: { key: 'state', dir: 1 }, shown: 300, tagKey: null };
const PAGE = 300;
const BUCKET_KEY = 'terraform.bucket';   // bucket scelto, solo in questo browser

const stateId = (r) => `${r.bucket}/${r.state}`;
async function load() {
    const bucket = $('tfBucket').value;
    $('resources').innerHTML = loadingHtml(`Lettura degli state ${bucket ? `di ${bucket}` : `di ${$('tfBucket').options.length - 1} bucket`}...`);
    clearAlert();
    $('btnLoad').disabled = true;
    try {
        state.data = await apiGet(`/api/terraform/resources?${query({ bucket })}`);
        state.open.clear();
        state.shown = PAGE;
        renderFilterSelects();
        renderStates();
        render();
        const d = state.data;
        const errors = d.buckets.filter(b => b.error).length + d.states.filter(s => s.error).length;
        const cached = d.states.filter(s => s.cached).length;
        showAlertHtml(`Letti ${d.states.length} state da ${d.buckets.length} bucket in ${d.elapsed} s`
            + (cached ? ` (${cached} invariati, dalla cache)` : '')
            + (errors ? ` &middot; <strong>${errors} errori</strong> (vedi la tabella degli state)` : ''),
            errors ? 'warning' : 'success');
        if (errors) bootstrap.Collapse.getOrCreateInstance($('statesBody'), { toggle: false }).show();
    } catch (e) {
        $('resources').innerHTML = '';
        showAlert('Errore: ' + e.message, 'danger');
    } finally {
        $('btnLoad').disabled = false;
    }
}

// ---------------------------------------------------------------- filtri

function renderFilterSelects() {
    const rows = state.data.resources.filter(r => $('tfData').checked || r.mode === 'managed');
    selectOptions($('tfType'), counts(rows, r => r.type), 'Tutti');
    selectOptions($('tfRegion'), counts(rows, regionKey), 'Tutte', v => v === NO_REGION ? '(non indicata)' : v);
    selectOptions($('tfState'), counts(rows, stateId), 'Tutti');
    renderTagKeySelect($('tfTagKey'), rows, state.tagKey === null ? DEFAULT_TAG : state.tagKey);
    renderTagValues();
    $('tfFilters').classList.remove('d-none');
}

function renderTagValues() {
    const rows = state.data.resources.filter(r => ($('tfData').checked || r.mode === 'managed') && r.tagged);
    renderTagValueSelect($('tfTagValue'), $('tfTagValueLabel'), $('tfTagKey').value, rows);
}

function filtered() {
    const q = $('tfSearch').value.trim().toLowerCase();
    const type = $('tfType').value, region = $('tfRegion').value, st = $('tfState').value;
    const tagKey = $('tfTagKey').value, tagValue = tagKey ? $('tfTagValue').value : '';
    return state.data.resources.filter(r =>
        ($('tfData').checked || r.mode === 'managed')
        && (!type || r.type === type)
        && (!region || regionKey(r) === region)
        && (!st || stateId(r) === st)
        && tagMatches(r, tagKey, tagValue)
        && (!$('tfMissing').checked || missingRequired(r).length)
        && (!q || [r.address, r.name, r.id, r.arn, r.type, r.region, r.state, r.bucket,
            ...Object.entries(r.tags).map(([k, v]) => `${k}=${v}`)].join(' ').toLowerCase().includes(q)));
}

const SORTS = {
    address: r => r.address,
    type: r => r.type,
    name: r => r.name,
    region: r => r.region,
    state: r => `${stateId(r)} ${r.address}`,
    tags: r => String(userTags(r.tags).length).padStart(4, '0'),
};

// ---------------------------------------------------------------- tabelle

function renderStates() {
    const d = state.data;
    $('statesCount').textContent = d.states.length;
    $('statesCard').classList.remove('d-none');
    const bucketErrors = d.buckets.filter(b => b.error || b.truncated).map(b => b.error
        ? `<div class="alert alert-danger py-1 px-2 m-2 mb-0"><strong>${escapeHtml(b.bucket)}</strong>: ${escapeHtml(b.error)}</div>`
        : `<div class="alert alert-warning py-1 px-2 m-2 mb-0"><strong>${escapeHtml(b.bucket)}</strong>: letti solo i primi state (terraform.max_states)</div>`).join('');
    $('statesTable').innerHTML = bucketErrors + rowsTable(d.states.slice().sort((a, b) => stateId(a).localeCompare(stateId(b))), [
        { title: 'Bucket', get: s => escapeHtml(s.bucket) },
        { title: 'File', get: s => `<span class="mono">${escapeHtml(s.key)}</span>` },
        { title: 'Terraform', get: s => s.error ? '' : escapeHtml(s.terraform_version) },
        { title: 'Serial', cls: 'num', get: s => s.error ? '' : escapeHtml(s.serial) },
        { title: 'Risorse', cls: 'num', get: s => s.error ? `<span class="text-danger" title="${escapeHtml(s.error)}"><i class="fas fa-triangle-exclamation me-1"></i>errore</span>` : s.resources },
        { title: 'Output', cls: 'num', get: s => s.error ? '' : s.outputs },
        { title: 'Modificato', get: s => escapeHtml(fmtDate(s.last_modified)) },
        { title: 'Dimensione', cls: 'num', get: s => escapeHtml(fmtBytes(s.size)) },
    ], 'Nessun file .tfstate nei bucket letti');
}

function render() {
    if (!state.data) return;
    const rows = filtered();
    const { key, dir } = state.sort;
    rows.sort((a, b) => dir * SORTS[key](a).localeCompare(SORTS[key](b)));

    const th = (k, label) => sortableTh(state.sort, k, label);
    const shown = rows.slice(0, state.shown);
    const body = shown.map((r, i) => {
        const id = `${stateId(r)}|${r.address}`;
        const open = state.open.has(id);
        // colonne: Region, Tipo, Nome, Risorsa (indirizzo e, a capo, ID), State, Tag
        return `<tr class="tf-row${open ? ' tf-open' : ''}" data-id="${escapeHtml(id)}" data-i="${i}">
                <td>${regionCell(r.region)}</td>
                <td>${escapeHtml(r.type)}</td>
                <td class="text-break">${escapeHtml(r.name)}</td>
                <td class="text-break"><span class="mono">${r.module ? `<span class="text-muted">${escapeHtml(r.module)}.</span>` : ''}${escapeHtml(r.address.slice(r.module ? r.module.length + 1 : 0))}</span>
                    ${r.mode === 'data' ? iacBadge('data', 'info') : ''}
                    <br><span class="small mono text-muted">${escapeHtml(r.id)}</span></td>
                <td class="small"><span class="text-muted">${escapeHtml(r.bucket)}/</span>${escapeHtml(r.state)}</td>
                <td class="text-nowrap">${tagCountCell(r)}</td>
            </tr>`
            + (open ? `<tr class="tf-sub"><td colspan="6">${tagsSubTable(r, r.provider
                ? `<div class="small text-muted">Provider <span class="mono">${escapeHtml(r.provider)}</span></div>` : '')}</td></tr>` : '');
    }).join('');

    $('resources').innerHTML = `<div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="fas fa-cubes me-2 text-secondary"></i>Risorse <span class="badge text-bg-light border ms-1">${rows.length.toLocaleString('it-IT')}</span></span>
            <span class="card-hint">clic su una riga per i tag, sulle intestazioni per ordinare</span>
        </div>
        ${rows.length ? `<div class="table-responsive"><table class="table table-sm table-hover align-middle mb-0 tf-table">
            <thead class="table-light"><tr>${th('region', 'Region')}${th('type', 'Tipo')}${th('name', 'Nome')}${th('address', 'Risorsa / ID')}${th('state', 'State')}${th('tags', 'Tag')}</tr></thead>
            <tbody>${body}</tbody></table></div>`
            : '<div class="empty-state">Nessuna risorsa con questi filtri</div>'}
        ${rows.length > shown.length ? `<div class="text-center p-2"><button class="btn btn-sm btn-outline-primary" id="btnMore">
            <i class="fas fa-angles-down me-1"></i>Mostra altre ${Math.min(PAGE, rows.length - shown.length)} (di ${rows.length - shown.length})</button></div>` : ''}
    </div>`;

    $('resources').querySelectorAll('tr.tf-row').forEach(tr => tr.addEventListener('click', (ev) => {
        if (ev.target.closest('a')) return;
        const id = tr.dataset.id;
        if (state.open.has(id)) state.open.delete(id); else state.open.add(id);
        render();
    }));
    $('resources').querySelectorAll('th.sortable').forEach(h => h.addEventListener('click', () => {
        const k = h.dataset.sort;
        state.sort = { key: k, dir: state.sort.key === k ? -state.sort.dir : 1 };
        render();
    }));
    if ($('btnMore')) $('btnMore').addEventListener('click', () => { state.shown += PAGE; render(); });
    state.visible = shown;
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        const saved = localStorage.getItem(BUCKET_KEY);
        if (saved !== null && [...$('tfBucket').options].some(o => o.value === saved)) $('tfBucket').value = saved;
    } catch (e) { /* storage non disponibile */ }
    $('tfBucket').addEventListener('change', () => {
        try { localStorage.setItem(BUCKET_KEY, $('tfBucket').value); } catch (e) { /* ignorato */ }
    });
    $('btnLoad').addEventListener('click', load);

    const again = () => { state.shown = PAGE; render(); };
    $('tfSearch').addEventListener('input', debounce(again, 250));
    ['tfType', 'tfRegion', 'tfState', 'tfMissing', 'tfTagValue'].forEach(id => $(id).addEventListener('change', again));
    $('tfTagKey').addEventListener('change', () => {
        state.tagKey = $('tfTagKey').value;
        $('tfTagValue').value = '';
        renderTagValues();
        again();
    });
    $('tfData').addEventListener('change', () => { renderFilterSelects(); again(); });
    $('btnReset').addEventListener('click', () => {
        $('tfSearch').value = '';
        ['tfType', 'tfRegion', 'tfState', 'tfTagValue'].forEach(id => { $(id).value = ''; });
        state.tagKey = null;
        $('tfTagKey').value = DEFAULT_TAG;
        renderTagValues();
        $('tfMissing').checked = false;
        again();
    });
    $('btnExpand').addEventListener('click', () => {
        (state.visible || []).forEach(r => state.open.add(`${stateId(r)}|${r.address}`));
        render();
    });
    $('btnCollapse').addEventListener('click', () => { state.open.clear(); render(); });
    setupBackToTop();
});

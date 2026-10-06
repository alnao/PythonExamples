/* CloudFormation: risorse gestite, stack per stack, lette con "Carica".
 *
 * Il server manda gli stack {name, id, region, status, created, updated, description,
 * parent, drift, tags, resources, error} e una riga per risorsa {logical_id, physical_id,
 * type, status, reason, drift, updated, arn, region, tags, tagged, stack, stack_id,
 * stack_region, nested}; filtri, ordinamento e sottotabelle dei tag si calcolano nel
 * browser. Le parti comuni con Terraform sono in iac_common.js. */

const state = { data: null, open: new Set(), sort: { key: 'stack', dir: 1 }, shown: 300, tagKey: null };
const PAGE = 300;

const rowId = (r) => `${r.stack_id}|${r.logical_id}`;

// Stati di CloudFormation: verde completato, giallo in corso o rollback, rosso fallito
function cfnStatus(s) {
    if (!s) return '';
    const cls = /FAILED/.test(s) ? 'danger' : /ROLLBACK|IN_PROGRESS/.test(s) ? 'warning'
        : /COMPLETE/.test(s) ? 'success' : 'secondary';
    return iacBadge(s.replace(/_/g, ' ').toLowerCase(), cls);
}

// Drift: solo quando c'e' (in sync e non verificato non si mostrano)
function driftBadge(d) {
    if (!d || d === 'NOT_CHECKED' || d === 'IN_SYNC') return '';
    return iacBadge(d.toLowerCase(), ['DRIFTED', 'MODIFIED', 'DELETED'].includes(d) ? 'warning' : 'secondary');
}

async function load() {
    $('resources').innerHTML = loadingHtml(`Lettura degli stack (${APP.region === ALL ? `${APP.regions.length} region` : APP.region})...`);
    clearAlert();
    $('btnLoad').disabled = true;
    try {
        state.data = await apiGet(`/api/cloudformation/resources?${query({ region: APP.region, refresh: $('cfnRefresh').checked ? '1' : '' })}`);
        state.open.clear();
        state.shown = PAGE;
        renderFilterSelects();
        renderStacks();
        render();
        const d = state.data;
        const errors = d.stacks.filter(s => s.error).length;
        showAlertHtml(`Letti ${d.stacks.length} stack e ${d.resources.length} risorse in ${d.elapsed} s`
            + ` &middot; tag dalla Tagging API di ${d.tag_regions.join(', ') || 'nessuna region'}`
            + (d.warnings.length ? `<br>${d.warnings.map(escapeHtml).join('<br>')}` : '')
            + (errors ? `<br><strong>${errors} stack</strong> con errori (vedi la tabella degli stack)` : ''),
            d.warnings.length || errors ? 'warning' : 'success');
    } catch (e) {
        $('resources').innerHTML = '';
        showAlert('Errore: ' + e.message, 'danger');
    } finally {
        $('btnLoad').disabled = false;
    }
}

// ---------------------------------------------------------------- filtri

function renderFilterSelects() {
    const rows = state.data.resources;
    selectOptions($('cfnType'), counts(rows, r => r.type), 'Tutti');
    selectOptions($('cfnResRegion'), counts(rows, regionKey), 'Tutte', v => v === NO_REGION ? '(non indicata)' : v);
    selectOptions($('cfnStack'), counts(rows, r => r.stack_id), 'Tutti', v => {
        const s = state.data.stacks.find(x => x.id === v);
        return s ? `${s.name}${APP.region === ALL ? ` · ${s.region}` : ''}` : v;
    });
    selectOptions($('cfnStatus'), counts(rows, r => r.status), 'Tutti', v => v.replace(/_/g, ' ').toLowerCase());
    renderTagKeySelect($('cfnTagKey'), rows, state.tagKey === null ? DEFAULT_TAG : state.tagKey);
    renderTagValues();
    $('cfnFilters').classList.remove('d-none');
}

function renderTagValues() {
    renderTagValueSelect($('cfnTagValue'), $('cfnTagValueLabel'), $('cfnTagKey').value,
        state.data.resources.filter(r => r.tagged));
}

function filtered() {
    const q = $('cfnSearch').value.trim().toLowerCase();
    const type = $('cfnType').value, region = $('cfnResRegion').value;
    const stack = $('cfnStack').value, status = $('cfnStatus').value;
    const tagKey = $('cfnTagKey').value, tagValue = tagKey ? $('cfnTagValue').value : '';
    return state.data.resources.filter(r =>
        (!type || r.type === type)
        && (!region || regionKey(r) === region)
        && (!stack || r.stack_id === stack)
        && (!status || r.status === status)
        && tagMatches(r, tagKey, tagValue)
        && (!$('cfnMissing').checked || missingRequired(r).length)
        && (!q || [r.logical_id, r.physical_id, r.arn, r.type, r.region, r.stack, r.status,
            ...Object.entries(r.tags).map(([k, v]) => `${k}=${v}`)].join(' ').toLowerCase().includes(q)));
}

const SORTS = {
    logical: r => r.logical_id,
    type: r => r.type,
    physical: r => r.physical_id,
    region: r => r.region,
    stack: r => `${r.stack} ${r.logical_id}`,
    status: r => r.status,
    project: r => r.tags.Project || '',
    tags: r => String(userTags(r.tags).length).padStart(4, '0'),
};

// ---------------------------------------------------------------- tabelle

function renderStacks() {
    const d = state.data;
    $('stacksCount').textContent = d.stacks.length;
    $('stacksCard').classList.remove('d-none');
    // gli stack nested sotto il loro padre
    const byId = Object.fromEntries(d.stacks.map(s => [s.id, s]));
    const roots = d.stacks.filter(s => !s.parent || !byId[s.parent]).sort((a, b) => a.name.localeCompare(b.name));
    const ordered = [];
    const add = (s, depth) => {
        ordered.push({ ...s, depth });
        d.stacks.filter(c => c.parent === s.id).sort((a, b) => a.name.localeCompare(b.name)).forEach(c => add(c, depth + 1));
    };
    roots.forEach(s => add(s, 0));
    const active = $('cfnStack').value;
    $('stacksTable').innerHTML = `<div class="table-responsive"><table class="table table-sm table-hover align-middle mb-0 tf-table">
        <thead><tr><th>Stack</th><th>Region</th><th>Stato</th><th>Drift</th><th>Project</th><th class="num">Risorse</th><th>Aggiornato</th><th>Descrizione</th></tr></thead><tbody>`
        + ordered.map(s => `<tr class="tf-row${s.id === active ? ' table-active' : ''}" data-stack="${escapeHtml(s.id)}">
            <td style="padding-left:${0.5 + s.depth * 1.2}rem">${s.depth ? '&#8627; ' : ''}<strong>${escapeHtml(s.name)}</strong>
                ${s.depth ? iacBadge('nested', 'light border') : ''}${s.protection ? ` <i class="fas fa-lock text-secondary" title="Protezione dalla cancellazione attiva"></i>` : ''}</td>
            <td>${regionBadge(s.region)}</td>
            <td>${cfnStatus(s.status)}${s.reason ? `<div class="small text-muted text-wrap">${escapeHtml(s.reason)}</div>` : ''}</td>
            <td>${driftBadge(s.drift)}</td>
            <td>${'Project' in s.tags ? escapeHtml(s.tags.Project) : '<span class="badge text-bg-danger">mancante</span>'}</td>
            <td class="num">${s.error ? `<span class="text-danger" title="${escapeHtml(s.error)}"><i class="fas fa-triangle-exclamation"></i></span>` : s.resources}</td>
            <td class="small">${escapeHtml(fmtDate(s.updated || s.created))}</td>
            <td class="small text-muted text-wrap">${escapeHtml(s.description)}</td></tr>`).join('')
        + '</tbody></table></div>';
    $('stacksTable').querySelectorAll('tr[data-stack]').forEach(tr => tr.addEventListener('click', () => {
        const sel = $('cfnStack');
        sel.value = sel.value === tr.dataset.stack ? '' : tr.dataset.stack;
        state.shown = PAGE;
        renderStacks();
        render();
    }));
}

function render() {
    if (!state.data) return;
    const rows = filtered();
    const { key, dir } = state.sort;
    rows.sort((a, b) => dir * SORTS[key](a).localeCompare(SORTS[key](b)));
    const th = (k, label) => sortableTh(state.sort, k, label);
    const shown = rows.slice(0, state.shown);
    const body = shown.map(r => {
        const id = rowId(r);
        const open = state.open.has(id);
        const extra = `<div class="small text-muted mt-1">Stack <strong>${escapeHtml(r.stack)}</strong> (${escapeHtml(r.stack_region)})`
            + `${r.updated ? ` &middot; aggiornata ${escapeHtml(fmtDate(r.updated))}` : ''}</div>`
            + (r.reason ? `<div class="small text-muted">Motivo dello stato: ${escapeHtml(r.reason)}</div>` : '');
        return `<tr class="tf-row${open ? ' tf-open' : ''}" data-id="${escapeHtml(id)}">
                <td><span class="mono">${escapeHtml(r.logical_id)}</span></td>
                <td>${escapeHtml(r.type)}</td>
                <td class="text-break small mono">${escapeHtml(r.physical_id)}</td>
                <td>${regionCell(r.region)}</td>
                <td class="small">${escapeHtml(r.stack)}${r.nested ? ` ${iacBadge('nested', 'light border')}` : ''}</td>
                <td>${cfnStatus(r.status)} ${driftBadge(r.drift)}</td>
                <td>${projectCell(r)}</td>
                <td class="text-nowrap">${tagCountCell(r)}</td>
            </tr>`
            + (open ? `<tr class="tf-sub"><td colspan="8">${tagsSubTable(r, extra,
                'Nessun tag: tipo di risorsa senza tag, o non presente nella Tagging API')}</td></tr>` : '');
    }).join('');

    $('resources').innerHTML = `<div class="card mb-3">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="fas fa-cubes me-2 text-secondary"></i>Risorse <span class="badge text-bg-light border ms-1">${rows.length.toLocaleString('it-IT')}</span></span>
            <span class="card-hint">clic su una riga per i tag, sulle intestazioni per ordinare</span>
        </div>
        ${rows.length ? `<div class="table-responsive"><table class="table table-sm table-hover align-middle mb-0 tf-table">
            <thead class="table-light"><tr>${th('logical', 'Risorsa')}${th('type', 'Tipo')}${th('physical', 'ID fisico')}${th('region', 'Region')}${th('stack', 'Stack')}${th('status', 'Stato')}${th('project', 'Project')}${th('tags', 'Tag')}</tr></thead>
            <tbody>${body}</tbody></table></div>`
            : '<div class="empty-state">Nessuna risorsa con questi filtri</div>'}
        ${rows.length > shown.length ? `<div class="text-center p-2"><button class="btn btn-sm btn-outline-primary" id="btnMore">
            <i class="fas fa-angles-down me-1"></i>Mostra altre ${Math.min(PAGE, rows.length - shown.length)} (di ${rows.length - shown.length})</button></div>` : ''}
    </div>`;

    $('resources').querySelectorAll('tr.tf-row').forEach(tr => tr.addEventListener('click', () => {
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
    $('btnLoad').addEventListener('click', load);

    const again = () => { state.shown = PAGE; render(); };
    $('cfnSearch').addEventListener('input', debounce(again, 250));
    ['cfnType', 'cfnResRegion', 'cfnStatus', 'cfnMissing', 'cfnTagValue'].forEach(id => $(id).addEventListener('change', again));
    $('cfnStack').addEventListener('change', () => { renderStacks(); again(); });
    $('cfnTagKey').addEventListener('change', () => {
        state.tagKey = $('cfnTagKey').value;
        $('cfnTagValue').value = '';
        renderTagValues();
        again();
    });
    $('btnReset').addEventListener('click', () => {
        $('cfnSearch').value = '';
        ['cfnType', 'cfnResRegion', 'cfnStack', 'cfnStatus', 'cfnTagValue'].forEach(id => { $(id).value = ''; });
        state.tagKey = null;
        $('cfnTagKey').value = DEFAULT_TAG;
        renderTagValues();
        $('cfnMissing').checked = false;
        renderStacks();
        again();
    });
    $('btnExpand').addEventListener('click', () => {
        (state.visible || []).forEach(r => state.open.add(rowId(r)));
        render();
    });
    $('btnCollapse').addEventListener('click', () => { state.open.clear(); render(); });
    setupBackToTop();
});

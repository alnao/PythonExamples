/* Panoramic: una tabella per servizio, letta con "Servizi principali" o "Tutti i servizi".
 * Il filtro Project funziona come nel Tag Manager (tag_match.js): uguaglianza stretta con
 * la voce scelta, sottovoci dei valori suggeriti trovate nelle righe lette, "Altri valori". */

const state = { data: null };

async function load(scope) {
    $('sections').innerHTML = loadingHtml(`Lettura ${scope === 'all' ? 'di tutti i servizi' : 'dei servizi principali'}`
        + ` (${APP.region === ALL ? `${APP.regions.length} region` : APP.region})...`);
    $('indexCard').classList.add('d-none');
    clearAlert();
    ['btnMain', 'btnAll'].forEach(id => { $(id).disabled = true; });
    try {
        state.data = await apiGet(`/api/panoramic/resources?${query({ scope, region: APP.region })}`);
        populateProjectFilter();
        render();
        const errors = state.data.sections.reduce((a, s) => a + s.errors.length, 0);
        showAlertHtml(`Letti ${state.data.sections.length} servizi in ${state.data.elapsed} s`
            + (errors ? ` &middot; <strong>${errors} errori</strong> (dettaglio nelle singole sezioni)` : ''),
            errors ? 'warning' : 'success');
    } catch (e) {
        $('sections').innerHTML = '';
        showAlert('Errore: ' + e.message, 'danger');
    } finally {
        ['btnMain', 'btnAll'].forEach(id => { $(id).disabled = false; });
    }
}

function cell(v) {
    if (v === null || v === undefined || v === '') return '<span class="text-muted">&ndash;</span>';
    if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v)) return escapeHtml(fmtDate(v));
    return escapeHtml(v);
}

/* Colonna dopo cui va l'icona dei tag: 'Nome' se c'e', altrimenti la prima (esclusa Region). */
function nameColumn(s) {
    return s.columns.includes('Nome') ? 'Nome' : s.columns.find(c => c !== 'Region');
}

/* Opzioni della tendina Project: valori suggeriti con le sottovoci trovate nelle righe lette. */
function populateProjectFilter() {
    const select = $('projectFilter');
    const current = select.value;
    const rows = state.data ? state.data.sections.flatMap(s => s.rows) : [];
    select.innerHTML = suggestedFilterOptions('Project', rows.map(r => ({ tags: r._tags || {} })), 'Tutti i Project');
    select.value = current;
    if (select.value !== current) select.value = '';
}

/* Filtro Project su una riga: le righe di cui non si conoscono i tag spariscono quando il filtro e' attivo. */
function projectMatch(r, project) {
    if (!project) return true;
    if (!r._tags) return false;
    const have = r._tags.Project;
    if (project === '__other__') return have !== undefined && have !== null && !isSuggestedValue('Project', have);
    return (have || '') === project;
}

function render() {
    if (!state.data) return;
    const q = $('search').value.trim().toLowerCase();
    const hideEmpty = $('hideEmpty').checked;
    const project = $('projectFilter').value;
    const sections = state.data.sections.map(s => ({
        ...s,
        visible: s.rows.filter(r => projectMatch(r, project)
            && (!q || Object.values(r).join(' ').toLowerCase().includes(q))),
    }));
    // "Nascondi servizi vuoti": via dall'indice e dalle tabelle i servizi senza righe visibili
    // (con i filtri attivi), tranne quelli con errori che vanno comunque segnalati
    const shown = sections.filter(s => !hideEmpty || s.visible.length || s.errors.length);

    $('sectionIndex').innerHTML = shown.map(s =>
        `<a href="#sec-${s.key}" class="me-2 d-inline-block mb-1">
            <span class="badge ${s.errors.length ? 'text-bg-warning' : s.visible.length ? 'text-bg-primary' : 'text-bg-light border'}">
            ${escapeHtml(s.title)} ${s.visible.length}</span></a>`).join('')
        + (shown.length < sections.length ? `<span class="small text-muted">${sections.length - shown.length} servizi vuoti nascosti</span>` : '');
    $('indexCard').classList.remove('d-none');

    $('sections').innerHTML = shown.map(s => `
        <div class="card mb-3" id="sec-${s.key}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span>${escapeHtml(s.title)} <span class="badge text-bg-light border ms-1">${s.visible.length}</span>
                    ${s.global ? '<span class="card-hint ms-2">globale</span>' : ''}</span>
            </div>
            ${s.errors.length ? `<div class="alert alert-warning py-1 px-2 m-2 mb-0">${s.errors.map(escapeHtml).join('<br>')}</div>` : ''}
            ${rowsTable(s.visible, s.columns.map(c => ({
                title: c,
                get: r => c === 'Region' ? regionBadge(r[c]) : cell(r[c]) + (c === nameColumn(s) ? tagIcon(r._tags) : ''),
            })), q || project ? 'Nessuna risorsa corrisponde ai filtri' : 'Nessuna risorsa trovata')}
        </div>`).join('') || '<div class="empty-state">Nessun servizio da mostrare</div>';
}

document.addEventListener('DOMContentLoaded', () => {
    $('btnMain').addEventListener('click', () => load('main'));
    $('btnAll').addEventListener('click', () => load('all'));
    $('search').addEventListener('input', debounce(render, 250));
    $('hideEmpty').addEventListener('change', render);
    $('projectFilter').addEventListener('change', render);
    populateProjectFilter();

    const top = $('backToTop');
    window.addEventListener('scroll', () => top.classList.toggle('show', window.scrollY > 300));
    top.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
});

/* AlNao AWS Manager - funzioni comuni a tutte le pagine.
 *
 *  - chiamate alle API (JSON) con gestione degli errori
 *  - messaggi, spinner, formattazione di date e numeri
 *  - conferma prima di ogni operazione che modifica AWS (confirmAction)
 *  - profilo (navbar) e region (sezioni): salvati nella sessione, poi la pagina si ricarica
 *
 * window.APP e' valorizzato dal template base (profilo, region, lista delle region) e
 * ampliato dalle singole pagine.
 */

const ALL = '__all__';

function $(id) { return document.getElementById(id); }

/* Escape valido sia dentro il testo sia dentro gli attributi (virgolette comprese). */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ---------------------------------------------------------------- API

async function parseResponse(response) {
    let data = {};
    try { data = await response.json(); } catch (e) { data = {}; }
    if (!response.ok) throw new Error(data.error || `Errore ${response.status}`);
    return data;
}

async function apiGet(url) {
    return parseResponse(await fetch(url));
}

async function apiPost(url, body) {
    return parseResponse(await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {}),
    }));
}

function query(params) {
    const clean = {};
    Object.entries(params || {}).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') clean[k] = v; });
    return new URLSearchParams(clean).toString();
}

// ---------------------------------------------------------------- messaggi

/* Messaggio di testo (viene fatto l'escape). */
function showAlert(text, type = 'success', container = 'alertBox') {
    showAlertHtml(escapeHtml(text), type, container);
}

/* Messaggio con HTML gia' pronto (chi chiama fa l'escape dei dati). */
function showAlertHtml(html, type = 'danger', container = 'alertBox') {
    const el = $(container);
    if (!el) return;
    el.innerHTML = alertHtml(html, type);
}

function appendAlertHtml(html, type = 'info', container = 'alertBox') {
    const el = $(container);
    if (el) el.insertAdjacentHTML('beforeend', alertHtml(html, type));
}

function clearAlert(container = 'alertBox') {
    const el = $(container);
    if (el) el.innerHTML = '';
}

function alertHtml(html, type) {
    return `<div class="alert alert-${type} alert-dismissible fade show py-2" role="alert">${html}
        <button type="button" class="btn-close btn-sm py-2" data-bs-dismiss="alert"></button></div>`;
}

function spinner(on) {
    let el = document.querySelector('.spinner-overlay');
    if (on && !el) {
        document.body.insertAdjacentHTML('beforeend',
            '<div class="spinner-overlay"><div class="spinner-border text-primary"></div></div>');
    } else if (!on && el) {
        el.remove();
    }
}

/* Contenuto "in caricamento" per un elemento. */
function loadingHtml(text = 'Caricamento...') {
    return `<div class="empty-state"><span class="spinner-border spinner-border-sm me-2"></span>${escapeHtml(text)}</div>`;
}

// ---------------------------------------------------------------- conferma

/* Chiede conferma prima di un'operazione che modifica AWS.
 * opts: {title, html (corpo, gia' con escape), confirmText, danger}
 * Ritorna una Promise<boolean>. */
function confirmAction(opts) {
    const modalEl = $('confirmModal');
    $('confirmTitle').textContent = opts.title || 'Conferma operazione';
    $('confirmBody').innerHTML = opts.html || '';
    const btn = $('confirmOk');
    btn.textContent = opts.confirmText || 'Conferma';
    btn.className = `btn btn-sm ${opts.danger ? 'btn-danger' : 'btn-primary'}`;
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    return new Promise((resolve) => {
        let done = false;
        const finish = (value) => {
            if (done) return;
            done = true;
            btn.removeEventListener('click', onOk);
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
            resolve(value);
        };
        const onOk = () => { finish(true); modal.hide(); };
        const onHidden = () => finish(false);
        btn.addEventListener('click', onOk);
        modalEl.addEventListener('hidden.bs.modal', onHidden);
        modal.show();
    });
}

/* Riga "Profilo / Region" da mettere nelle conferme. Senza argomento la region scelta
 * nella pagina, con '' nessuna region (servizi globali). */
function contextHtml(region) {
    const r = region === undefined ? APP.region : region;
    return `<div class="small text-muted mt-2">Profilo <strong>${escapeHtml(APP.profile)}</strong>`
        + (r ? ` &middot; region <strong>${escapeHtml(r === ALL ? 'tutte' : r)}</strong>` : '') + '</div>';
}

// ---------------------------------------------------------------- formattazione

/* Data leggibile da ISO, epoch in millisecondi o in secondi. */
function fmtDate(v) {
    if (v === null || v === undefined || v === '') return '';
    let d;
    if (typeof v === 'number') d = new Date(v > 1e11 ? v : v * 1000);
    else d = new Date(v);
    if (isNaN(d)) return String(v);
    return d.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function fmtBytes(n) {
    if (n === null || n === undefined || n === '') return '';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let v = Number(n), i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return `${v.toLocaleString('it-IT', { maximumFractionDigits: i ? 1 : 0 })} ${units[i]}`;
}

function regionBadge(region) {
    return region ? `<span class="badge badge-region">${escapeHtml(region)}</span>` : '';
}

/* Tabella chiave/valore di un oggetto: i valori annidati in JSON. */
function kvTable(obj, skip = []) {
    const rows = Object.entries(obj || {}).filter(([k]) => !skip.includes(k) && !k.startsWith('_'));
    if (!rows.length) return '<div class="empty-state">Nessun dato</div>';
    return '<table class="table table-sm table-kv"><tbody>' + rows.map(([k, v]) => {
        const value = (v !== null && typeof v === 'object')
            ? `<pre class="json">${escapeHtml(JSON.stringify(v, null, 2))}</pre>`
            : escapeHtml(v);
        return `<tr><th>${escapeHtml(k)}</th><td>${value}</td></tr>`;
    }).join('') + '</tbody></table>';
}

/* Tabella di righe. columns: [{title, get(row) -> html gia' con escape, cls}] */
function rowsTable(rows, columns, empty = 'Nessun elemento') {
    if (!rows || !rows.length) return `<div class="empty-state">${escapeHtml(empty)}</div>`;
    return '<div class="table-responsive"><table class="table table-sm table-hover align-middle"><thead><tr>'
        + columns.map(c => `<th class="${c.cls || ''}">${escapeHtml(c.title)}</th>`).join('')
        + '</tr></thead><tbody>'
        + rows.map(r => '<tr>' + columns.map(c => `<td class="${c.cls || ''}">${c.get(r)}</td>`).join('') + '</tr>').join('')
        + '</tbody></table></div>';
}

/* Icona dei tag di una risorsa (regole del Tag Manager, APP.tagRules da config.json):
 *  - un tag che vale aws_auto: info "aws automatic" (risorsa gestita in automatico, esente)
 *  - tag obbligatori mancanti (e nessun set di compliant_tags): allarme con i tag mancanti
 *  - altrimenti: icona tag con i tag standard (le chiavi di suggested_tags)
 * tags null/undefined = tag non noti: nessuna icona. */
function tagIcon(tags) {
    if (tags === null || tags === undefined) return '';
    const rules = APP.tagRules || { required: [], standard: [], compliant: [], auto: 'aws_auto' };
    const tip = (icon, cls, text) =>
        `<i class="fas ${icon} ${cls} ms-1 tag-icon" data-bs-toggle="tooltip" data-bs-title="${escapeHtml(text)}"></i>`;
    if (Object.values(tags).includes(rules.auto)) return tip('fa-circle-info', 'text-info', 'aws automatic');
    const compliant = rules.compliant.some(set => Object.entries(set).every(([k, v]) => tags[k] === v));
    const missing = compliant ? [] : rules.required.filter(k => !(k in tags));
    if (missing.length) return tip('fa-triangle-exclamation', 'text-danger', `Tag mancanti: ${missing.join(', ')}`);
    const standard = rules.standard.map(k => `${k}: ${k in tags ? tags[k] : '–'}`).join('\n');
    return tip('fa-tag', 'text-success', standard || 'Tag presenti');
}

// Tooltip creati al primo passaggio del mouse: funzionano anche sugli elementi aggiunti dopo
document.addEventListener('mouseover', (ev) => {
    const el = ev.target.closest && ev.target.closest('[data-bs-toggle="tooltip"]');
    if (el && window.bootstrap && !bootstrap.Tooltip.getInstance(el)) {
        bootstrap.Tooltip.getOrCreateInstance(el, { customClass: 'tooltip-pre' }).show();
    }
});

function debounce(fn, wait) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
}

// ---------------------------------------------------------------- profilo e region

async function setContext(values) {
    try {
        spinner(true);
        await apiPost('/api/context', values);
        location.reload();
    } catch (e) {
        spinner(false);
        showAlert('Errore: ' + e.message, 'danger');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const profile = $('navProfile');
    if (profile) profile.addEventListener('change', () => setContext({ profile: profile.value }));
    document.querySelectorAll('.js-region').forEach(sel =>
        sel.addEventListener('change', () => setContext({ region: sel.value })));
});

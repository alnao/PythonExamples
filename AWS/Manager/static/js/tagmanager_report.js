/* Tag Manager, report multi-region - semplice vista aggregata con filtri per suggested_tags (solo quelli con lista)
 * Le risorse sono quelle di tutte le region della lista (config.json), col profilo della navbar.
 * Mostra colonne: Region, Service, Type, e per ogni suggested_tag con lista mostra il valore.
 * La tendina Project elenca anche le sottovoci trovate nelle risorse (like Valore%),
 * ma il filtro e' sempre di uguaglianza stretta: vedi tag_match.js.
 */

const state = {
    resources: [],
    visible: [],
    suggestedKeysWithList: [],
    filters: {},
    showSystem: false,
};

// $, escapeHtml, showAlert, clearAlert e apiGet sono in common.js

/* Stato della cache del server: da quando sono in cache i dati e quando scadono.
 * Con piu' region, la data e' quella della region in cache da piu' tempo. */
function renderCacheInfo(data){
    const el = $('cacheInfo');
    const ora = (ts) => new Date(ts * 1000).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    if (data.cached && data.cached_at) {
        const scadenza = data.cached_at + (data.cache_ttl || 0);
        el.innerHTML = `<i class="fas fa-database me-1"></i>Dati in cache dalle ${ora(data.cached_at)}`
            + (data.cache_ttl ? ` (scade alle ${ora(scadenza)})` : '');
        el.classList.remove('d-none');
    } else {
        el.innerHTML = `<i class="fas fa-cloud me-1"></i>Letti da AWS alle ${ora(Date.now() / 1000)}`;
        el.classList.remove('d-none');
    }
}

async function loadReport(refresh = false){
    showAlert(refresh ? 'Lettura da AWS in corso (senza cache)...' : 'Caricamento in corso...', 'info');
    try{
        const data = await apiGet('/api/tags/report/resources' + (refresh ? '?refresh=1' : ''));
        renderCacheInfo(data);
        state.resources = data.resources || [];
        state.visible = [...state.resources];
        // Calcola i valori "other" per ogni suggested key: valori presenti nelle risorse ma non nella lista suggerita
        state.otherValues = {};
        state.suggestedKeysWithList.forEach((k) => {
            const present = new Set();
            state.resources.forEach((r) => {
                const v = (r.tags && r.tags[k]);
                if (v !== undefined && v !== null && String(v).trim() !== '') present.add(String(v));
            });
            const others = [...present].filter(v => !isSuggestedValue(k, v)).sort();
            state.otherValues[k] = others;
        });
        clearAlert();
        if ((data.warnings || []).length) {
            appendAlertHtml(data.warnings.map(escapeHtml).join('<br>'), 'warning');
        }
        renderHeaderAndFilters();
        applyFilters();
    }catch(e){ showAlert('Errore: '+e.message, 'danger'); }
}

function renderHeaderAndFilters(){
    // Determina quali suggested keys hanno una lista di valori
    const suggested = window.suggestedTags || {};
    state.suggestedKeysWithList = Object.keys(suggested).filter(k => Array.isArray(suggested[k]) && suggested[k].length>0);

    // Costruisce l'header della tabella (Name come prima colonna)
    const header = ['Name','Region','Service','Type', ...state.suggestedKeysWithList];
    $('reportHeader').innerHTML = '<tr>' + header.map((h, idx) => {
        if (h === 'Name') return `<th style="width:15%">${escapeHtml(h)}</th>`;
        return `<th>${escapeHtml(h)}</th>`;
    }).join('') + '</tr>';

    // Costruisce i filtri per suggested keys (layout orizzontale)
    // Include l'opzione '__other__' che significa "qualsiasi valore presente
    // nelle risorse ma non in tendina". Per Project i valori trovati nelle
    // risorse che estendono un suggerito (es. "Annotazioni-Ec2") compaiono come
    // sottovoci del padre (vedi tag_match.js); la selezione corrente viene mantenuta.
    const container = $('suggestedFiltersRow');
    const precedenti = {};
    document.querySelectorAll('.suggested-filter').forEach(s => { precedenti[s.dataset.key] = s.value; });
    container.innerHTML = state.suggestedKeysWithList.map(k => {
        const options = suggestedFilterOptions(k, state.resources, 'Tutti');

        return `
            <div class="col-auto mb-2 d-flex flex-column">
                <label class="form-label small mb-1">${escapeHtml(k)}</label>
                <select class="form-select form-select-sm suggested-filter" data-key="${escapeHtml(k)}">${options}</select>
            </div>`;
    }).join('');

    // aggiusta layout se non ci sono filtri
    if(state.suggestedKeysWithList.length===0) container.innerHTML = '<div class="text-muted small">Nessun suggested_tag con lista di valori trovato in config.</div>';

    // ripristina la selezione precedente (se il valore esiste ancora nella tendina)
    document.querySelectorAll('.suggested-filter').forEach(s => { if (precedenti[s.dataset.key]) s.value = precedenti[s.dataset.key]; });

    // eventi
    $('search').addEventListener('input', applyFilters);
    $('regionFilter').addEventListener('change', applyFilters);
    document.querySelectorAll('.suggested-filter').forEach(s => s.addEventListener('change', (e) => {
        applyFilters();
    }));
}

function applyFilters(){
    const q = $('search').value.trim().toLowerCase();
    const region = $('regionFilter').value;
    const activeFilters = {};
    document.querySelectorAll('.suggested-filter').forEach(s => { if(s.value) activeFilters[s.dataset.key]=s.value; });
    const showSystem = $('showSystem') ? $('showSystem').checked : true;

    state.visible = state.resources.filter(r => {
        if(region && r.region !== region) return false;
        if(!showSystem && r.is_system) return false;
        // per ogni filtro suggerito, confronta
        for(const k of Object.keys(activeFilters)){
            const want = activeFilters[k];
            const have = (r.tags && r.tags[k]);
            if (want === '__other__') {
                // accetta qualsiasi valore presente nelle risorse ma non in tendina
                if (have === undefined || have === null) return false;
                if (isSuggestedValue(k, have)) return false;
                continue;
            }
            if((have || '') !== want) return false;
        }
        if(!q) return true;
        const tagText = Object.entries(r.tags||{}).map(([k,v])=>`${k}=${v}`).join(' ');
        return (r.name+' '+r.arn+' '+tagText).toLowerCase().includes(q);
    });
    renderBody();
}

function renderBody(){
    const cols = ['region','service','resource_type', ...state.suggestedKeysWithList];
    const body = state.visible.map(r => {
        const cells = [];
        // Name column: mostra i primi caratteri, tooltip con nome completo, click copia il nome
        const name = r.name || '';
        const preview = getNamePreview(name);
        cells.push(`<td style="width:15%"><span class="name-preview" data-full-name="${escapeHtml(name)}" data-bs-toggle="tooltip" title="${escapeHtml(name)}">${escapeHtml(preview)}</span></td>`);
        cells.push(`<td>${escapeHtml(r.region)}</td>`);
        cells.push(`<td>${escapeHtml(r.service)}</td>`);
        cells.push(`<td>${escapeHtml(r.resource_type||'-')}</td>`);
        for(const k of state.suggestedKeysWithList){
            let v = (r.tags && r.tags[k]) || '';
            // Per le risorse di sistema, se ManagedBy non è presente mostra 'aws_auto'
            if (r.is_system && String(k).toLowerCase() === 'managedby' && (!v || String(v).trim() === '')) {
                v = 'aws_auto';
            }
            cells.push(`<td>${escapeHtml(v)}</td>`);
        }
        return `<tr>${cells.join('')}</tr>`;
    }).join('');
    const baseCols = 4; // Name, Region, Service, Type
    const colspan = baseCols + state.suggestedKeysWithList.length;
    $('reportBody').innerHTML = body || `<tr><td class="text-center text-muted py-4" colspan="${colspan}">Nessuna risorsa corrisponde ai filtri</td></tr>`;

    // Attiva i tooltip di Bootstrap per gli elementi con tooltip
    var tooltipTriggerList = Array.prototype.slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        try { new bootstrap.Tooltip(tooltipTriggerEl); } catch (e) { /* ignore */ }
    });

    // Aggiunge evento click per copiare il nome completo nella clipboard
    document.querySelectorAll('.name-preview').forEach(el => {
        el.style.cursor = 'pointer';
        el.addEventListener('click', async () => {
            const full = el.dataset.fullName || '';
            try {
                await navigator.clipboard.writeText(full);
                showAlert('Nome copiato negli appunti', 'success');
            } catch (e) {
                showAlert('Copia non riuscita: ' + e.message, 'warning');
            }
        });
    });
}
function getNamePreview(name) {
    if (!name) return '';
    const maxChars = 30; // mostra i primi caratteri
    if (name.length <= maxChars) return name;
    return name.substring(0, maxChars) + '...';
}

document.addEventListener('DOMContentLoaded', () => {
    // le arrow servono: passando loadReport direttamente, l'evento click
    // finirebbe nel parametro refresh e risulterebbe sempre "vero"
    $('btnLoadReport').addEventListener('click', () => loadReport(false));
    $('btnReloadNoCache').addEventListener('click', () => loadReport(true));
});

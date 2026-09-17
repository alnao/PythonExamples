/* Report multi-region - semplice vista aggregata con filtri per suggested_tags (solo quelli con lista)
 * Mostra colonne: Region, Service, Type, e per ogni suggested_tag con lista mostra il valore.
 */

const state = {
    resources: [],
    visible: [],
    suggestedKeysWithList: [],
    filters: {},
    showSystem: false,
};

function $(id){ return document.getElementById(id); }

function escapeHtml(text){ if(text===null||text===undefined) return ''; return String(text)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

function showAlert(msg, type='success'){
    $('alertBox').innerHTML = `<div class="alert alert-${type} py-2">${escapeHtml(msg)}</div>`;
}

async function apiGet(url){
    const r = await fetch(url);
    const j = await r.json();
    if(!r.ok) throw new Error(j.error || 'Errore');
    return j;
}

async function loadReport(){
    showAlert('Caricamento in corso...', 'info');
    try{
        const data = await apiGet('/api/report/resources');
        state.resources = data.resources || [];
        state.visible = [...state.resources];
        // Calcola i valori "other" per ogni suggested key: valori presenti nelle risorse ma non nella lista suggerita
        state.otherValues = {};
        const suggested = window.suggestedTags || {};
        state.suggestedKeysWithList.forEach((k) => {
            const present = new Set();
            state.resources.forEach((r) => {
                const v = (r.tags && r.tags[k]);
                if (v !== undefined && v !== null && String(v).trim() !== '') present.add(String(v));
            });
            const suggestedSet = new Set((suggested[k] || []).map(String));
            const others = [...present].filter(v => !suggestedSet.has(v)).sort();
            state.otherValues[k] = others;
        });
        showAlert(`Caricate ${state.resources.length} risorse da ${data.regions.length} region.`, 'success');
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
    // nelle risorse ma non nella lista suggerita".
    const container = $('suggestedFiltersRow');
    container.innerHTML = state.suggestedKeysWithList.map(k => {
        const vals = window.suggestedTags[k] || [];
        const options = ['<option value="">Tutti</option>']
            .concat(vals.map(v => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`))
            .concat(['<option value="__other__">Altri valori</option>'])
            .join('');

        return `
            <div class="col-auto mb-2 d-flex flex-column" style="min-width:200px;">
                <label class="form-label small">${escapeHtml(k)}</label>
                <select class="form-select suggested-filter" data-key="${escapeHtml(k)}">${options}</select>
            </div>`;
    }).join('');

    // aggiusta layout se non ci sono filtri
    if(state.suggestedKeysWithList.length===0) container.innerHTML = '<div class="text-muted small">Nessun suggested_tag con lista di valori trovato in config.</div>';

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
                // accetta qualsiasi valore presente nelle risorse ma non nella lista suggerita
                const suggestedSet = new Set((window.suggestedTags[k] || []).map(String));
                if (have === undefined || have === null) return false;
                if (suggestedSet.has(String(have))) return false;
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
    $('btnLoadReport').addEventListener('click', loadReport);
});

/* Tendine di filtro sui valori suggeriti (config suggested_tags).
 * Condiviso da tagmanager.js e tagmanager_report.js, cosi' le tendine si comportano
 * allo stesso modo nelle due pagine.
 *
 * Per le chiavi in PREFIX_MATCH_KEYS (tag_manager.prefix_match_keys in config.json,
 * di default Project) i valori trovati nelle risorse che
 * estendono un valore suggerito (Valore%, es. "Annotazioni-Ec2" per "Annotazioni")
 * vengono aggiunti alla tendina come sottovoci del "padre". Il filtro pero' e'
 * sempre di uguaglianza stretta: scegliendo il padre si vedono solo le risorse con
 * esattamente quel valore, scegliendo la sottovoce solo quelle con la sottovoce.
 */

const PREFIX_MATCH_KEYS = (window.APP && APP.prefixMatchKeys) || ['Project'];

function suggestedValues(key){
    return ((window.suggestedTags || {})[key] || []).map(String);
}

// Il "padre" di un valore: il suggerito piu' lungo di cui il valore e' un'estensione.
// null se la chiave non usa il prefisso, se il valore e' esso stesso un suggerito o
// se nessun suggerito lo precede.
function suggestedParent(key, value){
    if (!PREFIX_MATCH_KEYS.includes(key)) return null;
    const v = String(value);
    let best = null;
    suggestedValues(key).forEach(p => {
        if (v !== p && v.startsWith(p) && (best === null || p.length > best.length)) best = p;
    });
    return best;
}

// Vero se il valore compare nella tendina: e' un suggerito oppure una sua sottovoce.
// Usato dall'opzione "Altri valori" (= tutto cio' che NON compare nella tendina).
function isSuggestedValue(key, have){
    if (have === undefined || have === null) return false;
    const v = String(have);
    return suggestedValues(key).includes(v) || suggestedParent(key, v) !== null;
}

// Sottovoci trovate nelle risorse caricate, raggruppate per padre e ordinate:
// { "Annotazioni": ["Annotazioni-Db", "Annotazioni-Ec2"], ... }
function suggestedChildren(key, resources){
    const fixed = new Set(suggestedValues(key));
    const found = {};
    (resources || []).forEach(r => {
        const v = r.tags && r.tags[key];
        if (v === undefined || v === null || String(v).trim() === '') return;
        const s = String(v);
        if (fixed.has(s)) return;
        const parent = suggestedParent(key, s);
        if (parent === null) return;
        (found[parent] = found[parent] || new Set()).add(s);
    });
    const out = {};
    Object.keys(found).forEach(p => {
        out[p] = [...found[p]].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
    });
    return out;
}

// HTML delle <option> di una tendina: "tutti", ogni suggerito seguito dalle sue
// sottovoci (indentate), infine "Altri valori". Il value e' sempre il valore esatto.
function suggestedFilterOptions(key, resources, allLabel){
    const esc = escapeHtml;   // common.js
    const children = suggestedChildren(key, resources);
    const parts = [`<option value="">${esc(allLabel)}</option>`];
    suggestedValues(key).forEach(p => {
        parts.push(`<option value="${esc(p)}">${esc(p)}</option>`);
        (children[p] || []).forEach(c =>
            parts.push(`<option value="${esc(c)}">&nbsp;&nbsp;&nbsp;&nbsp;&#8627; ${esc(c)}</option>`));
    });
    parts.push('<option value="__other__">Altri valori</option>');
    return parts.join('');
}

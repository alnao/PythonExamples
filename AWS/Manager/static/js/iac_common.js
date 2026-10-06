/* Parti comuni delle pagine delle risorse gestite da IaC (Terraform, CloudFormation).
 *
 * Le righe hanno sempre {type, region, arn, tags, tagged}: tags e' {chiave: valore}, tagged
 * dice se la risorsa ha i tag (false = tipo senza tag o tag non noti). Servono anche
 * tag_match.js (sottovalori di Project) e APP.suggestedKeys, APP.requiredTags. */

const TAG_MISSING = '__missing__';   // valore della tendina per "senza questo tag"
const DEFAULT_TAG = 'Project';
const NO_REGION = '__none__';        // valore della tendina per le risorse senza region
const regionKey = (r) => r.region || NO_REGION;

// I tag aws:* (es. aws:cloudformation:stack-name) li mette AWS: non contano come tag della risorsa
const isSystemTag = (k) => k.startsWith('aws:');
const userTags = (tags) => Object.keys(tags || {}).filter(k => !isSystemTag(k));

function iacBadge(text, cls = 'secondary') {
    return `<span class="badge text-bg-${cls}">${escapeHtml(text)}</span>`;
}

function selectOptions(sel, values, allLabel, labelFn = v => v) {
    const prev = sel.value;
    sel.innerHTML = `<option value="">${escapeHtml(allLabel)}</option>`
        + values.map(([v, n]) => `<option value="${escapeHtml(v)}">${escapeHtml(labelFn(v))} (${n})</option>`).join('');
    sel.value = values.some(([v]) => v === prev) ? prev : '';
}

function counts(rows, fn) {
    const out = {};
    rows.forEach(r => { const k = fn(r); out[k] = (out[k] || 0) + 1; });
    return Object.entries(out).sort((a, b) => a[0].localeCompare(b[0]));
}

// Chiavi dei tag: prima quelle di suggested_tags, poi le altre trovate nelle risorse
function renderTagKeySelect(sel, rows, prev) {
    const suggested = APP.suggestedKeys || [];
    const found = [...new Set(rows.flatMap(r => userTags(r.tags)))].filter(k => !suggested.includes(k)).sort();
    const opt = (k) => `<option value="${escapeHtml(k)}">${escapeHtml(k)}</option>`;
    sel.innerHTML = '<option value="">Nessun filtro</option>'
        + `<optgroup label="Suggeriti">${suggested.map(opt).join('')}</optgroup>`
        + (found.length ? `<optgroup label="Altri tag">${found.map(opt).join('')}</optgroup>` : '');
    sel.value = [...sel.options].some(o => o.value === prev) ? prev : '';
}

/* Valori del tag scelto, solo quelli presenti, col numero di risorse. Per le chiavi con
 * i sottovalori (Project) ogni suggerito e' seguito dai valori che lo estendono, come nel
 * Tag Manager (tag_match.js); il filtro e' sempre sul valore esatto.
 * rows: le righe da contare (solo quelle con i tag). */
function renderTagValueSelect(sel, label, key, rows) {
    sel.disabled = !key;
    label.textContent = key ? `Valore di ${key}` : 'Valore';
    if (!key) { sel.innerHTML = '<option value="">Tutti</option>'; return; }
    const prev = sel.value;
    const n = {};
    let missing = 0;
    rows.forEach(r => {
        if (key in r.tags) n[r.tags[key]] = (n[r.tags[key]] || 0) + 1; else missing++;
    });
    const opt = (v, text, count, child = false) =>
        `<option value="${escapeHtml(v)}">${child ? '&nbsp;&nbsp;&nbsp;&nbsp;&#8627; ' : ''}${escapeHtml(text)} (${count})</option>`;
    const parts = ['<option value="">Tutti</option>'];
    if (missing) parts.push(opt(TAG_MISSING, `(senza ${key})`, missing));
    const used = new Set();
    const children = suggestedChildren(key, rows);
    suggestedValues(key).forEach(p => {
        const kids = (children[p] || []).filter(c => n[c]);
        if (!n[p] && !kids.length) return;
        parts.push(n[p] ? opt(p, p, n[p]) : `<option disabled>${escapeHtml(p)}</option>`);
        used.add(p);
        kids.forEach(c => { parts.push(opt(c, c, n[c], true)); used.add(c); });
    });
    const others = Object.keys(n).filter(v => !used.has(v)).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
    if (others.length) {
        parts.push(`<optgroup label="${used.size ? 'Altri valori' : 'Valori'}">`
            + others.map(v => opt(v, v === '' ? '(vuoto)' : v, n[v])).join('') + '</optgroup>');
    }
    sel.innerHTML = parts.join('');
    sel.value = [...sel.options].some(o => o.value === prev && !o.disabled) ? prev : '';
}

function tagMatches(r, key, value) {
    if (!key || !value) return true;
    return value === TAG_MISSING ? r.tagged && !(key in r.tags) : r.tags[key] === value;
}

// Mancano tag obbligatori? Stesse regole dell'icona dei tag (tagIcon in common.js)
function missingRequired(r) {
    if (!r.tagged) return [];
    const rules = APP.tagRules || { required: [], compliant: [], auto: 'aws_auto' };
    if (Object.values(r.tags).includes(rules.auto)) return [];
    if (rules.compliant.some(set => Object.entries(set).every(([k, v]) => r.tags[k] === v))) return [];
    return rules.required.filter(k => !(k in r.tags));
}

// ---------------------------------------------------------------- celle

function regionCell(region) {
    return region === 'global' ? '<span class="badge text-bg-light border">globale</span>' : regionBadge(region);
}

function projectCell(r) {
    if (!r.tagged) return '';
    return 'Project' in r.tags ? escapeHtml(r.tags.Project) : '<span class="badge text-bg-danger">mancante</span>';
}

function tagCountCell(r) {
    return r.tagged ? `${userTags(r.tags).length}${tagIcon(r.tags)}` : '<span class="text-muted">&ndash;</span>';
}

function sortableTh(sort, key, label) {
    return `<th class="sortable" data-sort="${key}">${label}${sort.key === key ? ` <i class="fas fa-caret-${sort.dir > 0 ? 'up' : 'down'}"></i>` : ''}</th>`;
}

/* Sottotabella dei tag: prima quelli di suggested_tags (badge blu, "mancante" in rosso),
 * poi gli altri, in fondo i tag di sistema aws:*; extra = righe di dettaglio sotto. */
function tagsSubTable(r, extra = '', untaggedText = 'Questo tipo di risorsa non ha tag') {
    if (!r.tagged) return `<div class="text-muted small">${escapeHtml(untaggedText)}</div>${extra}`;
    const suggested = APP.suggestedKeys || [];
    const others = userTags(r.tags).filter(k => !suggested.includes(k)).sort();
    const system = Object.keys(r.tags).filter(isSystemTag).sort();
    const tagName = (k, cls) => `<span class="badge text-bg-${cls}"><i class="fas fa-tag me-1"></i>${escapeHtml(k)}</span>`;
    const value = (k) => k in r.tags
        ? (r.tags[k] === '' ? '<span class="text-muted">(vuoto)</span>' : escapeHtml(r.tags[k]))
        : `<span class="badge text-bg-danger">mancante</span>${(APP.requiredTags || []).includes(k) ? ' <span class="small text-danger">obbligatorio</span>' : ''}`;
    return '<table class="table table-sm table-kv tf-tags mb-0"><tbody>'
        + suggested.map(k => `<tr><th>${tagName(k, 'primary')}</th><td>${value(k)}</td></tr>`).join('')
        + others.map(k => `<tr><th>${tagName(k, 'secondary')}</th><td>${value(k)}</td></tr>`).join('')
        + '</tbody></table>'
        + (system.length ? `<div class="small text-muted mt-1">Tag di sistema: ${system.map(k =>
            `<span class="mono">${escapeHtml(k)}=${escapeHtml(r.tags[k])}</span>`).join(' &middot; ')}</div>` : '')
        + (r.arn ? `<div class="small text-muted mt-1">ARN <span class="mono">${escapeHtml(r.arn)}</span></div>` : '')
        + extra;
}

function setupBackToTop() {
    const top = $('backToTop');
    window.addEventListener('scroll', () => top.classList.toggle('show', window.scrollY > 300));
    top.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

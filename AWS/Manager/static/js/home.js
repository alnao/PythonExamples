/* Home: riepilogo dei costi (solo cache, gratis) e delle risorse attive. */

const moneyFmt = new Intl.NumberFormat('it-IT', {
    style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
});

function money(v) {
    if (v === null || v === undefined) return '–';
    if (v !== 0 && Math.abs(v) < 0.01) return (v < 0 ? '-' : '') + '< 0,01 $';
    return moneyFmt.format(v);
}

function monthLabel(ym) {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'long', year: 'numeric' });
}

function serviceLabel(s) { return (APP.serviceAliases || {})[s] || s; }

function deltaHtml(now, before) {
    if (!before) return now ? '<span class="delta-bad">nuovo</span>' : '';
    const d = (now - before) / Math.abs(before) * 100;
    if (Math.abs(d) < 0.5) return '<span class="text-muted">=</span>';
    return d > 0 ? `<span class="delta-bad"><i class="fas fa-arrow-up"></i> +${d.toFixed(0)}%</span>`
        : `<span class="delta-good"><i class="fas fa-arrow-down"></i> ${d.toFixed(0)}%</span>`;
}

function statCard(label, value, note, cls = '', col = 'col-6 col-md-3') {
    return `<div class="${col}"><div class="card stat h-100 ${cls}"><div class="card-body">
        <div class="stat-label">${label}</div><div class="stat-value">${value}</div>
        <div class="stat-note">${note || ''}</div></div></div></div>`;
}

// ---------------------------------------------------------------- costi

const state = { costs: null, groups: {}, groupSeq: 0 };
const GROUP_KEY = 'home.costGroup';   // scelta della tendina, solo in questo browser

/* Tabella "Raggruppa per": per servizio dal riepilogo, per tag da /api/home/costs/group
 * (solo cache e Data Export, come il resto della Home). */
async function renderBreakdown() {
    const group = $('costGroup').value;
    const d = state.costs;
    if (!d) return;
    if (group === 'SERVICE') {
        const cached = (d.months || []).filter(m => m.cached);
        const last = cached[cached.length - 1];
        $('servicesTitle').textContent = last ? `Servizi · ${monthLabel(last.month)}` : 'Servizi';
        $('servicesTable').innerHTML = rowsTable((d.services || []).slice(0, 10), [
            { title: 'Servizio', get: s => escapeHtml(serviceLabel(s.service)) },
            { title: 'Mese prima', cls: 'num text-muted', get: s => money(s.previous) },
            { title: 'Costo', cls: 'num', get: s => money(s.amount) },
        ], 'Nessun costo in cache per questo profilo');
        return;
    }
    const key = group.slice(4);
    $('servicesTitle').textContent = `Tag ${key}`;
    const seq = ++state.groupSeq;
    let g = state.groups[group];
    if (!g) {
        $('servicesTable').innerHTML = loadingHtml();
        try {
            g = await apiGet(`/api/home/costs/group?${query({ group })}`);
            state.groups[group] = g;
        } catch (e) {
            if (seq === state.groupSeq) $('servicesTable').innerHTML = `<div class="alert alert-danger py-2 mb-0">Errore: ${escapeHtml(e.message)}</div>`;
            return;
        }
    }
    if (seq !== state.groupSeq) return;
    if (!g.month) {
        $('servicesTable').innerHTML = `<div class="empty-state">Nessuna serie per tag ${escapeHtml(key)} in cache negli ultimi 3 mesi:
            si carica dal <a href="/costs">Cost Explorer</a> scegliendo ${escapeHtml(key)} in "Secondo grafico per".</div>`;
        return;
    }
    $('servicesTitle').textContent = `Tag ${key} · ${monthLabel(g.month)}`;
    $('servicesTable').innerHTML = rowsTable(g.items.slice(0, 10), [
        { title: key, get: x => x.key === '' ? '<span class="text-muted">(senza tag)</span>' : escapeHtml(x.key) },
        { title: 'Mese prima', cls: 'num text-muted', get: x => money(x.previous) },
        { title: 'Costo', cls: 'num', get: x => money(x.amount) },
    ], 'Nessun costo in cache per questo profilo')
        + (g.items.length > 10 ? `<div class="footer-note">Primi 10 valori su ${g.items.length}</div>` : '')
        + (g.previous_cached ? '' : '<div class="footer-note">Mese prima non in cache per questo tag</div>');
}

async function loadCosts() {
    try {
        const d = await apiGet('/api/home/costs');
        renderCosts(d);
    } catch (e) {
        $('costKpis').innerHTML = `<div class="col-12"><div class="alert alert-danger py-2 mb-0">Errore: ${escapeHtml(e.message)}</div></div>`;
    }
}

function renderCosts(d) {
    const months = d.months || [];
    const byMonth = {};
    months.forEach(m => { byMonth[m.month] = m; });
    const cur = months[months.length - 1];
    const prev = months[months.length - 2];
    const prev2 = months[months.length - 3];
    const cached = months.filter(m => m.cached);

    const cards = [];
    if (cur) {
        const f = d.forecast;
        const note = !cur.cached ? 'non in cache'
            : f ? `stima a fine mese <strong>${money(cur.total + f.amount)}</strong>`
            : (cur.complete ? '' : `letto il ${fmtDate(cur.loaded_at)}`);
        cards.push(statCard(`Mese in corso (${escapeHtml(monthLabel(cur.month))})`,
            cur.cached ? money(cur.total) : '–', note, cur.cached ? '' : 'stat-warning'));
    }
    if (prev) {
        const note = prev.cached && prev2 && prev2.cached
            ? `${deltaHtml(prev.total, prev2.total)} rispetto a ${escapeHtml(monthLabel(prev2.month))}` : (prev.cached ? '' : 'non in cache');
        cards.push(statCard(`Mese precedente (${escapeHtml(monthLabel(prev.month))})`,
            prev.cached ? money(prev.total) : '–', note, prev.cached ? '' : 'stat-warning'));
    }
    const tot = cached.reduce((a, m) => a + m.total, 0);
    cards.push(statCard('Ultimi 3 mesi', cached.length ? money(tot) : '–',
        cached.length < months.length ? `${cached.length} mesi su ${months.length} in cache` : 'tutti i mesi in cache'));
    if (d.untagged) {
        const pct = d.untagged.total ? d.untagged.amount / d.untagged.total * 100 : 0;
        cards.push(statCard(`Senza tag ${escapeHtml(d.untagged.key)}`,
            `${pct.toLocaleString('it-IT', { maximumFractionDigits: 1 })}%`,
            `${money(d.untagged.amount)} in ${escapeHtml(monthLabel(d.untagged.month))}`,
            pct > 50 ? 'stat-warning' : ''));
    } else {
        cards.push(statCard('Senza tag', '–', 'nessuna serie per tag in cache'));
    }
    $('costKpis').innerHTML = cards.join('');

    state.costs = d;
    renderBreakdown();

    $('monthsTable').innerHTML = rowsTable(months.slice().reverse(), [
        { title: 'Mese', get: m => escapeHtml(monthLabel(m.month)) },
        { title: 'Totale', cls: 'num', get: m => m.cached ? money(m.total) : '<span class="text-muted">non in cache</span>' },
        { title: 'Fonte', get: m => !m.cached ? '' : m.source === 'cur'
            ? '<span class="badge text-bg-success">Data Export</span>'
            : `<span class="badge text-bg-secondary">cache API</span>${m.complete ? '' : ' *'}` },
    ]);
    const missing = months.filter(m => !m.cached);
    $('costNote').innerHTML = (missing.length
        ? `<i class="fas fa-circle-info me-1"></i>Mesi non in cache: si caricano dal <a href="/costs">Cost Explorer</a> (con conferma, 0,01 $ a richiesta). `
        : '')
        + `Metrica ${escapeHtml(d.metric)}, profilo ${escapeHtml(d.profile)}`
        + (d.cur_enabled ? '' : ' &middot; Data Export non configurato (.env)')
        + (months.some(m => m.cached && !m.complete && m.source !== 'cur') ? ' &middot; * letto prima della fine del mese' : '');
}

// ---------------------------------------------------------------- risorse

/* Colonne della tabella: (chiave, titolo, icona, formato del valore, classe della cella
 * in base ai numeri, nota). S3 sta sulla riga della region del bucket, CloudFront e'
 * globale. */
const COLUMNS = [
    ['ec2', 'EC2 accese', 'fa-server', c => `${c.value} / ${c.total}`, c => c.value ? 'cell-ok' : '', 'istanze accese / totali'],
    ['rds', 'RDS disponibili', 'fa-database', c => `${c.value} / ${c.total}`, c => c.value ? 'cell-ok' : '', 'istanze disponibili / totali'],
    ['lambda', 'Lambda', 'fa-bolt', c => c.value, () => '', 'funzioni'],
    ['dynamodb', 'DynamoDB', 'fa-table', c => c.value, () => '', 'tabelle'],
    ['s3', 'S3', 'fa-bucket', c => c.value, () => '', 'bucket nella region'],
    ['cloudfront', 'CloudFront', 'fa-globe', c => `${c.value} / ${c.total}`, () => '', 'distribuzioni attive / totali (globale)'],
    ['load_balancers', 'Load balancer', 'fa-scale-balanced', c => c.value, c => c.value ? 'cell-warning' : '', 'costano anche senza traffico'],
    ['eip', 'EIP non associati', 'fa-location-dot', c => `${c.value} / ${c.total}`, c => c.value ? 'cell-warning' : '', 'un IP non associato si paga'],
    ['alarms', 'Allarmi in ALARM', 'fa-bell', c => `${c.value} / ${c.total}`, c => c.value ? 'cell-danger' : '', 'allarmi in stato ALARM / totali'],
];

async function loadResources() {
    $('resourcesTable').innerHTML = loadingHtml('Lettura delle risorse da AWS...');
    const started = Date.now();
    try {
        const d = await apiGet('/api/home/resources');
        renderResources(d);
        $('resourcesHint').textContent = `${d.regions.length} region · letto in ${((Date.now() - started) / 1000).toFixed(1)} s`;
    } catch (e) {
        $('resourcesTable').innerHTML = `<div class="alert alert-danger py-2 mb-0">Errore: ${escapeHtml(e.message)}</div>`;
    }
}

function resourceCell(c, fmt, cls) {
    if (!c) return '<td class="num"></td>';
    if (c.error) return `<td class="num"><span class="text-danger" title="${escapeHtml(c.error)}"><i class="fas fa-triangle-exclamation"></i></span></td>`;
    if (!c.value && !c.total) return '<td class="num"><span class="text-muted">0</span></td>';
    return `<td class="num ${cls(c)}"><strong>${fmt(c)}</strong></td>`;
}

/* Una riga per region della lista, una per i servizi globali e il totale. */
function renderResources(d) {
    const head = '<thead class="table-light"><tr><th>Region</th>'
        + COLUMNS.map(([, label, icon, , , note]) =>
            `<th class="num" title="${escapeHtml(note)}"><i class="fas ${icon} me-1 text-secondary"></i>${escapeHtml(label)}</th>`).join('')
        + '</tr></thead>';
    const row = (title, counts) => `<tr><td>${title}</td>`
        + COLUMNS.map(([key, , , fmt, cls]) => resourceCell(counts[key], fmt, cls)).join('') + '</tr>';
    const g = d.global || {};
    const globalTitle = '<span class="badge text-bg-light border"><i class="fas fa-earth-europe me-1"></i>globale</span>'
        + (g.s3 && g.s3.regions ? ` <span class="small text-muted" title="Bucket S3 in region fuori dalla lista">S3: ${escapeHtml(g.s3.regions.join(', '))}</span>` : '');
    const totals = d.totals || {};
    const foot = '<tfoot><tr><td>Totale</td>'
        + COLUMNS.map(([key, , , fmt]) => `<td class="num">${totals[key] ? fmt(totals[key]) : '–'}</td>`).join('')
        + '</tr></tfoot>';
    $('resourcesTable').innerHTML = '<div class="table-responsive"><table class="table table-sm table-hover align-middle mb-0 cost-table resources-table">'
        + head + '<tbody>'
        + d.regions.map(r => row(regionBadge(r.region), r.counts)).join('')
        + row(globalTitle, g)
        + '</tbody>' + foot + '</table></div>';
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        const saved = localStorage.getItem(GROUP_KEY);
        if (saved && [...$('costGroup').options].some(o => o.value === saved)) $('costGroup').value = saved;
    } catch (e) { /* storage non disponibile: resta Servizio */ }
    $('costGroup').addEventListener('change', () => {
        try { localStorage.setItem(GROUP_KEY, $('costGroup').value); } catch (e) { /* ignorato */ }
        renderBreakdown();
    });
    loadCosts();
    loadResources();
    $('btnResources').addEventListener('click', loadResources);
});

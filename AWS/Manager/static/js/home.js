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

    // servizi del mese piu' recente in cache
    const last = cached[cached.length - 1];
    $('servicesTitle').textContent = last ? `Servizi · ${monthLabel(last.month)}` : 'Servizi';
    const services = (d.services || []).slice(0, 10);
    $('servicesTable').innerHTML = rowsTable(services, [
        { title: 'Servizio', get: s => escapeHtml(serviceLabel(s.service)) },
        { title: 'Costo', cls: 'num', get: s => money(s.amount) },
        { title: 'Mese prima', cls: 'num', get: s => money(s.previous) },
        { title: 'Variazione', cls: 'num', get: s => deltaHtml(s.amount, s.previous) },
    ], 'Nessun costo in cache per questo profilo');

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

// (chiave, etichetta, icona, formato del valore, classe in base ai numeri)
const COUNTERS = [
    ['ec2', 'EC2 accese', 'fa-server', c => `${c.value} / ${c.total}`, c => c.value ? 'stat-ok' : ''],
    ['rds', 'RDS disponibili', 'fa-database', c => `${c.value} / ${c.total}`, c => c.value ? 'stat-ok' : ''],
    ['lambda', 'Funzioni Lambda', 'fa-bolt', c => c.value, () => ''],
    ['dynamodb', 'Tabelle DynamoDB', 'fa-table', c => c.value, () => ''],
    ['load_balancers', 'Load balancer', 'fa-scale-balanced', c => c.value, c => c.value ? 'stat-warning' : ''],
    ['nat', 'NAT Gateway', 'fa-route', c => c.value, c => c.value ? 'stat-warning' : ''],
    ['eip', 'Elastic IP non associati', 'fa-location-dot', c => `${c.value} / ${c.total}`, c => c.value ? 'stat-warning' : ''],
    ['alarms', 'Allarmi in ALARM', 'fa-bell', c => `${c.value} / ${c.total}`, c => c.value ? 'stat-danger' : ''],
    ['s3', 'Bucket S3', 'fa-bucket', c => c.value, () => ''],
    ['cloudfront', 'CloudFront attive', 'fa-globe', c => `${c.value} / ${c.total}`, () => ''],
];
const NOTES = {
    load_balancers: 'costano anche senza traffico',
    nat: 'circa 32 $ al mese ciascuno, piu\' il traffico',
    eip: 'un IP non associato si paga',
    alarms: 'allarmi in stato ALARM / totali',
    s3: 'globale', cloudfront: 'globale',
};

async function loadResources() {
    $('resourceKpis').innerHTML = `<div class="col-12">${loadingHtml('Lettura delle risorse da AWS...')}</div>`;
    $('resourcesTable').innerHTML = '';
    const started = Date.now();
    try {
        const d = await apiGet('/api/home/resources');
        renderResources(d);
        $('resourcesHint').textContent = `${d.region === ALL ? `${d.regions.length} region` : d.region} · letto in ${((Date.now() - started) / 1000).toFixed(1)} s`;
    } catch (e) {
        $('resourceKpis').innerHTML = `<div class="col-12"><div class="alert alert-danger py-2 mb-0">Errore: ${escapeHtml(e.message)}</div></div>`;
    }
}

function renderResources(d) {
    const totals = d.totals || {};
    $('resourceKpis').innerHTML = COUNTERS.map(([key, label, icon, fmt, cls]) => {
        const c = totals[key];
        const errors = [...d.regions.map(r => r.counts[key]), d.global[key]].filter(x => x && x.error);
        const note = errors.length ? `<span class="text-danger" title="${escapeHtml(errors.map(e => e.error).join('\n'))}">${errors.length} errori</span>`
            : (NOTES[key] || '');
        return statCard(`<i class="fas ${icon} me-1"></i>${label}`, c ? fmt(c) : '–', note, c ? cls(c) : '',
            'col-6 col-md-4 col-xl-2');
    }).join('');

    const regional = COUNTERS.filter(([key]) => !['s3', 'cloudfront'].includes(key));
    $('resourcesTable').innerHTML = rowsTable(d.regions, [
        { title: 'Region', get: r => regionBadge(r.region) },
        ...regional.map(([key, label, , fmt]) => ({
            title: label, cls: 'num',
            get: r => {
                const c = r.counts[key];
                if (!c) return '';
                if (c.error) return `<span class="text-danger" title="${escapeHtml(c.error)}"><i class="fas fa-triangle-exclamation"></i></span>`;
                return c.value || c.total ? `<strong>${fmt(c)}</strong>` : '<span class="text-muted">0</span>';
            },
        })),
    ]);
}

document.addEventListener('DOMContentLoaded', () => {
    loadCosts();
    loadResources();
    $('btnResources').addEventListener('click', loadResources);
});

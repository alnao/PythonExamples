/* Grafici a barre verticali (Chart.js) e formattazione condivisa.
 *
 * Regole seguite:
 *  - 8 colori categorici in ordine fisso (validati per il daltonismo), mai generati:
 *    oltre l'ottava voce si finisce in "Altri"
 *  - il colore segue la voce e non la sua posizione: filtrando, le voci rimaste
 *    tengono il loro colore (vedi assignColors)
 *  - barre sottili, angoli arrotondati solo in cima alla pila, 2px di stacco
 *    color superficie tra i segmenti, griglia leggera
 */

const CSS = getComputedStyle(document.documentElement);
const css = (name) => CSS.getPropertyValue(name).trim();

const PALETTE = [1, 2, 3, 4, 5, 6, 7, 8].map(i => css(`--series-${i}`));
const COLOR_UNTAGGED = css('--series-untagged');
const COLOR_OTHER = css('--series-other');
const SURFACE = css('--surface-1');
const INK_SECONDARY = css('--text-secondary');
const INK_MUTED = css('--text-muted');
const GRIDLINE = css('--gridline');
const BASELINE = css('--baseline');

// Chiave interna della voce che raccoglie tutto cio' che esce dal top N
const OTHER_KEY = '__other__';

const moneyFmt = new Intl.NumberFormat('it-IT', {
    style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
});
const moneyShortFmt = new Intl.NumberFormat('it-IT', {
    style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol',
    notation: 'compact', maximumFractionDigits: 1,
});

// Importi AWS: spesso frazioni di centesimo, che non vanno mostrate come "0,00 $"
function money(v) {
    if (v === 0) return moneyFmt.format(0);
    if (Math.abs(v) < 0.01) return (v < 0 ? '-' : '') + '< 0,01 $';
    return moneyFmt.format(v);
}

function moneyTick(v) {
    return Math.abs(v) >= 1000 ? moneyShortFmt.format(v) : moneyFmt.format(v);
}

function monthLabel(ym) {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'short', year: 'numeric' });
}

function dayLabel(iso) {
    const [, m, d] = iso.split('-');
    return `${d}/${m}`;
}

/* Colori per le voci mostrate, nell'ordine in cui compaiono.
 * rank: {voce: posizione nella classifica sull'intero caricamento}: le prime 8 hanno
 * il loro slot fisso, le altre prendono il primo slot libero in questa vista.
 * special: {voce: colore} per le voci con colore riservato (senza tag, Altri). */
function assignColors(keys, rank, special = {}) {
    const out = {};
    const used = new Set();
    keys.forEach(k => {
        if (special[k]) { out[k] = special[k]; return; }
        const r = rank[k];
        if (r !== undefined && r < PALETTE.length && !used.has(r)) { out[k] = PALETTE[r]; used.add(r); }
    });
    keys.forEach(k => {
        if (out[k]) return;
        const free = PALETTE.findIndex((_, i) => !used.has(i));
        out[k] = free >= 0 ? PALETTE[free] : COLOR_OTHER;
        if (free >= 0) used.add(free);
    });
    return out;
}

/* Il segmento e' l'ultimo positivo visibile della sua colonna? Solo quello ha
 * gli angoli arrotondati, la base resta squadrata. */
function isTopOfStack(ctx) {
    const chart = ctx.chart;
    const i = ctx.dataIndex;
    for (let d = chart.data.datasets.length - 1; d >= 0; d--) {
        if (!chart.isDatasetVisible(d)) continue;
        const v = chart.data.datasets[d].data[i];
        if (v > 0) return d === ctx.datasetIndex;
    }
    return false;
}

/* Crea (o ricrea) un grafico a barre verticali.
 * cfg: {labels, series: [{key, label, color, data}], stacked, onClick(key),
 *       axisPointer: manina sulle etichette dell'asse x (cliccabili per lo zoom),
 *       ignoreClick() vero quando il clic chiude un trascinamento (zoom)} */
function renderBarChart(canvas, previous, cfg) {
    if (previous) previous.destroy();
    const stacked = cfg.stacked !== false;

    const datasets = cfg.series.map(s => ({
        label: s.label,
        entityKey: s.key,
        data: s.data,
        backgroundColor: s.color,
        hoverBackgroundColor: s.color,
        borderColor: SURFACE,
        borderWidth: stacked ? { top: 2, right: 0, bottom: 0, left: 0 } : 0,
        borderRadius: stacked
            ? (ctx) => isTopOfStack(ctx) ? { topLeft: 4, topRight: 4 } : 0
            : { topLeft: 4, topRight: 4 },
        borderSkipped: 'start',
        maxBarThickness: stacked ? 24 : 12,
        barPercentage: stacked ? 0.9 : 0.85,
        categoryPercentage: 0.8,
    }));

    return new Chart(canvas, {
        type: 'bar',
        data: { labels: cfg.labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 250 },
            interaction: { mode: 'nearest', intersect: true },
            onHover: (evt, els, chart) => {
                const onAxis = cfg.axisPointer && evt.y > chart.chartArea.bottom;
                evt.native.target.style.cursor = (els.length && cfg.onClick) || onAxis ? 'pointer' : 'default';
            },
            onClick: (evt, els, chart) => {
                if (!els.length || (cfg.ignoreClick && cfg.ignoreClick())) return;
                if (cfg.onClick) cfg.onClick(chart.data.datasets[els[0].datasetIndex].entityKey);
            },
            scales: {
                x: {
                    stacked,
                    grid: { display: false },
                    border: { color: BASELINE },
                    ticks: { color: INK_MUTED, font: { size: 11 } },
                },
                y: {
                    stacked,
                    beginAtZero: true,
                    grid: { color: GRIDLINE, lineWidth: 1 },
                    border: { display: false },
                    ticks: { color: INK_MUTED, font: { size: 11 }, callback: moneyTick, maxTicksLimit: 6 },
                },
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: INK_SECONDARY, boxWidth: 10, boxHeight: 10,
                        useBorderRadius: true, borderRadius: 2, font: { size: 11 },
                    },
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const tot = columnTotal(ctx.chart, ctx.dataIndex);
                            const pct = tot ? ` (${(ctx.parsed.y / tot * 100).toFixed(1)}%)` : '';
                            return ` ${ctx.dataset.label}: ${money(ctx.parsed.y)}${pct}`;
                        },
                        footer: (items) => items.length
                            ? `Totale ${items[0].label}: ${money(columnTotal(items[0].chart, items[0].dataIndex))}`
                            : '',
                    },
                },
            },
        },
    });
}

// Indice della colonna sotto la coordinata x (in pixel del canvas)
function bucketIndexAt(chart, x) {
    const n = chart.data.labels.length;
    const i = Math.round(chart.scales.x.getValueForPixel(x));
    return Math.max(0, Math.min(n - 1, i));
}

function columnTotal(chart, index) {
    return chart.data.datasets.reduce((acc, ds, d) =>
        acc + (chart.isDatasetVisible(d) ? (ds.data[index] || 0) : 0), 0);
}

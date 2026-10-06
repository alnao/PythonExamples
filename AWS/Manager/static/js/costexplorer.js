/* Cost Explorer - logica della pagina (ex AWS/Managers/CostExplorer).
 *
 * Il profilo e' quello scelto nella navbar (APP.profile); la tendina "Region costi" e'
 * un filtro sui costi, indipendente dalla region delle altre sezioni. Le funzioni comuni
 * ($, escapeHtml, messaggi, spinner, apiGet) sono in common.js.
 *
 * Dati: il server tiene in cache, mese per mese e senza scadenza, due serie di costi
 * raggruppate per SERVICE e per il secondo criterio (tag o dimensione): una al mese e
 * una al giorno. Da quelle righe {period, month, service, group, amount} il browser
 * calcola grafici, tabelle, riepilogo e filtri incrociati senza altre chiamate.
 *
 * Zoom: grafici, tabelle e totale mostrano un intervallo (tutto il periodo, un mese,
 * una settimana o un tratto scelto trascinando) raggruppato per mesi, settimane o
 * giorni. Settimane e giorni usano la serie giornaliera dei mesi interessati.
 *
 * Fonti: per ogni mese il server usa il Data Export su S3 (gratis) se ha quel mese,
 * altrimenti i mesi gia' letti con l'API di Cost Explorer; months[].source dice quale.
 *
 * Costi: la pagina non chiama mai AWS da sola. A ogni cambio chiede al server solo cio'
 * che e' gia' in cache (cache_only=1, gratis); se per la vista manca qualcosa compare
 * "Carica i dati dal cloud", che apre una modale con le richieste e il loro costo.
 */

const state = {
    monthly: null,       // /api/ce/costs al mese per il periodo (solo i mesi in cache)
    daily: null,         // /api/ce/costs al giorno per il periodo (solo i mesi in cache)
    ready: false,        // la vista corrente ha tutti i dati che le servono
    forecast: null,      // stima di fine mese (se in cache per oggi)
    forecastCached: false,
    tags: [],            // cost allocation tag del Billing
    tagsMissing: false,
    rank: { service: {}, group: {} },   // classifica per il colore stabile delle voci
    zoom: null,          // {start, end} (date ISO comprese) o null = tutto il periodo
    zoomStack: [],       // livelli precedenti, per "indietro"
    bucket: 'auto',      // month | week | day | auto
    view: null,          // ultima vista disegnata (intervallo, colonne)
    charts: {},
    tables: {},          // righe per l'esportazione CSV
    expanded: new Set(),  // padri con i sottovalori aperti nella tabella per tag (chiusi di default)
    drill: { service: null, data: null, chart: null, seq: 0 },
    missing: [],         // richieste che mancano alla vista corrente
    modalItems: [],      // richieste proposte nella modale
    seq: 0,              // scarta le risposte arrivate dopo un cambio di parametri
    draggedAt: 0,        // il clic che chiude un trascinamento non deve filtrare
    apiCalls: 0,
};

const NONE = '__none__';   // valore delle tendine per "senza tag"

/* apiGet (common.js) che in piu' aggiorna il contatore delle chiamate a Cost Explorer. */
async function ceGet(url) {
    const j = await apiGet(url);
    if (j.api_calls_session !== undefined) {
        state.apiCalls = j.api_calls_session;
        $('apiCalls').innerHTML = `<i class="fas fa-receipt me-1"></i>Chiamate CE: ${j.api_calls_session}`
            + ` (${money(j.api_cost_session)})`;
    }
    return j;
}

// ----------------------------------------------------------------------
// Date (sempre stringhe ISO locali: 'YYYY-MM-DD' e 'YYYY-MM')
// ----------------------------------------------------------------------

function iso(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function parseIso(s) { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); }
function addDays(s, n) { const d = parseIso(s); d.setDate(d.getDate() + n); return iso(d); }
function todayIso() { return iso(new Date()); }
function currentMonth() { return todayIso().slice(0, 7); }
function lastDayOfMonth(ym) { const [y, m] = ym.split('-').map(Number); return iso(new Date(y, m, 0)); }
function daysBetween(a, b) { return Math.round((parseIso(b) - parseIso(a)) / 86400000) + 1; }
function minIso(a, b) { return a < b ? a : b; }
function maxIso(a, b) { return a > b ? a : b; }

// Lunedi' della settimana di una data (settimane ISO, da lunedi' a domenica)
function mondayOf(s) {
    const d = parseIso(s);
    d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    return iso(d);
}

function monthsBetween(a, b) {
    const out = [];
    let [y, m] = a.split('-').map(Number);
    while (`${y}-${String(m).padStart(2, '0')}` <= b) {
        out.push(`${y}-${String(m).padStart(2, '0')}`);
        if (++m > 12) { m = 1; y++; }
    }
    return out;
}

function lastMonths(n) {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() - (n - 1));
    return { start: iso(d).slice(0, 7), end: currentMonth() };
}

// Blocchi di mesi consecutivi: ognuno e' una richiesta ad AWS
function monthRuns(months) {
    const runs = [];
    [...months].sort().forEach(m => {
        const last = runs.length ? runs[runs.length - 1] : null;
        if (last && monthsBetween(last[last.length - 1], m).length === 2) last.push(m);
        else runs.push([m]);
    });
    return runs;
}

function shortDay(s) {
    return parseIso(s).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
}

function weekLabel(a, b) {
    if (a === b) return shortDay(a);
    return a.slice(0, 7) === b.slice(0, 7)
        ? `${Number(a.slice(8))}–${shortDay(b)}`
        : `${shortDay(a)} – ${shortDay(b)}`;
}

function monthsText(months) {
    return months.map(monthLabel).join(', ');
}

// Etichetta di un intervallo: "set 2026", "14–20 set", "lug 2026 – set 2026"...
function rangeLabel(r) {
    const m1 = r.start.slice(0, 7), m2 = r.end.slice(0, 7);
    const wholeStart = r.start.endsWith('-01');
    const wholeEnd = r.end === lastDayOfMonth(m2) || r.end === todayIso();
    if (wholeStart && wholeEnd) return m1 === m2 ? monthLabel(m1) : `${monthLabel(m1)} – ${monthLabel(m2)}`;
    return weekLabel(r.start, r.end);
}

// ----------------------------------------------------------------------
// Voci: servizi e valori del secondo raggruppamento
// ----------------------------------------------------------------------

// Secondo raggruppamento: quello dei dati mostrati, o quello indicato (es. la tendina)
function groupInfo(group) {
    const g = group || (state.monthly && state.monthly.group) || $('group').value;
    const [kind, key] = g.split(':');
    const isTag = kind === 'TAG';
    return {
        group: g, kind, key, isTag,
        name: isTag ? `tag ${key}` : (APP.secondDimensions[key] || key),
        prefix: isTag && APP.prefixMatchKeys.includes(key),
    };
}

function serviceLabel(s) { return APP.serviceAliases[s] || s; }

function groupLabel(v) {
    if (v === '') return groupInfo().isTag ? '(senza tag)' : '(nessuno)';
    return v;
}

// Il "padre" di un valore: il suggerito del TagManager piu' lungo che il valore
// estende (Paths.games.aws.serverless -> Paths.games). Stessa regola del TagManager.
function suggestedParent(value) {
    const info = groupInfo();
    if (!info.prefix || value === '') return null;
    let best = null;
    ((APP.suggestedTags || {})[info.key] || []).map(String).forEach(p => {
        if (value !== p && value.startsWith(p) && (best === null || p.length > best.length)) best = p;
    });
    return best;
}

function rollupOn() { return groupInfo().prefix && $('rollup').checked; }

// Valore del gruppo come compare in grafici e filtri (col padre se si raggruppa)
function normGroup(v) {
    if (!rollupOn()) return v;
    return suggestedParent(v) || v;
}

function enc(v) { return v === '' ? NONE : v; }
function dec(v) { return v === NONE ? '' : v; }

// ----------------------------------------------------------------------
// Parametri e richieste
// ----------------------------------------------------------------------

function serverParams() {
    return {
        profile: APP.profile,
        start: $('startMonth').value,
        end: $('endMonth').value,
        metric: $('metric').value,
        group: $('group').value,
        region: $('region').value,
        exclude: $('exclude').checked ? '1' : '0',
    };
}

// Mesi del periodo scelto, senza quelli futuri
function periodMonths() {
    const p = serverParams();
    return monthsBetween(p.start, p.end).filter(m => m <= currentMonth());
}

function costsUrl(granularity, extra = {}) {
    const p = serverParams();
    return '/api/ce/costs?' + new URLSearchParams({ ...p, granularity, ...extra }).toString();
}

// Stato di ogni mese in una serie: {mese: {cached, complete, loaded_at, ...}}
function monthsMap(resp) {
    const out = {};
    ((resp && resp.months) || []).forEach(m => { out[m.month] = m; });
    return out;
}

function costsRequest(granularity, months, refresh = false) {
    const daily = granularity === 'DAILY';
    const runs = monthRuns(months);
    return {
        id: daily ? 'daily' : 'monthly',
        url: costsUrl(granularity, { months: months.join(','), ...(refresh ? { refresh: '1' } : {}) }),
        label: `Costi ${daily ? 'al giorno' : 'al mese'} per servizio e per ${groupInfo($('group').value).name}: ${monthsText(months)}`,
        note: [$('metric').value, $('region').value ? `region ${$('region').value}` : '',
            $('exclude').checked ? 'senza tasse e crediti' : ''].filter(Boolean).join(', '),
        calls: runs.length,
        // tanti giorni in una sola richiesta: AWS puo' dividere la risposta in pagine
        pages: daily && runs.some(r => r.length > 1),
        checked: true,
    };
}

function tagsRequest(refresh = false) {
    return {
        id: 'tags',
        url: `/api/ce/tags?profile=${encodeURIComponent(APP.profile)}${refresh ? '&refresh=1' : ''}`,
        label: 'Elenco dei cost allocation tag del Billing',
        note: refresh ? 'serve solo se hai attivato o disattivato dei tag' : '',
        calls: 1, checked: !refresh,
    };
}

function forecastRequest() {
    return {
        id: 'forecast',
        url: `/api/ce/forecast?${new URLSearchParams(serverParams()).toString()}`,
        label: `Stima dei costi a fine mese, calcolata oggi (${new Date().toLocaleDateString('it-IT')})`,
        note: 'get-cost-forecast: una stima per giorno',
        calls: 1, checked: true,
    };
}

// ----------------------------------------------------------------------
// Lettura dalla cache (gratis) e dal cloud (dopo conferma)
// ----------------------------------------------------------------------

/* Legge dal server tutto cio' che e' in cache per il periodo (nessuna chiamata ad AWS).
 * keepZoom: dopo un caricamento dal cloud la vista resta dov'era. */
async function loadFromCache({ keepZoom = false } = {}) {
    const p = serverParams();
    if (!p.start || !p.end) { showAlertHtml('Indicare il periodo'); return; }
    const seq = ++state.seq;
    if (!keepZoom) { state.zoom = null; state.zoomStack = []; state.bucket = 'auto'; }
    try {
        // prima i tag: possono cambiare la scelta del secondo grafico
        const tags = await ceGet(`/api/ce/tags?profile=${encodeURIComponent(p.profile)}&cache_only=1`);
        if (seq !== state.seq) return;
        state.tagsMissing = !!tags.missing;
        state.tags = tags.missing ? [] : (tags.tags || []);
        renderGroupSelect();

        const inPeriod = p.start <= currentMonth() && currentMonth() <= p.end;
        const [monthly, daily, forecast] = await Promise.all([
            ceGet(costsUrl('MONTHLY', { cache_only: '1' })),
            ceGet(costsUrl('DAILY', { cache_only: '1' })),
            inPeriod ? ceGet(`${forecastRequest().url}&cache_only=1`) : Promise.resolve({ missing: true }),
        ]);
        if (seq !== state.seq) return;
        state.monthly = monthly;
        state.daily = daily;
        state.forecastCached = !forecast.missing;
        state.forecast = forecast.missing ? null : forecast.forecast;
        $('alertBox').innerHTML = '';
        computeRanks();
        renderFilterSelects();
        renderTagNotes();
        refreshView();
    } catch (e) {
        showAlertHtml(`Errore: ${escapeHtml(e.message)}`);
    }
}

/* Cosa manca alla vista corrente: per ogni mese del periodo la serie mensile (o quella
 * giornaliera) per riepilogo e grafico per mesi, e la serie giornaliera dei mesi
 * zoomati quando si raggruppa per settimane o giorni. */
function computeMissing() {
    const mInfo = monthsMap(state.monthly), dInfo = monthsMap(state.daily);
    const v = viewSpec();
    const dailyMissing = v.needDaily
        ? monthsBetween(v.range.start.slice(0, 7), v.range.end.slice(0, 7)).filter(m => !(dInfo[m] || {}).cached)
        : [];
    // un mese con la serie giornaliera non ha bisogno di quella mensile
    const monthlyMissing = periodMonths().filter(m =>
        !(mInfo[m] || {}).cached && !(dInfo[m] || {}).cached && !dailyMissing.includes(m));
    const items = [];
    if (state.tagsMissing) items.push(tagsRequest());
    if (monthlyMissing.length) items.push(costsRequest('MONTHLY', monthlyMissing));
    if (dailyMissing.length) items.push(costsRequest('DAILY', dailyMissing));
    return items;
}

// Mesi del periodo letti con l'API prima della loro fine (per "aggiorna"); quelli del
// Data Export si aggiornano da soli quando AWS riscrive i file
function incompleteRequests() {
    const mInfo = monthsMap(state.monthly), dInfo = monthsMap(state.daily);
    const stale = (i) => i && i.cached && i.source === 'api' && !i.complete;
    const monthly = periodMonths().filter(m => stale(mInfo[m]));
    const daily = periodMonths().filter(m => stale(dInfo[m]));
    const items = [];
    if (monthly.length) items.push(costsRequest('MONTHLY', monthly, true));
    if (daily.length) items.push(costsRequest('DAILY', daily, true));
    items.push(tagsRequest(true));
    return items;
}

// Riquadro e pulsante "Carica i dati dal cloud": visibili solo se manca qualcosa
function renderCloudPrompt() {
    const miss = state.missing;
    const costs = miss.filter(r => r.id !== 'tags');
    const calls = miss.reduce((a, r) => a + r.calls, 0);
    $('cloudPrompt').classList.toggle('d-none', !miss.length);
    $('btnCloud').disabled = !miss.length;
    $('btnCloud').innerHTML = miss.length
        ? '<i class="fas fa-cloud-arrow-down me-1"></i>Carica i dati dal cloud'
        : '<i class="fas fa-check me-1"></i>Dati in cache';
    if (!miss.length) return;
    $('cloudPromptTitle').textContent = costs.length
        ? `Mancano dati per ${rangeLabel(viewSpec().range)}`
        : 'Manca l\'elenco dei tag';
    $('cloudPromptText').innerHTML = 'Da leggere: ' + miss.map(r => escapeHtml(r.label)).join('; ')
        + `. Costa ${miss.some(r => r.pages) ? 'almeno ' : ''}${money(calls * APP.apiCost)}; i mesi già in cache non vengono riletti.`;
}

// Modale di conferma: richieste (selezionabili), costo e avviso
function openCloudModal(items, intro) {
    state.modalItems = items;
    $('cloudModalIntro').innerHTML = intro;
    $('cloudModalBody').innerHTML = items.map((r, i) => `<tr>
        <td><input class="form-check-input cloud-item" type="checkbox" data-i="${i}" ${r.checked ? 'checked' : ''}></td>
        <td>${escapeHtml(r.label)}${r.note ? `<div class="small text-muted">${escapeHtml(r.note)}</div>` : ''}
            ${r.pages ? '<div class="small text-muted"><i class="fas fa-circle-info me-1"></i>più giorni in una richiesta: AWS può dividere la risposta in pagine, 0,01 $ ciascuna</div>' : ''}</td>
        <td class="num">${r.calls}${r.pages ? '+' : ''}</td>
        <td class="num">${r.pages ? 'da ' : ''}${money(r.calls * APP.apiCost)}</td></tr>`).join('');
    document.querySelectorAll('.cloud-item').forEach(c => c.addEventListener('change', () => {
        state.modalItems[Number(c.dataset.i)].checked = c.checked;
        renderModalTotal();
    }));
    renderModalTotal();
    bootstrap.Modal.getOrCreateInstance($('cloudModal')).show();
}

function renderModalTotal() {
    const sel = state.modalItems.filter(r => r.checked);
    const calls = sel.reduce((a, r) => a + r.calls, 0);
    const atLeast = sel.some(r => r.pages);
    $('cloudModalFoot').innerHTML = `<tr><td></td><td>Totale</td><td class="num">${calls}${atLeast ? '+' : ''}</td>
        <td class="num">${atLeast ? 'da ' : ''}${money(calls * APP.apiCost)}</td></tr>`;
    $('cloudModalWarning').innerHTML = `<i class="fas fa-triangle-exclamation fa-lg mt-1"></i><div>
        <strong>Attenzione: costa ${atLeast ? 'almeno ' : ''}${money(calls * APP.apiCost)}</strong>,
        addebitati sulla fattura AWS dell'account del profilo <strong>${escapeHtml(APP.profile)}</strong>
        (${money(APP.apiCost)} per richiesta a Cost Explorer). I dati letti restano in cache senza scadenza
        e rivederli non costa nulla.</div>`;
    $('btnCloudConfirm').disabled = !sel.length;
}

// Dopo la conferma: esegue le richieste scelte e ridisegna la pagina dalla cache
async function loadFromCloud() {
    const items = state.modalItems.filter(r => r.checked);
    bootstrap.Modal.getOrCreateInstance($('cloudModal')).hide();
    if (!items.length) return;
    spinner(true);
    const before = state.apiCalls;
    try {
        const tags = items.find(r => r.id === 'tags');
        if (tags) await ceGet(tags.url);
        await Promise.all(items.filter(r => r.id !== 'tags').map(r => ceGet(r.url)));
        await loadFromCache({ keepZoom: true });
        const done = state.apiCalls - before;
        appendAlertHtml(`<i class="fas fa-cloud-arrow-down me-1"></i>Letti da AWS: ${done} richieste, ${money(done * APP.apiCost)}.`, 'success');
    } catch (e) {
        showAlertHtml(`Errore: ${escapeHtml(e.message)}`);
        await loadFromCache({ keepZoom: true });
    } finally {
        spinner(false);
    }
}

/* Tendina "Secondo grafico per": tag attivi, tag del TagManager non attivi
 * (disabilitati: Cost Explorer non li conosce) e dimensioni. */
function renderGroupSelect() {
    const sel = $('group');
    const prev = sel.value || APP.defaultGroup;
    const active = state.tags.filter(t => t.status === 'Active').map(t => t.key);
    const suggested = Object.keys(APP.suggestedTags || {});
    const inactive = state.tags.length ? suggested.filter(k => !active.includes(k)) : [];
    // senza l'elenco dei tag (non in cache) si tiene la scelta attuale
    const known = state.tags.length ? active : [prev.startsWith('TAG:') ? prev.slice(4) : ''].filter(Boolean);
    let html = '<optgroup label="Tag attivi">'
        + (known.length ? known.map(k => `<option value="TAG:${escapeHtml(k)}">${escapeHtml(k)}</option>`).join('')
            : '<option disabled>nessun tag attivo</option>')
        + '</optgroup>';
    if (inactive.length) {
        html += '<optgroup label="Tag del TagManager non attivi">'
            + inactive.map(k => `<option value="TAG:${escapeHtml(k)}" disabled>${escapeHtml(k)} (non attivo)</option>`).join('')
            + '</optgroup>';
    }
    html += '<optgroup label="Dimensioni">'
        + Object.entries(APP.secondDimensions).map(([k, v]) => `<option value="DIM:${k}">${escapeHtml(v)}</option>`).join('')
        + '</optgroup>';
    sel.innerHTML = html;
    const ok = [...sel.options].some(o => o.value === prev && !o.disabled);
    sel.value = ok ? prev : (known.length ? `TAG:${known[0]}` : 'DIM:REGION');
}

function renderTagNotes() {
    const info = groupInfo();
    if (!info.isTag) return;
    const tag = state.tags.find(t => t.key === info.key);
    if (!tag) return;
    if (tag.status !== 'Active') {
        appendAlertHtml(`Il tag <strong>${escapeHtml(info.key)}</strong> non è attivo come cost allocation tag: `
            + 'Cost Explorer lo ignora. Si attiva da Billing &rarr; Cost allocation tags.', 'warning');
        return;
    }
    const since = tag.last_updated ? tag.last_updated.slice(0, 10) : '';
    if (since && since.slice(0, 7) >= serverParams().start) {
        const d = new Date(since).toLocaleDateString('it-IT');
        appendAlertHtml(`Il tag <strong>${escapeHtml(info.key)}</strong> è attivo dal ${d}: Cost Explorer attribuisce `
            + 'ai tag solo i costi successivi all\'attivazione, quindi i mesi precedenti risultano quasi tutti '
            + '"senza tag". Per ricalcolarli si può richiedere un backfill (fino a 12 mesi) da '
            + 'Billing &rarr; Cost allocation tags &rarr; <em>Backfill tags</em>.', 'info');
    }
}

// ----------------------------------------------------------------------
// Righe dei costi
// ----------------------------------------------------------------------

/* Righe con risoluzione almeno mensile per tutto il periodo: per ogni mese la serie
 * mensile o, se manca, quella giornaliera (sommata poi per mese). */
function monthRows() {
    const mInfo = monthsMap(state.monthly), dInfo = monthsMap(state.daily);
    const use = {};
    periodMonths().forEach(m => {
        if ((mInfo[m] || {}).cached) use[m] = 'm';
        else if ((dInfo[m] || {}).cached) use[m] = 'd';
    });
    const out = [];
    ((state.monthly && state.monthly.rows) || []).forEach(r => { if (use[r.month] === 'm') out.push(r); });
    ((state.daily && state.daily.rows) || []).forEach(r => { if (use[r.month] === 'd') out.push(r); });
    return out;
}

function dailyRows() { return (state.daily && state.daily.rows) || []; }

function applyFilters(rows) {
    const svc = $('serviceFilter').value;
    const grp = $('groupFilter').value;
    return rows.filter(r =>
        (!svc || r.service === svc) && (!grp || enc(normGroup(r.group)) === grp));
}

function hasClientFilters() { return !!($('serviceFilter').value || $('groupFilter').value); }

function totalsBy(rows, keyFn) {
    const out = {};
    rows.forEach(r => { const k = keyFn(r); out[k] = (out[k] || 0) + r.amount; });
    return out;
}

/* Classifica delle voci sull'intero periodo: decide lo slot di colore, cosi' filtrando,
 * zoomando o cambiando il top N le voci non cambiano colore. */
function computeRanks() {
    const rows = monthRows();
    const rankOf = (keyFn, skip) => {
        const tot = totalsBy(rows, keyFn);
        const out = {};
        Object.keys(tot).filter(k => !skip(k)).sort((a, b) => tot[b] - tot[a]).forEach((k, i) => { out[k] = i; });
        return out;
    };
    state.rank.service = rankOf(r => r.service, () => false);
    state.rank.group = rankOf(r => normGroup(r.group), k => k === '');
}

function renderFilterSelects() {
    const rows = monthRows();

    const svcSel = $('serviceFilter');
    const prevSvc = svcSel.value;
    const svcTot = totalsBy(rows, r => r.service);
    svcSel.innerHTML = '<option value="">Tutti</option>' + Object.keys(svcTot)
        .filter(k => svcTot[k] !== 0)
        .sort((a, b) => svcTot[b] - svcTot[a])
        .map(k => `<option value="${escapeHtml(k)}">${escapeHtml(serviceLabel(k))} · ${money(svcTot[k])}</option>`)
        .join('');
    svcSel.value = svcTot[prevSvc] !== undefined ? prevSvc : '';

    // Valori del gruppo: raggruppando, solo i padri; senza raggruppare, ogni padre
    // seguito dai suoi sottovalori (come le tendine del TagManager)
    const grpSel = $('groupFilter');
    const prevGrp = grpSel.value;
    const rawTot = totalsBy(rows, r => r.group);
    const families = {};
    Object.keys(rawTot).forEach(v => {
        const fam = suggestedParent(v) || v;
        (families[fam] = families[fam] || { total: 0, members: [] });
        families[fam].total += rawTot[v];
        families[fam].members.push(v);
    });
    const opts = ['<option value="">Tutti</option>'];
    Object.keys(families).sort((a, b) => families[b].total - families[a].total).forEach(fam => {
        const f = families[fam];
        if (f.total === 0) return;
        if (rollupOn()) {
            const n = f.members.filter(m => m !== fam).length;
            opts.push(`<option value="${escapeHtml(enc(fam))}">${escapeHtml(groupLabel(fam))}`
                + `${n ? ` (+${n} sottovalori)` : ''} · ${money(f.total)}</option>`);
            return;
        }
        const members = f.members.sort((a, b) => (a === fam ? -1 : b === fam ? 1 : rawTot[b] - rawTot[a]));
        members.forEach(m => {
            const child = m !== fam;
            opts.push(`<option value="${escapeHtml(enc(m))}"${child ? ' class="child"' : ''}>`
                + `${child ? '&nbsp;&nbsp;&#8627; ' : ''}${escapeHtml(groupLabel(m))} · ${money(rawTot[m])}</option>`);
        });
    });
    grpSel.innerHTML = opts.join('');
    grpSel.value = [...grpSel.options].some(o => o.value === prevGrp) ? prevGrp : '';
}

// ----------------------------------------------------------------------
// Zoom: intervallo e raggruppamento del tempo
// ----------------------------------------------------------------------

function fullRange() {
    const p = serverParams();
    const end = minIso(lastDayOfMonth(p.end), todayIso());
    return { start: `${p.start}-01`, end: maxIso(end, `${p.start}-01`) };
}

function viewRange() { return state.zoom || fullRange(); }

function sameRange(a, b) { return !!a && !!b && a.start === b.start && a.end === b.end; }

// L'intervallo e' fatto di mesi interi (il mese in corso fino a oggi)?
function isMonthAligned(r) {
    return r.start.endsWith('-01') && (r.end === lastDayOfMonth(r.end.slice(0, 7)) || r.end === todayIso());
}

/* Raggruppamento del tempo: scelto dall'utente o automatico. In automatico il periodo
 * intero va per mesi (per giorni se e' un mese solo), uno zoom corto per giorni,
 * uno medio per settimane. */
function effectiveBucket() {
    if (state.bucket !== 'auto') return state.bucket;
    const r = viewRange();
    if (!state.zoom) return monthsBetween(r.start.slice(0, 7), r.end.slice(0, 7)).length > 1 ? 'month' : 'day';
    const days = daysBetween(r.start, r.end);
    return days <= 35 ? 'day' : days <= 120 ? 'week' : 'month';
}

function viewSpec() {
    const range = viewRange();
    const bucket = effectiveBucket();
    return { range, bucket, needDaily: bucket !== 'month' || !isMonthAligned(range) };
}

/* Colonne della vista: {key, start, end, label, current}. key e' il mese, il lunedi'
 * della settimana o il giorno; start/end sono tagliati sull'intervallo. */
function buildBuckets(range, bucket) {
    const out = [];
    const today = todayIso();
    if (bucket === 'month') {
        const mInfo = monthsMap(state.monthly), dInfo = monthsMap(state.daily);
        monthsBetween(range.start.slice(0, 7), range.end.slice(0, 7)).forEach(m => {
            const info = mInfo[m] && mInfo[m].cached ? mInfo[m] : dInfo[m];
            out.push({
                key: m, start: maxIso(`${m}-01`, range.start), end: minIso(lastDayOfMonth(m), range.end),
                label: monthLabel(m) + (info && info.cached && !info.complete ? ' *' : ''),
                current: m === currentMonth(),
            });
        });
    } else if (bucket === 'week') {
        for (let d = mondayOf(range.start); d <= range.end; d = addDays(d, 7)) {
            const s = maxIso(d, range.start), e = minIso(addDays(d, 6), range.end);
            out.push({ key: d, start: s, end: e, label: weekLabel(s, e),
                current: today >= d && today <= addDays(d, 6) });
        }
    } else {
        for (let d = range.start; d <= range.end; d = addDays(d, 1)) {
            out.push({ key: d, start: d, end: d, label: dayLabel(d), current: d === today });
        }
    }
    return out;
}

function bucketKeyFn(bucket) {
    if (bucket === 'month') return r => r.month;
    if (bucket === 'week') return r => mondayOf(r.period);
    return r => r.period;
}

// Righe dell'intervallo zoomato, alla risoluzione che serve
function viewRows(spec) {
    if (spec.needDaily) {
        return dailyRows().filter(r => r.period >= spec.range.start && r.period <= spec.range.end);
    }
    const ms = new Set(monthsBetween(spec.range.start.slice(0, 7), spec.range.end.slice(0, 7)));
    return monthRows().filter(r => ms.has(r.month));
}

function zoomTo(range) {
    if (sameRange(range, viewRange())) return;
    state.zoomStack.push(state.zoom);
    state.zoom = sameRange(range, fullRange()) ? null : range;
    state.bucket = 'auto';
    refreshView();
}

function zoomOut() {
    if (!state.zoom) return;
    state.zoom = state.zoomStack.length ? state.zoomStack.pop() : null;
    state.bucket = 'auto';
    refreshView();
}

// Doppio clic o clic sull'etichetta: si entra nel mese o nella settimana
function zoomIntoBucket(i) {
    const b = state.view && state.view.buckets[i];
    if (!b || state.view.bucket === 'day') return;
    zoomTo({ start: b.start, end: b.end });
}

// Trascinamento su piu' colonne: l'intervallo dalla prima all'ultima
function zoomIntoBuckets(i0, i1) {
    const bs = state.view && state.view.buckets;
    if (!bs) return;
    const a = Math.min(i0, i1), b = Math.max(i0, i1);
    if (a === b) { zoomIntoBucket(a); return; }
    zoomTo({ start: bs[a].start, end: bs[b].end });
}

function renderZoomBar() {
    const spec = viewSpec();
    const full = fullRange();
    // briciole: tutto il periodo > livelli precedenti > vista attuale
    const levels = [...state.zoomStack, state.zoom].filter(Boolean);
    const crumbs = [null, ...levels];
    $('zoomCrumbs').innerHTML = crumbs.map((z, i) => {
        const label = z ? rangeLabel(z) : `Tutto il periodo (${rangeLabel(full)})`;
        return i === crumbs.length - 1
            ? `<li class="breadcrumb-item active fw-semibold">${escapeHtml(label)}</li>`
            : `<li class="breadcrumb-item"><a href="#" data-level="${i}">${escapeHtml(label)}</a></li>`;
    }).join('');
    $('zoomCrumbs').querySelectorAll('a[data-level]').forEach(a => a.addEventListener('click', (ev) => {
        ev.preventDefault();
        const i = Number(a.dataset.level);
        state.zoom = crumbs[i];
        state.zoomStack = crumbs.slice(1, i);
        state.bucket = 'auto';
        refreshView();
    }));
    $('btnZoomOut').disabled = !state.zoom;

    // "Vai a": periodo intero, mesi e settimane del periodo
    const val = (r) => `${r.start}|${r.end}`;
    const cur = viewRange();
    const months = monthsBetween(full.start.slice(0, 7), full.end.slice(0, 7));
    let html = '<option value="">Tutto il periodo</option><optgroup label="Mesi">'
        + months.map(m => {
            const r = { start: `${m}-01`, end: minIso(lastDayOfMonth(m), full.end) };
            return `<option value="${val(r)}">${monthLabel(m)}</option>`;
        }).join('') + '</optgroup><optgroup label="Settimane">'
        + buildBuckets(full, 'week').map(w => `<option value="${val(w)}">${escapeHtml(w.label)}</option>`).join('')
        + '</optgroup>';
    if (state.zoom && !html.includes(`value="${val(cur)}"`)) {
        html += `<option value="${val(cur)}">${escapeHtml(rangeLabel(cur))}</option>`;
    }
    $('zoomSelect').innerHTML = html;
    $('zoomSelect').value = state.zoom ? val(cur) : '';

    document.querySelectorAll('input[name="bucket"]').forEach(r => { r.checked = r.value === spec.bucket; });
}

// ----------------------------------------------------------------------
// Aggregazione e rendering
// ----------------------------------------------------------------------

/* {voce: {total, byBucket: {colonna: importo}}} */
function aggregate(rows, keyFn, bucketFn) {
    const out = {};
    rows.forEach(r => {
        const k = keyFn(r);
        const b = bucketFn(r);
        const e = out[k] || (out[k] = { total: 0, byBucket: {} });
        e.total += r.amount;
        e.byBucket[b] = (e.byBucket[b] || 0) + r.amount;
    });
    return out;
}

/* Voci da mostrare: sopra la soglia, ordinate per totale; nel grafico le prime N
 * e il resto sommato in "Altri". */
function visibleEntries(agg) {
    const min = parseFloat($('minAmount').value) || 0;
    return Object.entries(agg)
        .filter(([, e]) => e.total !== 0 && Math.abs(e.total) >= min)
        .sort((a, b) => b[1].total - a[1].total);
}

function chartSeries(agg, kind, keys, labelFn) {
    const topN = parseInt($('topN').value, 10);
    const entries = visibleEntries(agg);
    const top = entries.slice(0, topN);
    const rest = entries.slice(topN);
    const special = kind === 'group' ? { '': COLOR_UNTAGGED } : {};
    const colors = assignColors(top.map(([k]) => k), state.rank[kind], special);
    const series = top.map(([k, e]) => ({
        key: k, label: labelFn(k), color: colors[k],
        data: keys.map(b => round4(e.byBucket[b] || 0)),
    }));
    if (rest.length) {
        series.push({
            key: OTHER_KEY, label: `Altri (${rest.length})`, color: COLOR_OTHER,
            data: keys.map(b => round4(rest.reduce((acc, [, e]) => acc + (e.byBucket[b] || 0), 0))),
        });
    }
    colors[OTHER_KEY] = COLOR_OTHER;
    return { series, colors };
}

// i grafici non hanno bisogno di piu' di 4 decimali (centesimi di centesimo)
function round4(v) { return Math.round(v * 10000) / 10000; }

function barsStacked() {
    return document.querySelector('input[name="barMode"]:checked').value === 'stacked';
}

/* Ricalcola cosa manca, aggiorna la barra dello zoom e il riquadro dei dati mancanti
 * e disegna la vista se ha tutti i dati. */
function refreshView() {
    if (!state.monthly) return;
    state.missing = computeMissing();
    renderCloudPrompt();
    renderZoomBar();
    state.ready = !state.missing.some(r => r.id !== 'tags');
    if (!state.ready) { clearView(); return; }
    render();
}

function render() {
    if (!state.ready) return;
    const info = groupInfo();
    const spec = viewSpec();
    const buckets = buildBuckets(spec.range, spec.bucket);
    const keys = buckets.map(b => b.key);
    const bfn = bucketKeyFn(spec.bucket);
    state.view = { ...spec, buckets };

    $('chartsRow').classList.remove('d-none');
    $('rollupBox').classList.toggle('d-none', !info.prefix);
    $('groupFilterLabel').textContent = info.isTag ? `Valore di ${info.key}` : info.name;
    const per = { month: 'al mese', week: 'a settimana', day: 'al giorno' }[spec.bucket];
    const where = rangeLabel(spec.range);
    $('chartServiceTitle').textContent = `Costi per servizio, ${per} · ${where}`;
    $('chartGroupTitle').textContent = `Costi per ${info.name}, ${per} · ${where}`;
    $('tableServiceTitle').textContent = `Dettaglio per servizio · ${where}`;
    $('tableGroupTitle').textContent = `Dettaglio per ${info.name} · ${where}`;
    $('kpiUntaggedLabel').textContent = info.isTag ? `Costi senza tag ${info.key}` : 'Costi senza tag';

    const rows = applyFilters(viewRows(spec));
    const aggSvc = aggregate(rows, r => r.service, bfn);
    const aggGrp = aggregate(rows, r => normGroup(r.group), bfn);
    const common = {
        labels: buckets.map(b => b.label),
        stacked: barsStacked(),
        axisPointer: true,
        // Chart.js gestisce il clic al frame successivo: si guarda quanto e' passato
        ignoreClick: () => Date.now() - state.draggedAt < 400,
    };

    const svc = chartSeries(aggSvc, 'service', keys, serviceLabel);
    state.charts.service = renderBarChart($('chartService'), state.charts.service, {
        ...common, series: svc.series, onClick: (k) => setFilter('serviceFilter', k),
    });
    const grp = chartSeries(aggGrp, 'group', keys, groupLabel);
    state.charts.group = renderBarChart($('chartGroup'), state.charts.group, {
        ...common, series: grp.series, onClick: (k) => setFilter('groupFilter', enc(k)),
    });

    renderKpis(rows, spec, buckets);
    renderTable('service', $('tableService'), aggSvc, buckets, svc.colors, serviceLabel, rows, bfn);
    renderTable('group', $('tableGroup'), aggGrp, buckets, grp.colors, groupLabel, rows, bfn);
    renderNotes();
}

// Clic su una barra o su una riga: filtra quella voce, un secondo clic toglie il filtro
function setFilter(selectId, value) {
    if (value === OTHER_KEY || value === enc(OTHER_KEY)) return;
    const sel = $(selectId);
    sel.value = sel.value === value ? '' : value;
    render();
}

// Ultime due colonne concluse (senza quella in corso), per la variazione
function lastTwo(buckets) {
    const closed = buckets.filter(b => !b.current && b.end < todayIso());
    return { last: closed[closed.length - 1], prev: closed[closed.length - 2] };
}

function deltaHtml(now, before) {
    if (before === undefined) return '';
    if (!before) return now ? '<span class="delta-bad"><i class="fas fa-arrow-up"></i> nuovo</span>' : '';
    const d = (now - before) / Math.abs(before) * 100;
    if (Math.abs(d) < 0.5) return '<span class="text-muted">= stabile</span>';
    // per i costi salire e' il verso negativo
    return d > 0
        ? `<span class="delta-bad"><i class="fas fa-arrow-up"></i> +${d.toFixed(0)}%</span>`
        : `<span class="delta-good"><i class="fas fa-arrow-down"></i> ${d.toFixed(0)}%</span>`;
}

// Importo per le celle delle tabelle: sotto il centesimo (zero compreso) in grigio chiaro,
// da 0,01 $ in su nel colore normale
function moneyCell(v) {
    const text = escapeHtml(money(v));
    return Math.abs(v) < 0.01 ? `<span class="cost-tiny">${text}</span>` : text;
}

// Percentuale: un decimale vicino agli estremi, cosi' 99,9% non diventa 100%
function pct(v) {
    const d = (v > 0 && v < 1) || (v > 99 && v < 100) ? 1 : 0;
    return `${v.toLocaleString('it-IT', { minimumFractionDigits: d, maximumFractionDigits: d })}%`;
}

/* Riepilogo. Totale e quota senza tag seguono lo zoom; mese in corso e ultimo mese
 * chiuso guardano sempre tutto il periodo. */
function renderKpis(rows, spec, buckets) {
    const total = rows.reduce((a, r) => a + r.amount, 0);
    const unit = { month: ['mese', 'mesi', 'al mese'], week: ['settimana', 'settimane', 'a settimana'],
        day: ['giorno', 'giorni', 'al giorno'] }[spec.bucket];
    $('kpiTotalLabel').textContent = state.zoom ? `Totale ${rangeLabel(spec.range)}` : 'Totale del periodo';
    $('kpiTotal').textContent = money(total);
    $('kpiTotalNote').textContent = buckets.length > 1
        ? `${buckets.length} ${unit[1]}, media ${money(total / buckets.length)} ${unit[2]}`
        : `1 ${unit[0]}`;

    const full = applyFilters(monthRows());
    const byMonth = totalsBy(full, r => r.month);
    const months = periodMonths();
    const cur = currentMonth();
    const closed = months.filter(m => m < cur);
    const last = closed[closed.length - 1], prev = closed[closed.length - 2];

    if (months.includes(cur)) {
        const mtd = byMonth[cur] || 0;
        $('kpiCurrent').textContent = money(mtd);
        const f = state.forecast;
        if (!state.forecastCached) {
            $('kpiCurrentNote').innerHTML = `<a href="#" id="linkForecast">Calcola la stima a fine mese</a> (${money(APP.apiCost)})`;
            $('linkForecast').addEventListener('click', (ev) => {
                ev.preventDefault();
                openCloudModal([forecastRequest()],
                    'La stima di fine mese viene da <code>get-cost-forecast</code> e vale per il giorno in cui è calcolata:');
            });
        } else if (f && !hasClientFilters()) {
            // l'intervallo di AWS puo' scendere sotto zero: il costo del resto del mese no
            const lo = f.lower !== null ? money(mtd + Math.max(0, f.lower)) : null;
            const hi = f.upper !== null ? money(mtd + f.upper) : null;
            $('kpiCurrentNote').innerHTML = `Stima a fine mese <strong>${money(mtd + f.amount)}</strong>`
                + (lo && hi ? ` <span title="Intervallo di previsione all'80%">(${lo} – ${hi})</span>` : '');
        } else {
            $('kpiCurrentNote').textContent = f ? 'Stima a fine mese solo senza filtri su servizio e valore'
                : 'Stima a fine mese non disponibile';
        }
    } else {
        $('kpiCurrent').textContent = '–';
        $('kpiCurrentNote').textContent = 'Il periodo non comprende il mese in corso';
    }

    if (last) {
        $('kpiLastLabel').textContent = `Ultimo mese chiuso (${monthLabel(last)})`;
        $('kpiLast').textContent = money(byMonth[last] || 0);
        $('kpiLastNote').innerHTML = prev
            ? `${deltaHtml(byMonth[last] || 0, byMonth[prev] || 0)} rispetto a ${monthLabel(prev)} (${money(byMonth[prev] || 0)})`
            : '';
    } else {
        // periodo col solo mese in corso: media al giorno e proiezione lineare
        const r = fullRange();
        const days = daysBetween(r.start, r.end);
        const tot = full.reduce((a, x) => a + x.amount, 0);
        const today = new Date();
        const monthDays = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
        $('kpiLastLabel').textContent = 'Media al giorno';
        $('kpiLast').textContent = money(tot / days);
        $('kpiLastNote').textContent = months.includes(cur)
            ? `su ${days} giorni, proiezione lineare a fine mese ${money((byMonth[cur] || 0) / today.getDate() * monthDays)}`
            : `su ${days} giorni`;
    }

    const info = groupInfo();
    if (info.isTag && total) {
        const untagged = rows.filter(r => r.group === '').reduce((a, r) => a + r.amount, 0);
        $('kpiUntagged').textContent = pct(untagged / total * 100);
        $('kpiUntaggedNote').textContent = `${money(untagged)} in ${rangeLabel(spec.range)}`;
    } else {
        $('kpiUntagged').textContent = '–';
        $('kpiUntaggedNote').textContent = info.isTag ? '' : 'Il secondo grafico non è per tag';
    }
}

/* Tabella voce x colonna (mesi, settimane o giorni dello zoom) con totale, quota e
 * variazione tra le ultime due colonne concluse. Per il gruppo, raggruppando i
 * sottovalori, sotto ogni padre sono elencati i figli: chiusi, si aprono e chiudono con
 * la freccia. La lente in fondo alla riga filtra la voce (un secondo clic toglie il
 * filtro); per i servizi c'e' anche il dettaglio per usage type. */
function renderTable(kind, table, agg, buckets, colors, labelFn, rows, bfn) {
    const entries = visibleEntries(agg);
    const grand = entries.reduce((a, [, e]) => a + e.total, 0);
    const keys = buckets.map(b => b.key);
    const { last, prev } = lastTwo(buckets);
    const withDelta = !!(last && prev);
    const active = kind === 'service' ? $('serviceFilter').value : dec($('groupFilter').value);
    const children = (kind === 'group' && rollupOn())
        ? aggregate(rows.filter(r => r.group !== normGroup(r.group)), r => r.group, bfn) : {};

    const childrenOf = (k) => Object.entries(children).filter(([c]) => suggestedParent(c) === k)
        .sort((a, b) => b[1].total - a[1].total);
    const anyChildren = entries.some(([k]) => childrenOf(k).length);

    const head = ['Voce', ...buckets.map(b => b.label), 'Totale', 'Quota',
        ...(withDelta ? [`${last.label} vs ${prev.label}`] : [])];
    let html = '<thead class="table-light"><tr>'
        + head.map((h, i) => `<th class="${i ? 'num' : ''}">${escapeHtml(h)}</th>`).join('')
        + '<th></th></tr></thead><tbody>';
    const csv = [['Voce', ...keys, 'Totale', 'Quota %']];

    entries.forEach(([k, e]) => {
        const color = colors[k] || COLOR_OTHER;
        const share = grand ? e.total / grand * 100 : 0;
        const isActive = active !== '' && active === k;
        const kids = childrenOf(k);
        const open = state.expanded.has(k);
        const toggle = kids.length
            ? `<button class="btn btn-link btn-sm p-0 me-1 btn-toggle" data-key="${escapeHtml(k)}" title="${open ? 'Chiudi' : 'Apri'} i ${kids.length} sottovalori">`
                + `<i class="fas fa-fw ${open ? 'fa-chevron-down' : 'fa-chevron-right'}"></i></button>`
            : (anyChildren ? '<span class="toggle-spacer"></span>' : '');
        html += `<tr${isActive ? ' class="active-filter"' : ''} data-key="${escapeHtml(k)}">`
            + `<td class="entity" title="${escapeHtml(k)}">${toggle}<span class="swatch" style="background:${color}"></span>${escapeHtml(labelFn(k))}</td>`
            + keys.map(b => `<td class="num">${e.byBucket[b] !== undefined ? moneyCell(e.byBucket[b]) : ''}</td>`).join('')
            + `<td class="num fw-semibold">${moneyCell(e.total)}</td>`
            + `<td class="num"><span class="share-bar" style="width:${Math.max(0, Math.min(60, share * 0.6))}px"></span>${share.toFixed(1)}%</td>`
            + (withDelta ? `<td class="num">${deltaHtml(e.byBucket[last.key] || 0, e.byBucket[prev.key] || 0)}</td>` : '')
            + '<td class="row-actions">'
            + `<button class="btn btn-sm btn-link py-0 btn-filter" data-key="${escapeHtml(k)}" `
            + `title="${isActive ? 'Togli il filtro' : 'Filtra grafici e tabelle su questa voce'}">`
            + `<i class="fas ${isActive ? 'fa-magnifying-glass-minus' : 'fa-magnifying-glass'}"></i></button>`
            + (kind === 'service'
                ? `<button class="btn btn-sm btn-link py-0 btn-drill" data-service="${escapeHtml(k)}" title="Dettaglio per usage type"><i class="fas fa-magnifying-glass-chart"></i></button>`
                : '')
            + '</td></tr>';
        csv.push([labelFn(k), ...keys.map(b => (e.byBucket[b] || 0).toFixed(4)), e.total.toFixed(4), share.toFixed(2)]);

        kids.forEach(([c, ce]) => {
            html += `<tr class="child-row${open ? '' : ' d-none'}" data-parent="${escapeHtml(k)}">`
                + `<td class="entity" title="${escapeHtml(c)}">&#8627; ${escapeHtml(c)}</td>`
                + keys.map(b => `<td class="num">${ce.byBucket[b] !== undefined ? moneyCell(ce.byBucket[b]) : ''}</td>`).join('')
                + `<td class="num">${moneyCell(ce.total)}</td><td></td>${withDelta ? '<td></td>' : ''}<td></td></tr>`;
            csv.push([`  ${c}`, ...keys.map(b => (ce.byBucket[b] || 0).toFixed(4)), ce.total.toFixed(4), '']);
        });
    });

    if (!entries.length) {
        html += `<tr><td colspan="${head.length + 1}" class="text-center text-muted py-4">Nessun costo con i filtri attuali</td></tr>`;
    }
    const colTot = keys.map(b => entries.reduce((a, [, e]) => a + (e.byBucket[b] || 0), 0));
    html += '</tbody><tfoot><tr><td>Totale</td>'
        + colTot.map(v => `<td class="num">${moneyCell(v)}</td>`).join('')
        + `<td class="num">${moneyCell(grand)}</td><td></td>`
        + (withDelta ? `<td class="num">${deltaHtml(colTot[keys.indexOf(last.key)], colTot[keys.indexOf(prev.key)])}</td>` : '')
        + '<td></td></tr></tfoot>';
    csv.push(['Totale', ...colTot.map(v => v.toFixed(4)), grand.toFixed(4), '100']);

    table.innerHTML = html;
    state.tables[kind] = csv;

    table.querySelectorAll('.btn-filter').forEach(b => b.addEventListener('click', () => {
        if (kind === 'service') setFilter('serviceFilter', b.dataset.key);
        else setFilter('groupFilter', enc(b.dataset.key));
    }));
    table.querySelectorAll('.btn-drill').forEach(b => b.addEventListener('click', () => openDrill(b.dataset.service)));
    // apre e chiude i sottovalori senza ridisegnare (la scelta resta nei render successivi)
    table.querySelectorAll('.btn-toggle').forEach(b => b.addEventListener('click', () => {
        const k = b.dataset.key;
        const open = !state.expanded.has(k);
        if (open) state.expanded.add(k); else state.expanded.delete(k);
        table.querySelectorAll('tr.child-row').forEach(tr => {
            if (tr.dataset.parent === k) tr.classList.toggle('d-none', !open);
        });
        b.querySelector('i').className = `fas fa-fw ${open ? 'fa-chevron-down' : 'fa-chevron-right'}`;
        b.title = `${open ? 'Chiudi' : 'Apri'} i sottovalori`;
    }));
}

function renderNotes() {
    const p = serverParams();
    const fmt = (ts) => new Date(ts * 1000).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    // mesi mostrati nella vista e loro fonte (la serie giornaliera se la vista la usa)
    const spec = viewSpec();
    const shown = monthsBetween(spec.range.start.slice(0, 7), spec.range.end.slice(0, 7));
    const mInfo = monthsMap(state.monthly), dInfo = monthsMap(state.daily);
    const infoOf = (m) => (spec.needDaily || !(mInfo[m] || {}).cached) ? dInfo[m] : mInfo[m];
    const fromCur = shown.filter(m => (infoOf(m) || {}).source === 'cur');
    const fromApi = shown.filter(m => (infoOf(m) || {}).source === 'api');
    const parts = [];
    if (fromCur.length) {
        const last = Math.max(...fromCur.map(m => infoOf(m).loaded_at));
        parts.push(`<i class="fas fa-file-invoice-dollar me-1"></i>Data Export: ${monthsText(fromCur)} `
            + `(file del ${fmt(last)}, si aggiorna da solo)`);
    }
    if (fromApi.length) {
        const inc = fromApi.filter(m => !infoOf(m).complete);
        parts.push(`<i class="fas fa-database me-1"></i>cache API Cost Explorer: ${monthsText(fromApi)}`
            + (inc.length ? ` &ndash; * letti prima della fine del mese: ${inc.map(m => `${monthLabel(m)} (${fmt(infoOf(m).loaded_at)})`).join(', ')}, `
                + 'restano così finché non li aggiorni con <i class="fas fa-rotate"></i>' : ''));
    }
    parts.push(`metrica ${escapeHtml(p.metric)}` + (p.region ? `, region ${escapeHtml(p.region)}` : '')
        + (p.exclude === '1' ? ', senza tasse, crediti e rimborsi' : ''));
    $('estimatedNote').innerHTML = parts.join(' &middot; ');
}

// Badge nella barra in alto: stato del Data Export su S3
async function loadCurStatus() {
    const el = $('curStatus');
    try {
        const st = await ceGet(`/api/ce/cur/status?profile=${encodeURIComponent(APP.profile)}`);
        if (!st.enabled) { el.classList.add('d-none'); return; }
        const where = `s3://${st.bucket}/${st.prefix}${st.export ? ` (export ${st.export})` : ''}`;
        let cls = 'text-bg-success', text, title;
        if (st.error) {
            cls = 'text-bg-danger'; text = 'Data Export: errore'; title = `${where}\n${st.error}`;
        } else if (!st.months.length) {
            cls = 'text-bg-secondary'; text = 'Data Export: in attesa dei file';
            title = `${where}\nNessun file ancora: AWS scrive il primo entro circa 24 ore dalla creazione dell'export. `
                + 'Nel frattempo si usano i dati letti con l\'API.';
        } else {
            const last = Math.max(...st.months.map(m => m.last_modified));
            text = `Data Export: ${st.months.length === 1 ? monthLabel(st.months[0].month) : `${st.months.length} mesi`}`;
            title = `${where}\nMesi: ${monthsText(st.months.map(m => m.month))}\nUltimo file: `
                + new Date(last * 1000).toLocaleString('it-IT');
            const unknown = [...new Set(st.months.flatMap(m => m.unknown_products || []))];
            if (unknown.length) title += `\nServizi senza nome noto: ${unknown.join(', ')} (vedi cur_service_names in config.json)`;
        }
        el.className = `badge ${cls} me-3`;
        el.textContent = text;
        el.title = title;
    } catch (e) {
        el.classList.add('d-none');
    }
}

// Svuota grafici, tabelle e riepilogo quando alla vista mancano dei dati
function clearView() {
    Object.values(state.charts).forEach(c => c && c.destroy());
    state.charts = {};
    state.view = null;
    $('chartsRow').classList.add('d-none');
    ['tableService', 'tableGroup'].forEach(id => {
        $(id).innerHTML = '<tbody><tr><td class="text-center text-muted py-4">Dati non in cache: '
            + 'usa <strong>Carica i dati dal cloud</strong></td></tr></tbody>';
    });
    $('kpiLastLabel').textContent = 'Ultimo mese chiuso';
    $('kpiTotalLabel').textContent = 'Totale del periodo';
    ['kpiTotal', 'kpiCurrent', 'kpiLast', 'kpiUntagged'].forEach(id => { $(id).textContent = '–'; });
    ['kpiTotalNote', 'kpiCurrentNote', 'kpiLastNote', 'kpiUntaggedNote'].forEach(id => { $(id).textContent = ''; });
    $('estimatedNote').innerHTML = '';
}

// ----------------------------------------------------------------------
// Zoom col mouse sui grafici
// ----------------------------------------------------------------------

/* Trascinando sul grafico si disegna una banda e, al rilascio, si zooma sulle colonne
 * coperte; il doppio clic su una colonna entra nel suo mese o nella sua settimana. */
function setupChartZoom(canvasId, chartKey) {
    const canvas = $(canvasId);
    const box = canvas.parentElement;
    const band = document.createElement('div');
    band.className = 'zoom-select';
    box.appendChild(band);
    let startX = null, moved = false;

    const localX = (ev) => ev.clientX - canvas.getBoundingClientRect().left;
    canvas.addEventListener('mousedown', (ev) => {
        const chart = state.charts[chartKey];
        if (!chart || ev.button !== 0) return;
        const x = localX(ev);
        const a = chart.chartArea;
        if (x < a.left || x > a.right) return;
        startX = x;
        moved = false;
    });
    window.addEventListener('mousemove', (ev) => {
        const chart = state.charts[chartKey];
        if (startX === null || !chart) return;
        const a = chart.chartArea;
        const x = Math.max(a.left, Math.min(a.right, localX(ev)));
        if (Math.abs(x - startX) < 6 && !moved) return;
        moved = true;
        band.style.display = 'block';
        band.style.left = `${canvas.offsetLeft + Math.min(x, startX)}px`;
        band.style.width = `${Math.abs(x - startX)}px`;
        band.style.top = `${canvas.offsetTop + a.top}px`;
        band.style.height = `${a.bottom - a.top}px`;
    });
    window.addEventListener('mouseup', (ev) => {
        if (startX === null) return;
        const chart = state.charts[chartKey];
        band.style.display = 'none';
        if (moved && chart) {
            const a = chart.chartArea;
            const x = Math.max(a.left, Math.min(a.right, localX(ev)));
            const i0 = bucketIndexAt(chart, startX), i1 = bucketIndexAt(chart, x);
            // il clic che segue il rilascio non deve filtrare la voce sotto il mouse
            state.draggedAt = Date.now();
            zoomIntoBuckets(i0, i1);
        }
        startX = null;
        moved = false;
    });
    canvas.addEventListener('dblclick', (ev) => {
        const chart = state.charts[chartKey];
        if (chart) zoomIntoBucket(bucketIndexAt(chart, localX(ev)));
    });
    // clic sulle etichette dell'asse x (sotto l'area del grafico): Chart.js non sempre
    // li passa a onClick, quindi si ascoltano direttamente
    canvas.addEventListener('click', (ev) => {
        const chart = state.charts[chartKey];
        if (!chart || Date.now() - state.draggedAt < 400) return;
        const y = ev.clientY - canvas.getBoundingClientRect().top;
        const a = chart.chartArea;
        if (y > a.bottom && y < chart.scales.x.bottom) zoomIntoBucket(bucketIndexAt(chart, localX(ev)));
    });
}

// ----------------------------------------------------------------------
// Dettaglio di un servizio (usage type)
// ----------------------------------------------------------------------

function openDrill(service) {
    state.drill.service = service;
    $('drillTitle').textContent = serviceLabel(service);
    const months = periodMonths();
    $('drillMonth').innerHTML = months.slice().reverse()
        .map(m => `<option value="${m}">${monthLabel(m)}</option>`).join('');
    // parte dalla vista della pagina: per giorni o settimane -> giornaliero del mese zoomato
    const spec = viewSpec();
    $('drillGranularity').value = spec.bucket === 'month' ? 'MONTHLY' : 'DAILY';
    if (spec.bucket !== 'month') $('drillMonth').value = spec.range.end.slice(0, 7);
    bootstrap.Modal.getOrCreateInstance($('drillModal')).show();
    loadDrill();
}

/* Dettaglio: prima dalla cache; se manca, un avviso col costo e il pulsante per
 * leggerlo da AWS (fromCloud = true dopo il clic). */
async function loadDrill(fromCloud = false) {
    const p = serverParams();
    const qs = new URLSearchParams({
        profile: p.profile, start: p.start, end: p.end, metric: p.metric,
        region: p.region, exclude: p.exclude,
        service: state.drill.service,
        dimension: $('drillDimension').value,
        granularity: $('drillGranularity').value,
        month: $('drillMonth').value,
    });
    // stesso filtro sul valore del gruppo della pagina: raggruppando, il padre
    // porta con se' tutti i suoi sottovalori
    const grp = $('groupFilter').value;
    if (grp) {
        qs.append('group', p.group);
        const want = dec(grp);
        const raw = [...new Set(monthRows().map(r => r.group))].filter(v => normGroup(v) === want);
        (raw.length ? raw : [want]).forEach(v => qs.append('group_value', v));
    }
    $('drillMonthBox').classList.toggle('d-none', $('drillGranularity').value !== 'DAILY');
    $('drillInfo').textContent = grp ? `Solo ${groupInfo().name} = ${groupLabel(dec(grp))}` : '';
    $('tableDrill').innerHTML = '<tbody><tr><td class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm"></div></td></tr></tbody>';
    if (!fromCloud) qs.append('cache_only', '1');
    const seq = ++state.drill.seq;
    try {
        const before = state.apiCalls;
        const d = await ceGet(`/api/ce/drilldown?${qs.toString()}`);
        if (seq !== state.drill.seq) return;
        const missing = d.missing_months || [];
        $('drillCloud').classList.toggle('d-none', !missing.length);
        $('drillCloud').classList.toggle('d-flex', !!missing.length);
        $('drillContent').classList.toggle('d-none', !!missing.length);
        if (missing.length) {
            state.drill.data = null;
            const calls = monthRuns(missing).length;
            const daily = $('drillGranularity').value === 'DAILY';
            $('drillCloudText').innerHTML = `Il dettaglio per <strong>${escapeHtml($('drillDimension').selectedOptions[0].text.toLowerCase())}</strong>`
                + ` ${daily ? 'al giorno' : 'al mese'} non è in cache per: ${escapeHtml(monthsText(missing))}.<br>`
                + `<strong>Attenzione: costa ${money(calls * APP.apiCost)}</strong> `
                + `(${calls} ${calls === 1 ? 'richiesta' : 'richieste'} a Cost Explorer; di più se AWS divide la risposta in pagine), `
                + 'poi resta in cache senza scadenza.';
            return;
        }
        state.drill.data = d;
        renderDrill();
        if (fromCloud) {
            const done = state.apiCalls - before;
            $('drillInfo').textContent += `${$('drillInfo').textContent ? ' · ' : ''}letto da AWS: ${done} richieste, ${money(done * APP.apiCost)}`;
        }
    } catch (e) {
        $('tableDrill').innerHTML = `<tbody><tr><td class="text-danger py-3">Errore: ${escapeHtml(e.message)}</td></tr></tbody>`;
    }
}

function renderDrill() {
    const d = state.drill.data;
    const daily = d.granularity === 'DAILY';
    const periods = d.periods;
    const agg = {};
    d.rows.forEach(r => {
        const e = agg[r.key] || (agg[r.key] = { total: 0, byPeriod: {} });
        e.total += r.amount;
        e.byPeriod[r.period] = (e.byPeriod[r.period] || 0) + r.amount;
    });
    const entries = Object.entries(agg).filter(([, e]) => e.total !== 0).sort((a, b) => b[1].total - a[1].total);
    const rank = {};
    entries.forEach(([k], i) => { rank[k] = i; });
    const top = entries.slice(0, 8);
    const rest = entries.slice(8);
    const colors = assignColors(top.map(([k]) => k), rank);
    const series = top.map(([k, e]) => ({ key: k, label: k, color: colors[k], data: periods.map(p => round4(e.byPeriod[p] || 0)) }));
    if (rest.length) {
        series.push({ key: OTHER_KEY, label: `Altri (${rest.length})`, color: COLOR_OTHER,
            data: periods.map(p => round4(rest.reduce((a, [, e]) => a + (e.byPeriod[p] || 0), 0))) });
    }
    const labels = periods.map(p => daily ? dayLabel(p) : monthLabel(p.slice(0, 7)));
    state.drill.chart = renderBarChart($('chartDrill'), state.drill.chart, { labels, series, stacked: barsStacked() });

    // tabella: per il giornaliero solo i totali, i giorni sarebbero troppe colonne
    const cols = daily ? [] : periods;
    const grand = entries.reduce((a, [, e]) => a + e.total, 0);
    let html = '<thead class="table-light"><tr><th>' + escapeHtml($('drillDimension').selectedOptions[0].text) + '</th>'
        + cols.map(p => `<th class="num">${monthLabel(p.slice(0, 7))}</th>`).join('')
        + '<th class="num">Totale</th><th class="num">Quota</th></tr></thead><tbody>';
    const csv = [[d.dimension, ...cols, 'Totale', 'Quota %']];
    entries.forEach(([k, e]) => {
        const share = grand ? e.total / grand * 100 : 0;
        html += `<tr><td class="entity" title="${escapeHtml(k)}"><span class="swatch" style="background:${colors[k] || COLOR_OTHER}"></span>${escapeHtml(k)}</td>`
            + cols.map(p => `<td class="num">${e.byPeriod[p] !== undefined ? moneyCell(e.byPeriod[p]) : ''}</td>`).join('')
            + `<td class="num fw-semibold">${moneyCell(e.total)}</td><td class="num">${share.toFixed(1)}%</td></tr>`;
        csv.push([k, ...cols.map(p => (e.byPeriod[p] || 0).toFixed(4)), e.total.toFixed(4), share.toFixed(2)]);
    });
    if (!entries.length) html += `<tr><td colspan="${cols.length + 3}" class="text-center text-muted py-4">Nessun costo</td></tr>`;
    html += `</tbody><tfoot><tr><td>Totale</td>${cols.map(p => `<td class="num">${moneyCell(entries.reduce((a, [, e]) => a + (e.byPeriod[p] || 0), 0))}</td>`).join('')}`
        + `<td class="num">${moneyCell(grand)}</td><td></td></tr></tfoot>`;
    $('tableDrill').innerHTML = html;
    state.tables.drill = csv;

    // il comando CLI equivalente, per rifare la stessa interrogazione da terminale
    $('drillCommand').textContent = d.period
        ? `aws ce get-cost-and-usage --time-period Start=${d.period.Start},End=${d.period.End} `
            + `--granularity ${d.granularity} --metrics ${d.metric} --group-by Type=DIMENSION,Key=${d.dimension}`
            + (d.filter ? ` --filter '${JSON.stringify(d.filter)}'` : '')
        : '';
}

// ----------------------------------------------------------------------
// CSV
// ----------------------------------------------------------------------

function downloadCsv(kind) {
    const rows = state.tables[kind];
    if (!rows) return;
    const text = rows.map(r => r.map(c => {
        const s = String(c);
        return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(';')).join('\n');
    const blob = new Blob(['﻿' + text], { type: 'text/csv;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    const r = state.view ? state.view.range : fullRange();
    a.download = `costi_${kind}_${r.start}_${r.end}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
}

// ----------------------------------------------------------------------
// Avvio
// ----------------------------------------------------------------------

function setPreset(n) {
    const r = lastMonths(n);
    $('startMonth').value = r.start;
    $('endMonth').value = r.end;
    document.querySelectorAll('#presets button').forEach(b =>
        b.classList.toggle('active', Number(b.dataset.months) === n));
}

document.addEventListener('DOMContentLoaded', () => {
    setPreset(APP.defaultMonths);
    $('endMonth').max = currentMonth();
    $('startMonth').max = currentMonth();

    // Ogni cambio di parametri legge solo la cache (gratis): AWS si chiama dalla modale
    document.querySelectorAll('#presets button').forEach(b => b.addEventListener('click', () => {
        setPreset(Number(b.dataset.months));
        loadFromCache();
    }));
    ['startMonth', 'endMonth'].forEach(id => $(id).addEventListener('change', () => {
        document.querySelectorAll('#presets button').forEach(b => b.classList.remove('active'));
        loadFromCache();
    }));
    ['metric', 'group', 'region', 'exclude'].forEach(id => $(id).addEventListener('change', () => loadFromCache()));

    const missingIntro = 'Questi dati non sono nella cache locale e vanno letti da AWS Cost Explorer '
        + '(i mesi già in cache non vengono riletti):';
    $('btnCloud').addEventListener('click', () => openCloudModal(state.missing, missingIntro));
    $('btnCloudPrompt').addEventListener('click', () => openCloudModal(state.missing, missingIntro));
    $('btnRefresh').addEventListener('click', () => {
        const items = incompleteRequests();
        openCloudModal(items, items.some(r => r.id !== 'tags')
            ? 'Aggiorna i mesi letti <strong>prima della loro fine</strong>; i mesi completi restano quelli in cache.'
            : 'Tutti i mesi del periodo sono completi: non c\'è niente da aggiornare. Puoi solo rileggere l\'elenco dei tag.');
    });
    $('btnCloudConfirm').addEventListener('click', loadFromCloud);

    ['serviceFilter', 'groupFilter', 'topN', 'minAmount'].forEach(id => $(id).addEventListener('change', render));
    $('minAmount').addEventListener('input', render);
    document.querySelectorAll('input[name="barMode"]').forEach(r => r.addEventListener('change', () => {
        render();
        if (state.drill.data) renderDrill();
    }));
    $('rollup').addEventListener('change', () => {
        $('groupFilter').value = '';
        computeRanks();
        renderFilterSelects();
        render();
    });
    $('btnReset').addEventListener('click', () => {
        $('serviceFilter').value = '';
        $('groupFilter').value = '';
        $('minAmount').value = '0';
        $('topN').value = '8';
        render();
    });

    // zoom
    $('btnZoomOut').addEventListener('click', zoomOut);
    $('zoomSelect').addEventListener('change', () => {
        const v = $('zoomSelect').value;
        if (!v) { zoomTo(fullRange()); return; }
        const [start, end] = v.split('|');
        zoomTo({ start, end });
    });
    document.querySelectorAll('input[name="bucket"]').forEach(r => r.addEventListener('change', () => {
        state.bucket = r.value;
        refreshView();
    }));
    setupChartZoom('chartService', 'service');
    setupChartZoom('chartGroup', 'group');

    ['drillDimension', 'drillGranularity', 'drillMonth'].forEach(id => $(id).addEventListener('change', () => loadDrill(false)));
    $('btnDrillCloud').addEventListener('click', () => loadDrill(true));
    document.querySelectorAll('[data-csv]').forEach(b => b.addEventListener('click', () => downloadCsv(b.dataset.csv)));

    // all'apertura solo la cache (e il Data Export): se manca qualcosa compare "Carica i dati dal cloud"
    loadFromCache();
    loadCurStatus();
});

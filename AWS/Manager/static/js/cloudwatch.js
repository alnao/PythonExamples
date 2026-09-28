/* CloudWatch: allarmi e log (ex AWS/Managers/ManagerFlaskCloudWatch).
 *
 * Con la region "Tutte" gli elenchi comprendono tutte le region della lista e ogni
 * elemento porta la sua (_region), usata poi per dettagli e operazioni.
 * Ogni operazione che modifica AWS chiede conferma.
 */

const CW = '/api/cloudwatch';
const state = {
    alarms: [],
    groups: [],
    group: null,        // {name, region} del log group aperto
    alarm: null,        // allarme della modale "forza stato"
    stream: null,       // stream della modale "scrivi evento"
    logsLoaded: false,
};

const multiRegion = () => APP.region === ALL;

function stateBadge(s) {
    const cls = { OK: 'success', ALARM: 'danger', INSUFFICIENT_DATA: 'warning' }[s] || 'secondary';
    return `<span class="badge text-bg-${cls}">${escapeHtml(s)}</span>`;
}

function warn(warnings) {
    if ((warnings || []).length) appendAlertHtml(warnings.map(escapeHtml).join('<br>'), 'warning');
}

/* Esegue un'azione dopo la conferma: POST, messaggio, poi after(). */
async function runAction(confirmOpts, url, body, after) {
    if (!await confirmAction(confirmOpts)) return;
    spinner(true);
    try {
        const data = await apiPost(url, body);
        showAlert(data.message || 'Operazione eseguita', 'success');
        if (after) await after();
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger');
    } finally {
        spinner(false);
    }
}

// ---------------------------------------------------------------- allarmi

async function loadAlarms() {
    $('alarmsTable').innerHTML = loadingHtml();
    try {
        const d = await apiGet(`${CW}/alarms?${query({ region: APP.region, state: $('stateFilter').value })}`);
        state.alarms = d.alarms;
        warn(d.warnings);
        renderAlarms();
    } catch (e) {
        $('alarmsTable').innerHTML = `<div class="alert alert-danger m-2">${escapeHtml(e.message)}</div>`;
    }
}

function renderAlarms() {
    const q = $('alarmSearch').value.trim().toLowerCase();
    const rows = state.alarms.filter(a => !q || `${a.AlarmName} ${a.MetricName} ${a.Namespace}`.toLowerCase().includes(q));
    $('alarmsCount').textContent = rows.length;
    $('alarmsTable').innerHTML = rowsTable(rows, [
        ...(multiRegion() ? [{ title: 'Region', get: a => regionBadge(a._region) }] : []),
        { title: 'Nome', get: a => `<strong>${escapeHtml(a.AlarmName)}</strong>`
            + (a.AlarmDescription ? `<div class="text-muted">${escapeHtml(a.AlarmDescription)}</div>` : '') },
        { title: 'Stato', get: a => stateBadge(a.StateValue) },
        { title: 'Metrica', get: a => escapeHtml(`${a.Namespace || ''} ${a.MetricName || ''}`) },
        { title: 'Soglia', cls: 'num', get: a => escapeHtml(`${a.ComparisonOperator ? a.ComparisonOperator.replace('Threshold', '') : ''} ${a.Threshold ?? ''}`) },
        { title: 'Azioni', get: a => a.ActionsEnabled ? '<span class="badge text-bg-success">attive</span>' : '<span class="badge text-bg-secondary">disattive</span>' },
        { title: 'Aggiornato', get: a => escapeHtml(fmtDate(a.StateUpdatedTimestamp)) },
        { title: '', cls: 'text-end text-nowrap', get: a => {
            const i = state.alarms.indexOf(a);
            return `<div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary" data-act="history" data-i="${i}" title="Storico"><i class="fas fa-clock-rotate-left"></i></button>
                <button class="btn btn-outline-warning" data-act="state" data-i="${i}" title="Forza stato"><i class="fas fa-triangle-exclamation"></i></button>
                <button class="btn btn-outline-secondary" data-act="actions" data-i="${i}" title="${a.ActionsEnabled ? 'Disattiva' : 'Attiva'} le azioni">
                    <i class="fas ${a.ActionsEnabled ? 'fa-bell-slash' : 'fa-bell'}"></i></button>
                <button class="btn btn-outline-danger" data-act="delete" data-i="${i}" title="Cancella"><i class="fas fa-trash"></i></button>
            </div>`;
        } },
    ], 'Nessun allarme');
    $('alarmsTable').querySelectorAll('button[data-act]').forEach(b =>
        b.addEventListener('click', () => alarmAction(b.dataset.act, state.alarms[Number(b.dataset.i)])));
}

async function alarmAction(act, a) {
    const region = a._region;
    const name = `<strong>${escapeHtml(a.AlarmName)}</strong>`;
    if (act === 'history') return showHistory(a);
    if (act === 'state') {
        state.alarm = a;
        $('stateTitle').textContent = a.AlarmName;
        bootstrap.Modal.getOrCreateInstance($('stateModal')).show();
        return;
    }
    if (act === 'actions') {
        const enable = !a.ActionsEnabled;
        return runAction({
            title: enable ? 'Attivare le azioni?' : 'Disattivare le azioni?',
            html: `Le azioni dell'allarme ${name} (notifiche, scaling...) vengono ${enable ? 'attivate' : 'disattivate'}.` + contextHtml(region),
            confirmText: enable ? 'Attiva' : 'Disattiva',
        }, `${CW}/alarms/actions`, { region, name: a.AlarmName, enabled: enable }, loadAlarms);
    }
    if (act === 'delete') {
        return runAction({
            title: 'Cancellare l\'allarme?', danger: true, confirmText: 'Cancella',
            html: `L'allarme ${name} viene cancellato definitivamente.` + contextHtml(region),
        }, `${CW}/alarms/delete`, { region, name: a.AlarmName }, loadAlarms);
    }
}

async function showHistory(a) {
    $('historyTitle').textContent = a.AlarmName;
    $('historyBody').innerHTML = loadingHtml();
    bootstrap.Modal.getOrCreateInstance($('historyModal')).show();
    try {
        const d = await apiGet(`${CW}/alarms/history?${query({ region: a._region, name: a.AlarmName })}`);
        $('historyBody').innerHTML = rowsTable(d.history, [
            { title: 'Data', get: h => escapeHtml(fmtDate(h.Timestamp)) },
            { title: 'Tipo', get: h => escapeHtml(h.HistoryItemType) },
            { title: 'Da', get: h => h.OldState ? stateBadge(h.OldState) : '' },
            { title: 'A', get: h => h.NewState ? stateBadge(h.NewState) : '' },
            { title: 'Descrizione', get: h => escapeHtml(h.HistorySummary) },
        ], 'Nessun evento nello storico');
    } catch (e) {
        $('historyBody').innerHTML = `<div class="alert alert-danger">${escapeHtml(e.message)}</div>`;
    }
}

async function setAlarmState() {
    const a = state.alarm;
    const newState = $('newState').value;
    bootstrap.Modal.getOrCreateInstance($('stateModal')).hide();
    await runAction({
        title: 'Forzare lo stato?', confirmText: 'Forza stato',
        html: `L'allarme <strong>${escapeHtml(a.AlarmName)}</strong> passa in ${stateBadge(newState)}.` + contextHtml(a._region),
    }, `${CW}/alarms/state`, { region: a._region, name: a.AlarmName, state: newState, reason: $('stateReason').value }, loadAlarms);
}

async function createAlarm() {
    if (multiRegion()) { showAlert('Per creare un allarme scegli una region al posto di "Tutte"', 'warning'); return; }
    const body = {
        region: APP.region, alarm_name: $('alarmName').value.trim(), asg_name: $('asgName').value.trim(),
        threshold: $('threshold').value, evaluation_periods: $('evaluationPeriods').value, period: $('period').value,
    };
    if (!body.alarm_name || !body.asg_name) { showAlert('Nome allarme e Auto Scaling Group sono obbligatori', 'warning'); return; }
    await runAction({
        title: 'Creare l\'allarme?', confirmText: 'Crea',
        html: `Nuovo allarme <strong>${escapeHtml(body.alarm_name)}</strong>: CPU media dell'ASG
            <strong>${escapeHtml(body.asg_name)}</strong> sopra ${escapeHtml(body.threshold)}% per
            ${escapeHtml(body.evaluation_periods)} periodi da ${escapeHtml(body.period)} secondi.` + contextHtml(),
    }, `${CW}/alarms/create`, body, loadAlarms);
}

// ---------------------------------------------------------------- log group

async function loadGroups() {
    state.logsLoaded = true;
    $('groupsTable').innerHTML = loadingHtml();
    try {
        const d = await apiGet(`${CW}/logs/groups?${query({ region: APP.region, prefix: $('groupPrefix').value.trim() })}`);
        state.groups = d.groups;
        warn(d.warnings);
        renderGroups();
    } catch (e) {
        $('groupsTable').innerHTML = `<div class="alert alert-danger m-2">${escapeHtml(e.message)}</div>`;
    }
}

function renderGroups() {
    $('groupsCount').textContent = state.groups.length;
    $('groupsTable').innerHTML = rowsTable(state.groups, [
        ...(multiRegion() ? [{ title: 'Region', get: g => regionBadge(g._region) }] : []),
        { title: 'Nome', get: g => `<a href="#" class="mono" data-open="${state.groups.indexOf(g)}">${escapeHtml(g.logGroupName)}</a>` },
        { title: 'Creato', get: g => escapeHtml(fmtDate(g.creationTime)) },
        { title: 'Conservazione', get: g => g.retentionInDays ? `${g.retentionInDays} giorni` : '<span class="text-muted">illimitata</span>' },
        { title: 'Dimensione', cls: 'num', get: g => escapeHtml(fmtBytes(g.storedBytes)) },
        { title: '', cls: 'text-end', get: g => `<button class="btn btn-sm btn-outline-danger btn-xs" data-del="${state.groups.indexOf(g)}" title="Cancella il log group"><i class="fas fa-trash"></i></button>` },
    ], 'Nessun log group');
    $('groupsTable').querySelectorAll('[data-open]').forEach(a => a.addEventListener('click', (ev) => {
        ev.preventDefault();
        const g = state.groups[Number(a.dataset.open)];
        openGroup({ name: g.logGroupName, region: g._region });
    }));
    $('groupsTable').querySelectorAll('[data-del]').forEach(b => b.addEventListener('click', () => {
        const g = state.groups[Number(b.dataset.del)];
        runAction({
            title: 'Cancellare il log group?', danger: true, confirmText: 'Cancella',
            html: `Il log group <strong class="mono">${escapeHtml(g.logGroupName)}</strong> viene cancellato
                con <strong>tutti i suoi stream ed eventi</strong>.` + contextHtml(g._region),
        }, `${CW}/logs/groups/delete`, { region: g._region, name: g.logGroupName }, async () => {
            if (state.group && state.group.name === g.logGroupName) $('streamsCard').classList.add('d-none');
            await loadGroups();
        });
    }));
}

async function createGroup() {
    if (multiRegion()) { showAlert('Per creare un log group scegli una region al posto di "Tutte"', 'warning'); return; }
    const name = $('newGroupName').value.trim();
    const days = $('retentionDays').value;
    if (!name) { showAlert('Indicare il nome del log group', 'warning'); return; }
    await runAction({
        title: 'Creare il log group?', confirmText: 'Crea',
        html: `Nuovo log group <strong class="mono">${escapeHtml(name)}</strong>, conservazione
            ${Number(days) > 0 ? `${escapeHtml(days)} giorni` : 'illimitata'}.` + contextHtml(),
    }, `${CW}/logs/groups/create`, { region: APP.region, name, retention_days: days }, loadGroups);
}

// ---------------------------------------------------------------- stream ed eventi

async function openGroup(group) {
    state.group = group;
    $('currentGroup').textContent = group.name;
    $('streamsCard').classList.remove('d-none');
    await loadStreams();
}

async function loadStreams() {
    const g = state.group;
    $('streamsTable').innerHTML = loadingHtml();
    try {
        const d = await apiGet(`${CW}/logs/streams?${query({ region: g.region, group: g.name })}`);
        $('streamsTable').innerHTML = rowsTable(d.streams, [
            { title: 'Stream', get: s => `<span class="mono">${escapeHtml(s.logStreamName)}</span>` },
            { title: 'Creato', get: s => escapeHtml(fmtDate(s.creationTime)) },
            { title: 'Ultimo evento', get: s => s.lastEventTimestamp ? escapeHtml(fmtDate(s.lastEventTimestamp)) : '<span class="text-muted">nessuno</span>' },
            { title: '', cls: 'text-end text-nowrap', get: s => `<div class="btn-group btn-group-sm">
                <button class="btn btn-outline-primary btn-xs" data-ev="${escapeHtml(s.logStreamName)}" title="Ultimi eventi"><i class="fas fa-magnifying-glass"></i></button>
                <button class="btn btn-outline-secondary btn-xs" data-put="${escapeHtml(s.logStreamName)}" title="Scrivi un evento"><i class="fas fa-pen"></i></button>
                <button class="btn btn-outline-danger btn-xs" data-del="${escapeHtml(s.logStreamName)}" title="Cancella lo stream"><i class="fas fa-trash"></i></button>
            </div>` },
        ], 'Nessuno stream in questo log group');
        $('streamsTable').querySelectorAll('[data-ev]').forEach(b => b.addEventListener('click', () => showEvents(b.dataset.ev)));
        $('streamsTable').querySelectorAll('[data-put]').forEach(b => b.addEventListener('click', () => {
            state.stream = b.dataset.put;
            $('putEventTitle').textContent = b.dataset.put;
            $('putEventMessage').value = '';
            bootstrap.Modal.getOrCreateInstance($('putEventModal')).show();
        }));
        $('streamsTable').querySelectorAll('[data-del]').forEach(b => b.addEventListener('click', () => runAction({
            title: 'Cancellare lo stream?', danger: true, confirmText: 'Cancella',
            html: `Lo stream <strong class="mono">${escapeHtml(b.dataset.del)}</strong> del log group
                <span class="mono">${escapeHtml(g.name)}</span> viene cancellato con tutti i suoi eventi.` + contextHtml(g.region),
        }, `${CW}/logs/streams/delete`, { region: g.region, group: g.name, stream: b.dataset.del }, loadStreams)));
    } catch (e) {
        $('streamsTable').innerHTML = `<div class="alert alert-danger m-2">${escapeHtml(e.message)}</div>`;
    }
}

function eventsTable(events) {
    return rowsTable(events, [
        { title: 'Data', cls: 'text-nowrap', get: e => escapeHtml(fmtDate(e.timestamp)) },
        ...(events.some(e => e.logStreamName) ? [{ title: 'Stream', get: e => `<span class="mono">${escapeHtml(e.logStreamName || '')}</span>` }] : []),
        { title: 'Messaggio', get: e => `<pre class="log">${escapeHtml(e.message)}</pre>` },
    ], 'Nessun evento');
}

async function showEvents(stream) {
    const g = state.group;
    $('eventsTitle').textContent = `Ultimi eventi di ${stream}`;
    $('eventsBody').innerHTML = loadingHtml();
    bootstrap.Modal.getOrCreateInstance($('eventsModal')).show();
    try {
        const d = await apiGet(`${CW}/logs/events?${query({ region: g.region, group: g.name, stream })}`);
        $('eventsBody').innerHTML = eventsTable(d.events);
    } catch (e) {
        $('eventsBody').innerHTML = `<div class="alert alert-danger">${escapeHtml(e.message)}</div>`;
    }
}

async function filterEvents() {
    const g = state.group;
    const pattern = $('filterPattern').value;
    const hours = $('filterHours').value;
    $('eventsTitle').textContent = `Ricerca "${pattern}" in ${g.name} (${$('filterHours').selectedOptions[0].text})`;
    $('eventsBody').innerHTML = loadingHtml();
    bootstrap.Modal.getOrCreateInstance($('eventsModal')).show();
    try {
        const d = await apiGet(`${CW}/logs/filter?${query({ region: g.region, group: g.name, pattern, hours })}`);
        $('eventsBody').innerHTML = eventsTable(d.events);
    } catch (e) {
        $('eventsBody').innerHTML = `<div class="alert alert-danger">${escapeHtml(e.message)}</div>`;
    }
}

async function createStream() {
    const g = state.group;
    const stream = $('newStreamName').value.trim();
    if (!stream) { showAlert('Indicare il nome dello stream', 'warning'); return; }
    await runAction({
        title: 'Creare lo stream?', confirmText: 'Crea',
        html: `Nuovo stream <strong class="mono">${escapeHtml(stream)}</strong> nel log group
            <span class="mono">${escapeHtml(g.name)}</span>.` + contextHtml(g.region),
    }, `${CW}/logs/streams/create`, { region: g.region, group: g.name, stream }, loadStreams);
}

async function putEvent() {
    const g = state.group;
    const message = $('putEventMessage').value;
    if (!message.trim()) return;
    bootstrap.Modal.getOrCreateInstance($('putEventModal')).hide();
    await runAction({
        title: 'Scrivere l\'evento?', confirmText: 'Scrivi',
        html: `Nello stream <span class="mono">${escapeHtml(state.stream)}</span> viene scritto:
            <pre class="json mt-2">${escapeHtml(message)}</pre>` + contextHtml(g.region),
    }, `${CW}/logs/events/put`, { region: g.region, group: g.name, stream: state.stream, message }, loadStreams);
}

// ---------------------------------------------------------------- avvio

document.addEventListener('DOMContentLoaded', () => {
    loadAlarms();
    $('btnAlarms').addEventListener('click', loadAlarms);
    $('stateFilter').addEventListener('change', loadAlarms);
    $('alarmSearch').addEventListener('input', debounce(renderAlarms, 200));
    $('btnCreateAlarm').addEventListener('click', createAlarm);
    $('btnSetState').addEventListener('click', setAlarmState);

    // i log group si leggono alla prima apertura della scheda
    document.querySelector('[data-bs-target="#tabLogs"]').addEventListener('shown.bs.tab', () => {
        if (!state.logsLoaded) loadGroups();
    });
    $('btnGroups').addEventListener('click', loadGroups);
    $('groupPrefix').addEventListener('input', debounce(loadGroups, 600));
    $('btnCreateGroup').addEventListener('click', createGroup);
    $('btnStreams').addEventListener('click', loadStreams);
    $('btnCreateStream').addEventListener('click', createStream);
    $('btnFilter').addEventListener('click', filterEvents);
    $('btnPutEvent').addEventListener('click', putEvent);
});

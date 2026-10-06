/* Manager: gestione dei singoli servizi (ex AWS/Managers/ManagerFlask, piu' i Security Group).
 *
 * Tre colonne: elenco delle risorse, dettaglio della risorsa scelta, terzo livello
 * (sotto-risorse, azioni, log). Ogni servizio e' una voce di SERVICES con:
 *   label(item), sub(item)  testo dell'elenco
 *   open(item)              riempie dettaglio e terzo livello
 *   wideExtra               (facoltativo) terzo livello piu' largo del dettaglio
 * Con la region "Tutte" ogni risorsa porta la sua region (_region): dettagli e azioni
 * vengono chiesti in quella region. Le azioni che modificano AWS chiedono conferma.
 */

const SVC = APP.service;
const API = `/api/manager/${SVC}`;
const state = { items: [], index: -1 };

const item = () => state.items[state.index];
const regionOf = (it) => (APP.serviceGlobal ? '' : ((it && it._region) || APP.region));

// ---------------------------------------------------------------- chiamate

async function mGet(op, params = {}) {
    const d = await apiGet(`${API}/${op}?${query({ region: regionOf(item()), ...params })}`);
    return d.data;
}

/* Azione su AWS dopo la conferma; ritorna i dati o null se annullata/fallita. */
async function mPost(op, body, confirmOpts) {
    const region = regionOf(item());
    if (!await confirmAction({ ...confirmOpts, html: confirmOpts.html + contextHtml(APP.serviceGlobal ? '' : region) })) return null;
    spinner(true);
    try {
        const d = await apiPost(`${API}/${op}`, { region, ...body });
        return d.data === undefined ? {} : d.data;
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger');
        return null;
    } finally {
        spinner(false);
    }
}

// ---------------------------------------------------------------- pannelli

/* Riempie un pannello. Il dettaglio di una risorsa si apre sempre con i suoi tag
 * suggeriti (suggestedTagRows); withTags = false per lo spinner di caricamento. */
function setPanel(which, title, html, actions = '', withTags = true) {
    $(`${which}Title`).innerHTML = title;
    $(`${which}Body`).innerHTML = which === 'detail' && withTags && item() ? withTagRows(html, item()._tags) : html;
    $(`${which}Actions`).innerHTML = actions;
}

function panelLoading(which, title) { setPanel(which, title, loadingHtml(), '', false); }

/* Righe dei tag di suggested_tags (config.json) con il valore sulla risorsa, badge rosso
 * "mancante" se non c'e'. tags null = tag non determinabili. */
function suggestedTagRows(tags) {
    const keys = (APP.tagRules || {}).standard || [];
    if (!keys.length) return '';
    const name = (k) => `<span class="badge text-bg-primary"><i class="fas fa-tag me-1"></i>${escapeHtml(k)}</span>`;
    if (tags === null || tags === undefined) {
        return `<tr><th>${name('Tag')}</th><td class="text-muted">non determinabili per questa risorsa</td></tr>`;
    }
    return keys.map(k => `<tr><th>${name(k)}</th><td>${k in tags
        ? (tags[k] === '' ? '<span class="text-muted">(vuoto)</span>' : escapeHtml(tags[k]))
        : '<span class="badge text-bg-danger">mancante</span>'}</td></tr>`).join('');
}

/* I tag vanno in testa alla tabella delle proprieta' (kvTable) quando e' la prima cosa
 * del dettaglio; altrimenti (S3, API Gateway, log...) in una tabella con lo stesso
 * aspetto sopra il contenuto. */
function withTagRows(html, tags) {
    const rows = suggestedTagRows(tags);
    if (!rows) return html;
    const kv = '<table class="table table-sm table-kv"><tbody>';
    const i = html.indexOf(kv);
    const first = i >= 0 && !/<table|<h6/.test(html.slice(0, i));
    return first ? html.slice(0, i + kv.length) + rows + html.slice(i + kv.length)
        : kv + rows + '</tbody></table>' + html;
}

/* Rende sicura l'apertura: gli errori finiscono nel pannello del dettaglio. */
async function guarded(which, fn) {
    try { await fn(); } catch (e) { panelError(which, e); }
}

function badge(text, cls = 'secondary') {
    return `<span class="badge text-bg-${cls}">${escapeHtml(text)}</span>`;
}

function stateBadge(s) {
    const map = {
        running: 'success', available: 'success', ACTIVE: 'success', ENABLED: 'success', active: 'success',
        OK: 'success', SUCCEEDED: 'success', Deployed: 'success', InService: 'success', healthy: 'success',
        stopped: 'secondary', DISABLED: 'secondary', stopping: 'warning', pending: 'warning', RUNNING: 'info',
        InProgress: 'warning', FAILED: 'danger', ALARM: 'danger', TIMED_OUT: 'danger', unhealthy: 'danger',
        INSUFFICIENT_DATA: 'warning', ABORTED: 'secondary',
    };
    // stati composti (CloudFormation): CREATE_COMPLETE, UPDATE_IN_PROGRESS, ROLLBACK_FAILED...
    const byPattern = !s ? '' : /FAILED/.test(s) ? 'danger' : /ROLLBACK|IN_PROGRESS|PROVISIONING|PENDING/.test(s) ? 'warning'
        : /COMPLETE|ACTIVE|RUNNING/.test(s) ? 'success' : '';
    return s ? badge(s, map[s] || byPattern || 'light border') : '';
}

function pretty(value) {
    let v = value;
    if (typeof v === 'string') { try { v = JSON.parse(v); } catch (e) { return `<pre class="json">${escapeHtml(v)}</pre>`; } }
    return `<pre class="json">${escapeHtml(JSON.stringify(v, null, 2))}</pre>`;
}

function tagsTable(tags) {
    const list = Array.isArray(tags) ? tags.map(t => [t.Key, t.Value]) : Object.entries(tags || {});
    return rowsTable(list, [
        { title: 'Chiave', get: t => `<strong>${escapeHtml(t[0])}</strong>` },
        { title: 'Valore', get: t => escapeHtml(t[1]) },
    ], 'Nessun tag');
}

function h6(text) { return `<h6 class="fw-semibold mt-3 mb-2">${text}</h6>`; }

// ---------------------------------------------------------------- servizi

const SERVICES = {
    // ------------------------------------------------ S3
    s3: {
        label: b => b.Name,
        sub: b => fmtDate(b.CreationDate),
        open: b => s3Browse(b.Name, ''),
    },
    // ------------------------------------------------ EC2
    ec2: {
        label: i => i.Nome || i.InstanceId,
        sub: i => `${i.InstanceId} · ${i.InstanceType} · ${i.State.Name}`,
        open: i => {
            const s = i.State.Name;
            const actions = s === 'stopped' ? '<button class="btn btn-sm btn-success btn-xs" id="btnStart"><i class="fas fa-play me-1"></i>Start</button>'
                : s === 'running' ? '<button class="btn btn-sm btn-danger btn-xs" id="btnStop"><i class="fas fa-stop me-1"></i>Stop</button>' : '';
            setPanel('detail', `${escapeHtml(i.Nome || i.InstanceId)} ${stateBadge(s)}`, kvTable(i, ['Tags', 'Nome']), actions);
            setPanel('extra', 'Tag e rete', tagsTable(i.Tags) + h6('Security group')
                + rowsTable(i.SecurityGroups || [], [
                    { title: 'ID', get: g => `<span class="mono">${escapeHtml(g.GroupId)}</span>` },
                    { title: 'Nome', get: g => escapeHtml(g.GroupName) }]));
            const run = async (op, verb, danger) => {
                const updated = await mPost(op, { id: i.InstanceId }, {
                    title: `${verb} l'istanza?`, danger, confirmText: verb,
                    html: `L'istanza <strong>${escapeHtml(i.Nome || i.InstanceId)}</strong> (<span class="mono">${escapeHtml(i.InstanceId)}</span>) viene ${op === 'start' ? 'avviata' : 'arrestata'}.`,
                });
                if (updated) replaceItem(updated);
            };
            if ($('btnStart')) $('btnStart').addEventListener('click', () => run('start', 'Avvia', false));
            if ($('btnStop')) $('btnStop').addEventListener('click', () => run('stop', 'Arresta', true));
        },
    },
    // ------------------------------------------------ Security Group
    sg: {
        label: g => g.GroupName,
        sub: g => `${g.GroupId} · ${g.VpcId || ''}`,
        open: g => {
            setPanel('detail', escapeHtml(g.GroupName), kvTable(g, ['IpPermissions', 'IpPermissionsEgress', 'Tags'])
                + h6('Tag') + tagsTable(g.Tags));
            setPanel('extra', 'Regole', h6('In ingresso') + sgRules(g.IpPermissions) + h6('In uscita') + sgRules(g.IpPermissionsEgress)
                + h6('Nuova regola in ingresso') + `
                <div class="row g-1 toolbar">
                    <div class="col-4"><label class="form-label">Protocollo</label>
                        <select class="form-select form-select-sm" id="ruleProtocol">
                            <option value="tcp">TCP</option><option value="udp">UDP</option>
                            <option value="icmp">ICMP</option><option value="-1">Tutti</option></select></div>
                    <div class="col-4"><label class="form-label">Da porta</label><input type="number" class="form-control form-control-sm" id="ruleFrom" value="443"></div>
                    <div class="col-4"><label class="form-label">A porta</label><input type="number" class="form-control form-control-sm" id="ruleTo" value="443"></div>
                    <div class="col-6"><label class="form-label">CIDR</label><input type="text" class="form-control form-control-sm" id="ruleCidr" placeholder="es. 10.0.0.0/16"></div>
                    <div class="col-6"><label class="form-label">Descrizione</label><input type="text" class="form-control form-control-sm" id="ruleDesc"></div>
                    <div class="col-12 text-end mt-1"><button class="btn btn-sm btn-primary" id="btnAddRule"><i class="fas fa-plus me-1"></i>Aggiungi regola</button></div>
                </div>`);
            $('btnAddRule').addEventListener('click', async () => {
                const body = { id: g.GroupId, protocol: $('ruleProtocol').value, from_port: $('ruleFrom').value,
                    to_port: $('ruleTo').value, cidr: $('ruleCidr').value.trim(), description: $('ruleDesc').value.trim() };
                if (!body.cidr) { showAlert('Indicare il CIDR della regola', 'warning'); return; }
                const open = body.cidr === '0.0.0.0/0' || body.cidr === '::/0';
                const updated = await mPost('ingress', body, {
                    title: 'Aggiungere la regola?', danger: open, confirmText: 'Aggiungi',
                    html: `Nel security group <strong>${escapeHtml(g.GroupName)}</strong> entra il traffico
                        ${escapeHtml(body.protocol === '-1' ? 'di tutti i protocolli' : body.protocol.toUpperCase())}
                        sulle porte ${escapeHtml(body.from_port)}-${escapeHtml(body.to_port)} da <strong>${escapeHtml(body.cidr)}</strong>.`
                        + (open ? '<div class="alert alert-warning py-1 mt-2 mb-0">Attenzione: la regola apre le porte a tutta Internet.</div>' : ''),
                });
                if (updated) replaceItem(updated);
            });
        },
    },
    // ------------------------------------------------ CloudFront
    cloudfront: {
        label: d => (d.Aliases && d.Aliases.Items && d.Aliases.Items[0]) || d.Origins.Items[0].DomainName,
        sub: d => `${d.Id} · ${d.Status} · ${d.DomainName}`,
        open: async d => {
            panelLoading('detail', escapeHtml(d.Id));
            panelLoading('extra', 'Invalidazioni');
            const data = await mGet('detail', { id: d.Id });
            const cfg = data.distribution.DistributionConfig || {};
            setPanel('detail', `${escapeHtml(d.Id)} ${stateBadge(data.distribution.Status)}`,
                kvTable(data.distribution, ['DistributionConfig']) + h6('Origini')
                + rowsTable((cfg.Origins || {}).Items || [], [
                    { title: 'ID', get: o => escapeHtml(o.Id) },
                    { title: 'Dominio', get: o => `<span class="mono">${escapeHtml(o.DomainName)}</span>` },
                    { title: 'Path', get: o => escapeHtml(o.OriginPath) }])
                + h6('Configurazione') + pretty(cfg));
            setPanel('extra', 'Invalidazioni', rowsTable(data.invalidations, [
                { title: 'ID', get: x => `<span class="mono">${escapeHtml(x.Id)}</span>` },
                { title: 'Stato', get: x => stateBadge(x.Status) },
                { title: 'Creata', get: x => escapeHtml(fmtDate(x.CreateTime)) }], 'Nessuna invalidazione'),
                '<button class="btn btn-sm btn-warning btn-xs" id="btnInvalidate"><i class="fas fa-broom me-1"></i>Invalida /*</button>');
            $('btnInvalidate').addEventListener('click', async () => {
                const done = await mPost('invalidate', { id: d.Id }, {
                    title: 'Invalidare la cache?', confirmText: 'Invalida',
                    html: `Tutta la cache della distribuzione <strong>${escapeHtml(d.Id)}</strong> (percorso <code>/*</code>) viene invalidata.
                        Le prime 1000 invalidazioni al mese sono gratuite.`,
                });
                if (done) { showAlert(`Invalidazione ${done.Id} creata`, 'success'); openItem(state.index); }
            });
        },
    },
    // ------------------------------------------------ SSM Parameter Store
    ssm: {
        label: p => p.Name,
        sub: p => `${p.Type} · versione ${p.Version} · ${fmtDate(p.LastModifiedDate)}`,
        open: p => {
            setPanel('detail', escapeHtml(p.Name), kvTable(p));
            setPanel('extra', 'Modifica il valore', `
                <textarea class="form-control form-control-sm mb-2" id="paramValue" rows="6">${escapeHtml(p.Value)}</textarea>
                <div class="d-flex justify-content-between align-items-center">
                    <span class="footer-note">Il tipo resta ${escapeHtml(p.Type)}${p.Type === 'SecureString' ? ' (cifrato)' : ''}</span>
                    <button class="btn btn-sm btn-primary" id="btnSaveParam"><i class="fas fa-floppy-disk me-1"></i>Salva</button>
                </div>`);
            $('btnSaveParam').addEventListener('click', async () => {
                const value = $('paramValue').value;
                const updated = await mPost('update', { name: p.Name, value }, {
                    title: 'Salvare il parametro?', confirmText: 'Salva',
                    html: `Nuovo valore di <strong>${escapeHtml(p.Name)}</strong>:<pre class="json mt-2">${escapeHtml(value)}</pre>
                        Il valore precedente resta nella cronologia del parametro (versione ${escapeHtml(p.Version)}).`,
                });
                if (updated) replaceItem(updated);
            });
        },
    },
    // ------------------------------------------------ Lambda
    lambda: {
        label: f => f.FunctionName,
        sub: f => `${f.Runtime || f.PackageType} · ${f.MemorySize} MB · ${fmtDate(f.LastModified)}`,
        open: async f => {
            panelLoading('detail', escapeHtml(f.FunctionName));
            panelLoading('extra', 'Invocazioni e log');
            const data = await mGet('detail', { name: f.FunctionName });
            setPanel('detail', escapeHtml(f.FunctionName), kvTable(data.configuration, ['ResponseMetadata']));
            const total = data.invocations.reduce((a, x) => a + x.Sum, 0);
            setPanel('extra', `Invocazioni 24 ore: ${total}`, rowsTable(data.invocations, [
                { title: 'Ora', get: x => escapeHtml(fmtDate(x.Timestamp)) },
                { title: 'Invocazioni', cls: 'num', get: x => escapeHtml(x.Sum) }], 'Nessuna invocazione nelle ultime 24 ore')
                + h6(`Ultimi log (${data.logs.length})`) + rowsTable(data.logs, [
                    { title: 'Data', cls: 'text-nowrap', get: e => escapeHtml(fmtDate(e.timestamp)) },
                    { title: 'Messaggio', get: e => `<pre class="log">${escapeHtml(e.message)}</pre>` }], 'Nessun log'));
        },
    },
    // ------------------------------------------------ EventBridge
    eventbridge: {
        label: r => r.Name,
        sub: r => `${r.State} · ${r.ScheduleExpression || 'event pattern'}`,
        open: async r => {
            panelLoading('detail', escapeHtml(r.Name));
            const data = await mGet('detail', { name: r.Name });
            const enabled = data.State === 'ENABLED';
            setPanel('detail', `${escapeHtml(r.Name)} ${stateBadge(data.State)}`,
                kvTable(data, ['EventPattern', 'Targets']) + (data.EventPattern ? h6('Event pattern') + pretty(data.EventPattern) : ''),
                `<button class="btn btn-sm btn-xs ${enabled ? 'btn-outline-danger' : 'btn-success'}" id="btnToggle">
                    <i class="fas ${enabled ? 'fa-pause' : 'fa-play'} me-1"></i>${enabled ? 'Disattiva' : 'Attiva'}</button>`);
            setPanel('extra', 'Target', rowsTable(data.Targets, [
                { title: 'ID', get: t => escapeHtml(t.Id) },
                { title: 'ARN', get: t => `<span class="mono">${escapeHtml(t.Arn)}</span>` }], 'Nessun target'));
            $('btnToggle').addEventListener('click', async () => {
                const updated = await mPost('enable', { name: r.Name, enabled: !enabled }, {
                    title: `${enabled ? 'Disattivare' : 'Attivare'} la regola?`, danger: enabled,
                    confirmText: enabled ? 'Disattiva' : 'Attiva',
                    html: `La regola <strong>${escapeHtml(r.Name)}</strong> viene ${enabled ? 'disattivata: i suoi target non verranno piu\' invocati' : 'attivata'}.`,
                });
                if (updated) { item().State = updated.State; renderList(); openItem(state.index); }
            });
        },
    },
    // ------------------------------------------------ Step Functions
    stepfunctions: {
        label: m => m.name,
        sub: m => `${m.type} · ${fmtDate(m.creationDate)}`,
        open: async m => {
            panelLoading('detail', escapeHtml(m.name));
            panelLoading('extra', 'Esecuzioni');
            const data = await mGet('detail', { arn: m.stateMachineArn });
            setPanel('detail', escapeHtml(m.name), kvTable(data.detail, ['definition']) + h6('Definizione') + pretty(data.detail.definition));
            setPanel('extra', `Esecuzioni (${data.executions.length})`, rowsTable(data.executions, [
                { title: 'Stato', get: x => stateBadge(x.status) },
                { title: 'Inizio', get: x => escapeHtml(fmtDate(x.startDate)) },
                { title: 'Fine', get: x => escapeHtml(fmtDate(x.stopDate)) },
                { title: 'Nome', get: x => `<span class="mono">${escapeHtml(x.name)}</span>` }], 'Nessuna esecuzione'));
        },
    },
    // ------------------------------------------------ API Gateway
    apigateway: {
        label: a => a.name,
        sub: a => `${a.apiType} · ${a.id}${a.description ? ' · ' + a.description : ''}`,
        open: async a => {
            panelLoading('detail', escapeHtml(a.name));
            panelLoading('extra', 'Stage');
            const data = await mGet('detail', { id: a.id, type: a.apiType });
            const rest = a.apiType === 'REST';
            setPanel('detail', `${escapeHtml(a.name)} ${badge(a.apiType, 'info')} <span class="mono">${escapeHtml(a.id)}</span>`,
                h6(rest ? 'Risorse' : 'Route') + rowsTable(data.resources, [
                    { title: 'Path', get: r => `<span class="mono">${escapeHtml(r.path)}</span>` },
                    { title: 'Metodi', get: r => r.methods.map(x => badge(x, 'info')).join(' ') },
                    ...(rest ? [] : [{ title: 'Target', get: r => `<span class="mono">${escapeHtml(r.target)}</span>` }])],
                    rest ? 'Nessuna risorsa' : 'Nessuna route')
                + h6('API') + kvTable(a));
            setPanel('extra', `Stage (${data.stages.length})`, data.stages.map(s =>
                `<div class="border rounded mb-2"><div class="px-2 py-1 fw-semibold bg-light">${escapeHtml(s.stageName)}</div>${kvTable(s)}</div>`).join('')
                || '<div class="empty-state">Nessuno stage</div>');
        },
    },
    // ------------------------------------------------ DynamoDB
    dynamodb: {
        label: t => t.TableName,
        sub: () => '',
        wideExtra: true,   // a sinistra le informazioni, a destra (piu' larga) i dati
        // all'apertura solo la descrizione: le righe si leggono con "Carica dati"
        open: async t => {
            panelLoading('detail', escapeHtml(t.TableName));
            panelLoading('extra', 'Dati');
            const desc = await mGet('describe', { table: t.TableName });
            ddbOpen(desc);
        },
    },
    // ------------------------------------------------ RDS
    rds: {
        label: d => d.DBInstanceIdentifier,
        sub: d => `${d.Engine} ${d.EngineVersion} · ${d.DBInstanceClass} · ${d.DBInstanceStatus}`,
        open: d => {
            setPanel('detail', `${escapeHtml(d.DBInstanceIdentifier)} ${stateBadge(d.DBInstanceStatus)}`, kvTable(d, ['TagList']));
            setPanel('extra', 'Connessione e tag', kvTable({
                Endpoint: d.Endpoint ? `${d.Endpoint.Address}:${d.Endpoint.Port}` : '',
                'Accesso pubblico': d.PubliclyAccessible ? 'Sì' : 'No',
                'Multi-AZ': d.MultiAZ ? 'Sì' : 'No',
                'Spazio (GB)': d.AllocatedStorage,
                Cifrato: d.StorageEncrypted ? 'Sì' : 'No',
            }) + h6('Tag') + tagsTable(d.TagList));
        },
    },
    // ------------------------------------------------ Glue
    glue: {
        label: j => j.Name,
        sub: j => `${j.GlueVersion || ''} · ${j.WorkerType || ''} · ${fmtDate(j.LastModifiedOn)}`,
        open: async j => {
            setPanel('detail', escapeHtml(j.Name), kvTable(j));
            panelLoading('extra', 'Esecuzioni');
            const runs = await mGet('runs', { name: j.Name });
            setPanel('extra', `Esecuzioni (${runs.length})`, rowsTable(runs, [
                { title: 'Stato', get: r => stateBadge(r.JobRunState) },
                { title: 'Inizio', get: r => escapeHtml(fmtDate(r.StartedOn)) },
                { title: 'Fine', get: r => escapeHtml(fmtDate(r.CompletedOn)) },
                { title: 'Secondi', cls: 'num', get: r => escapeHtml(r.ExecutionTime) }], 'Nessuna esecuzione'));
        },
    },
    // ------------------------------------------------ SQS
    sqs: {
        label: q => q.Name,
        sub: q => q.QueueUrl,
        open: async q => {
            panelLoading('detail', escapeHtml(q.Name));
            const attributes = await mGet('detail', { url: q.QueueUrl });
            setPanel('detail', escapeHtml(q.Name), kvTable(attributes));
            setPanel('extra', 'Messaggi', `
                <label class="form-label" for="msgContent">Invia alla coda</label>
                <div class="input-group input-group-sm mb-1">
                    <input type="text" class="form-control" id="msgContent" placeholder="Testo del messaggio">
                    <button class="btn btn-primary" id="btnSend"><i class="fas fa-paper-plane me-1"></i>Invia</button>
                </div>
                <div class="footer-note mb-3">Il testo viene inviato come <code>{"messageEvent": "..."}</code></div>
                <button class="btn btn-sm btn-outline-danger" id="btnConsume"><i class="fas fa-download me-1"></i>Ricevi messaggi (e cancellali)</button>
                <div class="mt-2" id="messages"></div>`);
            $('btnSend').addEventListener('click', async () => {
                const content = $('msgContent').value;
                if (!content) return;
                const res = await mPost('send', { url: q.QueueUrl, content }, {
                    title: 'Inviare il messaggio?', confirmText: 'Invia',
                    html: `Nella coda <strong>${escapeHtml(q.Name)}</strong> viene inviato:<pre class="json mt-2">${escapeHtml(JSON.stringify({ messageEvent: content }))}</pre>`,
                });
                if (res) { showAlert(`Messaggio inviato (${res.MessageId})`, 'success'); $('msgContent').value = ''; }
            });
            $('btnConsume').addEventListener('click', async () => {
                const msgs = await mPost('consume', { url: q.QueueUrl }, {
                    title: 'Ricevere i messaggi?', danger: true, confirmText: 'Ricevi e cancella',
                    html: `Vengono letti fino a 10 messaggi dalla coda <strong>${escapeHtml(q.Name)}</strong>
                        e <strong>cancellati</strong>: non saranno piu' disponibili per chi consuma la coda.`,
                });
                if (msgs) $('messages').innerHTML = rowsTable(msgs, [
                    { title: 'ID', get: m => `<span class="mono">${escapeHtml(m.MessageId)}</span>` },
                    { title: 'Corpo', get: m => `<pre class="log">${escapeHtml(m.Body)}</pre>` }], 'Nessun messaggio in coda');
            });
        },
    },
    // ------------------------------------------------ SNS
    sns: {
        label: t => t.Name,
        sub: t => t.TopicArn,
        open: async t => {
            panelLoading('detail', escapeHtml(t.Name));
            panelLoading('extra', 'Sottoscrizioni');
            const data = await mGet('detail', { arn: t.TopicArn });
            setPanel('detail', escapeHtml(t.Name), kvTable(data.attributes, ['Policy', 'EffectiveDeliveryPolicy'])
                + (data.attributes.Policy ? h6('Policy') + pretty(data.attributes.Policy) : ''));
            setPanel('extra', `Sottoscrizioni (${data.subscriptions.length})`, rowsTable(data.subscriptions, [
                { title: 'Protocollo', get: s => badge(s.Protocol, 'info') },
                { title: 'Endpoint', get: s => `<span class="mono">${escapeHtml(s.Endpoint)}</span>` }], 'Nessuna sottoscrizione')
                + h6('Pubblica un messaggio') + `
                <div class="input-group input-group-sm mb-1">
                    <input type="text" class="form-control" id="snsContent" placeholder="Testo del messaggio">
                    <button class="btn btn-primary" id="btnPublish"><i class="fas fa-paper-plane me-1"></i>Pubblica</button>
                </div>
                <div class="footer-note">Il testo viene pubblicato come <code>{"message": "..."}</code> e arriva a tutte le sottoscrizioni</div>`);
            $('btnPublish').addEventListener('click', async () => {
                const content = $('snsContent').value;
                if (!content) return;
                const res = await mPost('publish', { arn: t.TopicArn, content }, {
                    title: 'Pubblicare il messaggio?', confirmText: 'Pubblica',
                    html: `Sul topic <strong>${escapeHtml(t.Name)}</strong> (${data.subscriptions.length} sottoscrizioni) viene pubblicato:
                        <pre class="json mt-2">${escapeHtml(JSON.stringify({ message: content }))}</pre>`,
                });
                if (res) { showAlert(`Messaggio pubblicato (${res.MessageId})`, 'success'); $('snsContent').value = ''; }
            });
        },
    },
    // ------------------------------------------------ Elastic IP
    eip: {
        label: a => a.PublicIp,
        sub: a => a.InstanceId || a.NetworkInterfaceId || 'non associato',
        open: a => {
            setPanel('detail', escapeHtml(a.PublicIp), kvTable(a, ['Tags']));
            setPanel('extra', 'Tag', tagsTable(a.Tags)
                + (a.AssociationId ? '' : '<div class="alert alert-warning py-1 mt-2">Indirizzo non associato: si paga anche senza usarlo.</div>'));
        },
    },
    // ------------------------------------------------ EFS
    efs: {
        label: f => f.Name || f.FileSystemId,
        sub: f => `${f.FileSystemId} · ${f.LifeCycleState} · ${fmtBytes((f.SizeInBytes || {}).Value)}`,
        open: async f => {
            setPanel('detail', `${escapeHtml(f.Name || f.FileSystemId)} ${stateBadge(f.LifeCycleState)}`, kvTable(f, ['Tags']) + h6('Tag') + tagsTable(f.Tags));
            panelLoading('extra', 'Mount target');
            const mounts = await mGet('mounts', { id: f.FileSystemId });
            setPanel('extra', `Mount target (${mounts.length})`, rowsTable(mounts, [
                { title: 'ID', get: m => `<span class="mono">${escapeHtml(m.MountTargetId)}</span>` },
                { title: 'Zona', get: m => escapeHtml(m.AvailabilityZoneName) },
                { title: 'Subnet', get: m => escapeHtml(m.SubnetId) },
                { title: 'IP', get: m => escapeHtml(m.IpAddress) },
                { title: 'Stato', get: m => stateBadge(m.LifeCycleState) }], 'Nessun mount target'));
        },
    },
    // ------------------------------------------------ Auto Scaling Group
    asg: {
        label: g => g.AutoScalingGroupName,
        sub: g => `min ${g.MinSize} · desiderate ${g.DesiredCapacity} · max ${g.MaxSize}`,
        open: g => {
            setPanel('detail', escapeHtml(g.AutoScalingGroupName), kvTable(g, ['Instances', 'Tags']));
            setPanel('extra', `Istanze (${(g.Instances || []).length})`, rowsTable(g.Instances || [], [
                { title: 'Istanza', get: i => `<span class="mono">${escapeHtml(i.InstanceId)}</span>` },
                { title: 'Tipo', get: i => escapeHtml(i.InstanceType) },
                { title: 'Zona', get: i => escapeHtml(i.AvailabilityZone) },
                { title: 'Stato', get: i => stateBadge(i.LifecycleState) },
                { title: 'Salute', get: i => stateBadge(i.HealthStatus === 'Healthy' ? 'healthy' : 'unhealthy') }], 'Nessuna istanza'));
        },
    },
    // ------------------------------------------------ Load balancer
    alb: {
        label: lb => lb.LoadBalancerName,
        sub: lb => `${lb.Type} · ${lb.Scheme} · ${(lb.State || {}).Code || ''}`,
        open: async lb => {
            setPanel('detail', `${escapeHtml(lb.LoadBalancerName)} ${stateBadge((lb.State || {}).Code)}`,
                `<div class="mono mb-2">${escapeHtml(lb.DNSName)}</div>` + kvTable(lb));
            panelLoading('extra', 'Listener e target');
            const data = await mGet('detail', { arn: lb.LoadBalancerArn });
            setPanel('extra', 'Listener e target', h6('Listener') + rowsTable(data.listeners, [
                { title: 'Porta', get: l => escapeHtml(`${l.Protocol} ${l.Port}`) },
                { title: 'Azione', get: l => escapeHtml((l.DefaultActions || []).map(a => a.Type).join(', ')) }], 'Nessun listener')
                + data.target_groups.map(tg => h6(`Target group ${escapeHtml(tg.TargetGroupName)}`)
                    + rowsTable(tg.Targets, [
                        { title: 'Target', get: t => `<span class="mono">${escapeHtml(t.Target.Id)}</span>` },
                        { title: 'Porta', get: t => escapeHtml(t.Target.Port) },
                        { title: 'Salute', get: t => stateBadge(t.TargetHealth.State) },
                        { title: 'Motivo', get: t => escapeHtml(t.TargetHealth.Description || '') }], 'Nessun target')).join(''));
        },
    },
    // ------------------------------------------------ CloudWatch Alarms (vista semplice)
    cw_alarms: {
        label: a => a.AlarmName,
        sub: a => `${a.StateValue} · ${a.MetricName || ''}`,
        open: async a => {
            setPanel('detail', `${escapeHtml(a.AlarmName)} ${stateBadge(a.StateValue)}`, kvTable(a));
            panelLoading('extra', 'Storico');
            const history = await mGet('history', { name: a.AlarmName });
            setPanel('extra', 'Storico', rowsTable(history, [
                { title: 'Data', get: h => escapeHtml(fmtDate(h.Timestamp)) },
                { title: 'Tipo', get: h => escapeHtml(h.HistoryItemType) },
                { title: 'Da', get: h => stateBadge(h.OldState) },
                { title: 'A', get: h => stateBadge(h.NewState) }], 'Nessun evento')
                + '<div class="footer-note mt-2">Gestione completa degli allarmi nella sezione <a href="/cloudwatch">CloudWatch</a></div>');
        },
    },
    // ------------------------------------------------ CloudWatch Logs (vista semplice)
    cw_logs: {
        label: g => g.logGroupName,
        sub: g => `${fmtBytes(g.storedBytes)} · ${g.retentionInDays ? g.retentionInDays + ' giorni' : 'conservazione illimitata'}`,
        open: async g => {
            panelLoading('detail', escapeHtml(g.logGroupName));
            setPanel('extra', 'Eventi', '<div class="empty-state">Scegli uno stream</div>');
            const streams = await mGet('streams', { group: g.logGroupName });
            setPanel('detail', escapeHtml(g.logGroupName), rowsTable(streams, [
                { title: 'Ultimo evento', get: s => `<a href="#" data-stream="${escapeHtml(s.logStreamName)}">${escapeHtml(fmtDate(s.lastEventTimestamp || s.creationTime))}</a>` },
                { title: 'Stream', get: s => `<span class="mono">${escapeHtml(s.logStreamName)}</span>` }], 'Nessuno stream'));
            $('detailBody').querySelectorAll('[data-stream]').forEach(a => a.addEventListener('click', async (ev) => {
                ev.preventDefault();
                const stream = a.dataset.stream;
                panelLoading('extra', escapeHtml(stream));
                await guarded('extra', async () => {
                    const events = await mGet('events', { group: g.logGroupName, stream });
                    setPanel('extra', `<span class="mono">${escapeHtml(stream)}</span>`, rowsTable(events, [
                        { title: 'Data', cls: 'text-nowrap', get: e => escapeHtml(fmtDate(e.timestamp)) },
                        { title: 'Messaggio', get: e => `<pre class="log">${escapeHtml(e.message)}</pre>` }], 'Nessun evento'));
                });
            }));
        },
    },
    // ------------------------------------------------ ECR
    ecr: {
        label: r => r.repositoryName,
        sub: r => r.repositoryUri,
        open: async r => {
            setPanel('detail', escapeHtml(r.repositoryName), kvTable(r));
            panelLoading('extra', 'Immagini');
            const images = await mGet('images', { name: r.repositoryName });
            setPanel('extra', `Immagini (${images.length})`, rowsTable(images, [
                { title: 'Tag', get: i => (i.imageTags || []).map(t => badge(t, 'info')).join(' ') || '<span class="text-muted">senza tag</span>' },
                { title: 'Dimensione', cls: 'num', get: i => escapeHtml(fmtBytes(i.imageSizeInBytes)) },
                { title: 'Caricata', get: i => escapeHtml(fmtDate(i.imagePushedAt)) },
                { title: 'Digest', get: i => `<span class="mono" title="${escapeHtml(i.imageDigest)}">${escapeHtml((i.imageDigest || '').slice(7, 19))}</span>` }], 'Nessuna immagine'));
        },
    },
    // ------------------------------------------------ CloudFormation
    cloudformation: {
        label: st => st.StackName,
        sub: st => `${st.StackStatus} · ${fmtDate(st.LastUpdatedTime || st.CreationTime)}`,
        open: async st => {
            setPanel('detail', `${escapeHtml(st.StackName)} ${stateBadge(st.StackStatus)}`,
                kvTable(st, ['Parameters', 'Outputs', 'Tags'])
                + h6(`Parametri (${(st.Parameters || []).length})`) + rowsTable(st.Parameters || [], [
                    { title: 'Chiave', get: x => `<strong>${escapeHtml(x.ParameterKey)}</strong>` },
                    { title: 'Valore', get: x => `<span class="mono">${escapeHtml(x.ResolvedValue || x.ParameterValue)}</span>` }], 'Nessun parametro')
                + h6(`Output (${(st.Outputs || []).length})`) + rowsTable(st.Outputs || [], [
                    { title: 'Chiave', get: x => `<strong>${escapeHtml(x.OutputKey)}</strong>${x.Description ? `<div class="small text-muted">${escapeHtml(x.Description)}</div>` : ''}` },
                    { title: 'Valore', get: x => `<span class="mono">${escapeHtml(x.OutputValue)}</span>` },
                    { title: 'Export', get: x => escapeHtml(x.ExportName || '') }], 'Nessun output'));
            panelLoading('extra', 'Risorse');
            const data = await mGet('detail', { stack: st.StackName });
            const tabs = `<div class="btn-group btn-group-sm" role="group">
                <button class="btn btn-outline-secondary btn-xs active" data-tab="resources">Risorse (${data.resources.length})</button>
                <button class="btn btn-outline-secondary btn-xs" data-tab="events">Eventi</button>
                <button class="btn btn-outline-secondary btn-xs" data-tab="template">Template</button></div>`;
            const show = async (tab) => {
                $('extraActions').querySelectorAll('[data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
                if (tab === 'resources') {
                    $('extraBody').innerHTML = rowsTable(data.resources, [
                        { title: 'Logico', get: r => `<strong>${escapeHtml(r.LogicalResourceId)}</strong><div class="small text-muted">${escapeHtml(r.ResourceType)}</div>` },
                        { title: 'Fisico', get: r => `<span class="mono">${escapeHtml(r.PhysicalResourceId || '')}</span>` },
                        { title: 'Stato', get: r => stateBadge(r.ResourceStatus) + ((r.DriftInformation || {}).StackResourceDriftStatus === 'MODIFIED' ? ' ' + badge('drift', 'warning') : '') }], 'Nessuna risorsa');
                } else if (tab === 'events') {
                    $('extraBody').innerHTML = rowsTable(data.events, [
                        { title: 'Quando', get: e => escapeHtml(fmtDate(e.Timestamp)) },
                        { title: 'Risorsa', get: e => `${escapeHtml(e.LogicalResourceId)}<div class="small text-muted">${escapeHtml(e.ResourceType)}</div>` },
                        { title: 'Stato', get: e => stateBadge(e.ResourceStatus) + (e.ResourceStatusReason ? `<div class="small text-muted text-wrap">${escapeHtml(e.ResourceStatusReason)}</div>` : '') }], 'Nessun evento');
                } else {
                    $('extraBody').innerHTML = loadingHtml();
                    try {
                        data.template = data.template !== undefined ? data.template : await mGet('template', { stack: st.StackName });
                        $('extraBody').innerHTML = typeof data.template === 'string'
                            ? `<pre class="json">${escapeHtml(data.template)}</pre>` : pretty(data.template);
                    } catch (e) { panelError('extra', e); }
                }
            };
            setPanel('extra', 'Stack', '', tabs);
            $('extraActions').querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click', () => show(b.dataset.tab)));
            show('resources');
        },
    },
    // ------------------------------------------------ Route 53
    route53: {
        label: z => z.Name,
        sub: z => `${z.ResourceRecordSetCount} record · ${(z.Config || {}).PrivateZone ? 'privata' : 'pubblica'}`,
        open: async z => {
            setPanel('detail', `${escapeHtml(z.Name)} ${badge((z.Config || {}).PrivateZone ? 'privata' : 'pubblica', 'info')}`, kvTable(z));
            panelLoading('extra', 'Record');
            const records = await mGet('records', { id: z.Id });
            setPanel('extra', `Record (${records.length})`, rowsTable(records, [
                { title: 'Nome', get: r => `<span class="mono">${escapeHtml(r.Name)}</span>` },
                { title: 'Tipo', get: r => badge(r.Type, 'secondary') },
                { title: 'TTL', cls: 'num', get: r => escapeHtml(r.TTL !== undefined ? r.TTL : '') },
                { title: 'Valore', get: r => r.AliasTarget
                    ? `<span class="mono">${escapeHtml(r.AliasTarget.DNSName)}</span> ${badge('alias', 'info')}`
                    : (r.ResourceRecords || []).map(v => `<div class="mono text-break">${escapeHtml(v.Value)}</div>`).join('') }], 'Nessun record'));
        },
    },
    // ------------------------------------------------ Secrets Manager
    secrets: {
        label: x => x.Name,
        sub: x => `modificato ${fmtDate(x.LastChangedDate || x.CreatedDate)}${x.RotationEnabled ? ' · rotazione attiva' : ''}`,
        open: async x => {
            panelLoading('detail', escapeHtml(x.Name));
            const d = await mGet('detail', { id: x.ARN });
            setPanel('detail', escapeHtml(x.Name), kvTable(d, ['ResponseMetadata', 'Tags', 'VersionIdsToStages'])
                + h6('Versioni') + rowsTable(Object.entries(d.VersionIdsToStages || {}), [
                    { title: 'Versione', get: v => `<span class="mono">${escapeHtml(v[0])}</span>` },
                    { title: 'Stadi', get: v => v[1].map(t => badge(t, t === 'AWSCURRENT' ? 'success' : 'secondary')).join(' ') }], 'Nessuna versione'));
            // il valore si legge solo col pulsante e si puo' nascondere di nuovo
            const hide = () => {
                setPanel('extra', 'Valore', `<div class="empty-state">Il valore non viene letto all'apertura.<br>
                    <button class="btn btn-sm btn-warning mt-2" id="btnSecret"><i class="fas fa-eye me-1"></i>Mostra valore</button></div>
                    <div class="footer-note">Legge la versione AWSCURRENT con GetSecretValue (registrato in CloudTrail).</div>`);
                $('btnSecret').addEventListener('click', () => guarded('extra', async () => {
                    const v = await mGet('value', { id: x.ARN });
                    setPanel('extra', `Valore <span class="mono small">${escapeHtml((v.VersionId || '').slice(0, 8))}</span>`,
                        v.Binary ? '<div class="empty-state">Segreto binario: non mostrato</div>' : pretty(v.SecretString),
                        '<button class="btn btn-sm btn-outline-secondary btn-xs" id="btnSecretHide"><i class="fas fa-eye-slash me-1"></i>Nascondi</button>');
                    $('btnSecretHide').addEventListener('click', hide);
                }));
            };
            hide();
        },
    },
    // ------------------------------------------------ ECS
    ecs: {
        label: c => c.clusterName,
        sub: c => `${c.status} · ${c.activeServicesCount} servizi · ${c.runningTasksCount} task attivi`,
        open: async c => {
            panelLoading('detail', escapeHtml(c.clusterName));
            panelLoading('extra', 'Task');
            const data = await mGet('detail', { cluster: c.clusterArn });
            setPanel('detail', `${escapeHtml(c.clusterName)} ${stateBadge(c.status)}`, kvTable(c, ['tags', 'statistics'])
                + h6(`Servizi (${data.services.length})`) + rowsTable(data.services, [
                    { title: 'Servizio', get: x => `<strong>${escapeHtml(x.serviceName)}</strong><div class="small text-muted">${escapeHtml((x.taskDefinition || '').split('/').pop())}</div>` },
                    { title: 'Stato', get: x => stateBadge(x.status) },
                    { title: 'Task', cls: 'num', get: x => `${x.runningCount} / ${x.desiredCount}${x.pendingCount ? ` (+${x.pendingCount})` : ''}` },
                    { title: 'Tipo', get: x => escapeHtml(x.launchType || ((x.capacityProviderStrategy || [])[0] || {}).capacityProvider || '') }], 'Nessun servizio'));
            setPanel('extra', `Task (${data.tasks.length})`, rowsTable(data.tasks, [
                { title: 'Task', get: t => `<span class="mono">${escapeHtml(t.taskArn.split('/').pop().slice(0, 12))}</span><div class="small text-muted">${escapeHtml((t.taskDefinitionArn || '').split('/').pop())}</div>` },
                { title: 'Stato', get: t => stateBadge(t.lastStatus) },
                { title: 'Avviato', get: t => escapeHtml(fmtDate(t.startedAt)) },
                { title: 'CPU/Mem', get: t => escapeHtml(`${t.cpu || ''} / ${t.memory || ''}`) }], 'Nessun task attivo'));
        },
    },
    // ------------------------------------------------ VPC
    vpc: {
        label: v => v.Nome || v.VpcId,
        sub: v => `${v.VpcId} · ${v.CidrBlock}${v.IsDefault ? ' · default' : ''}`,
        open: async v => {
            setPanel('detail', `${escapeHtml(v.Nome || v.VpcId)} ${stateBadge(v.State)}${v.IsDefault ? ' ' + badge('default', 'info') : ''}`, kvTable(v, ['Tags', 'Nome']));
            panelLoading('extra', 'Rete');
            const n = await mGet('network', { id: v.VpcId });
            const route = r => `${escapeHtml(r.DestinationCidrBlock || r.DestinationIpv6CidrBlock || r.DestinationPrefixListId || '')} → `
                + escapeHtml(r.GatewayId || r.NatGatewayId || r.TransitGatewayId || r.VpcPeeringConnectionId || r.NetworkInterfaceId || r.InstanceId || '');
            setPanel('extra', 'Rete', h6(`Subnet (${n.subnets.length})`) + rowsTable(n.subnets, [
                    { title: 'Subnet', get: x => `${escapeHtml(x.Nome || x.SubnetId)}${x.Nome ? `<div class="small text-muted mono">${escapeHtml(x.SubnetId)}</div>` : ''}` },
                    { title: 'CIDR', get: x => `<span class="mono">${escapeHtml(x.CidrBlock)}</span>` },
                    { title: 'AZ', get: x => escapeHtml(x.AvailabilityZone) },
                    { title: 'IP liberi', cls: 'num', get: x => escapeHtml(x.AvailableIpAddressCount) },
                    { title: 'IP pubblico', get: x => x.MapPublicIpOnLaunch ? badge('sì', 'warning') : '' }], 'Nessuna subnet')
                + h6(`Route table (${n.route_tables.length})`) + rowsTable(n.route_tables, [
                    { title: 'ID', get: t => `<span class="mono">${escapeHtml(t.RouteTableId)}</span>${(t.Associations || []).some(a => a.Main) ? ' ' + badge('main', 'info') : ''}` },
                    { title: 'Route', get: t => (t.Routes || []).map(r => `<div class="mono small">${route(r)}</div>`).join('') },
                    { title: 'Subnet', cls: 'num', get: t => (t.Associations || []).filter(a => a.SubnetId).length }], 'Nessuna route table')
                + h6('Gateway') + rowsTable([
                    ...n.internet_gateways.map(g => ({ id: g.InternetGatewayId, type: 'Internet gateway', state: ((g.Attachments || [])[0] || {}).State })),
                    ...n.nat_gateways.map(g => ({ id: g.NatGatewayId, type: `NAT gateway (${g.ConnectivityType || 'public'})`, state: g.State,
                        note: ((g.NatGatewayAddresses || [])[0] || {}).PublicIp })),
                ], [
                    { title: 'ID', get: g => `<span class="mono">${escapeHtml(g.id)}</span>` },
                    { title: 'Tipo', get: g => escapeHtml(g.type) + (g.note ? `<div class="small text-muted mono">${escapeHtml(g.note)}</div>` : '') },
                    { title: 'Stato', get: g => stateBadge(g.state) }], 'Nessun gateway'));
        },
    },
};

// ---------------------------------------------------------------- S3: navigazione e upload

function sgRules(perms) {
    const rows = [];
    (perms || []).forEach(p => {
        const ports = p.IpProtocol === '-1' ? 'tutte' : (p.FromPort === p.ToPort ? `${p.FromPort}` : `${p.FromPort}-${p.ToPort}`);
        const proto = p.IpProtocol === '-1' ? 'tutti' : p.IpProtocol;
        (p.IpRanges || []).forEach(r => rows.push([proto, ports, r.CidrIp, r.Description]));
        (p.Ipv6Ranges || []).forEach(r => rows.push([proto, ports, r.CidrIpv6, r.Description]));
        (p.UserIdGroupPairs || []).forEach(r => rows.push([proto, ports, r.GroupId, r.Description]));
        (p.PrefixListIds || []).forEach(r => rows.push([proto, ports, r.PrefixListId, r.Description]));
    });
    return rowsTable(rows, [
        { title: 'Protocollo', get: r => escapeHtml(r[0]) },
        { title: 'Porte', get: r => escapeHtml(r[1]) },
        { title: 'Origine / destinazione', get: r => `<span class="mono">${escapeHtml(r[2])}</span>` },
        { title: 'Descrizione', get: r => escapeHtml(r[3] || '') },
    ], 'Nessuna regola');
}

async function s3Browse(bucket, prefix) {
    panelLoading('detail', escapeHtml(bucket));
    await guarded('detail', async () => {
        const data = await mGet('objects', { bucket, prefix });
        const parts = prefix.split('/').filter(Boolean);
        const crumbs = [`<a href="#" data-prefix="">${escapeHtml(bucket)}</a>`]
            .concat(parts.map((p, i) => `<a href="#" data-prefix="${escapeHtml(parts.slice(0, i + 1).join('/') + '/')}">${escapeHtml(p)}</a>`));
        const folders = data.folders.map(f => `<a href="#" class="list-group-item list-group-item-action py-1" data-prefix="${escapeHtml(f)}">
            <i class="fas fa-folder text-warning me-2"></i>${escapeHtml(f.slice(prefix.length))}</a>`).join('');
        setPanel('detail', crumbs.join(' / '),
            (folders ? `<div class="list-group mb-2">${folders}</div>` : '')
            + rowsTable(data.objects, [
                { title: 'File', get: o => `<a href="/api/manager/s3/download?${query({ bucket, key: o.Key })}" target="_blank" title="Scarica (URL firmato, valido un'ora)">
                    <i class="fas fa-download me-1"></i>${escapeHtml(o.Key.slice(prefix.length))}</a>` },
                { title: 'Dimensione', cls: 'num', get: o => escapeHtml(fmtBytes(o.Size)) },
                { title: 'Modificato', get: o => escapeHtml(fmtDate(o.LastModified)) }], folders ? 'Nessun file in questa cartella' : 'Cartella vuota')
            + (data.truncated ? '<div class="alert alert-warning py-1 mt-2">Elenco troncato (manager.list_limit in config.json)</div>' : ''));
        $('detailTitle').querySelectorAll('[data-prefix]').forEach(a => a.addEventListener('click', (ev) => { ev.preventDefault(); s3Browse(bucket, a.dataset.prefix); }));
        $('detailBody').querySelectorAll('[data-prefix]').forEach(a => a.addEventListener('click', (ev) => { ev.preventDefault(); s3Browse(bucket, a.dataset.prefix); }));

        setPanel('extra', 'Carica un file', `
            <div class="mb-2">Cartella: <span class="mono">s3://${escapeHtml(bucket)}/${escapeHtml(prefix)}</span></div>
            <input type="file" class="form-control form-control-sm mb-2" id="uploadFile">
            <button class="btn btn-sm btn-primary" id="btnUpload"><i class="fas fa-upload me-1"></i>Carica</button>
            <div class="footer-note mt-2">Dimensione massima: manager.max_upload_mb in config.json. Un file con lo stesso nome viene sovrascritto.</div>`);
        $('btnUpload').addEventListener('click', () => s3Upload(bucket, prefix));
    });
}

async function s3Upload(bucket, prefix) {
    const file = $('uploadFile').files[0];
    if (!file) { showAlert('Scegli il file da caricare', 'warning'); return; }
    const ok = await confirmAction({
        title: 'Caricare il file?', confirmText: 'Carica',
        html: `Il file <strong>${escapeHtml(file.name)}</strong> (${escapeHtml(fmtBytes(file.size))}) viene caricato in
            <span class="mono">s3://${escapeHtml(bucket)}/${escapeHtml(prefix + file.name)}</span>; se esiste gia' viene sovrascritto.` + contextHtml(''),
    });
    if (!ok) return;
    const form = new FormData();
    form.append('bucket', bucket);
    form.append('prefix', prefix);
    form.append('profile', APP.profile);
    form.append('file', file);
    spinner(true);
    try {
        const r = await fetch('/api/manager/s3/upload', { method: 'POST', body: form });
        const d = await parseResponse(r);
        showAlert(d.message, 'success');
        await s3Browse(bucket, prefix);
    } catch (e) {
        showAlert('Errore: ' + e.message, 'danger');
    } finally {
        spinner(false);
    }
}

// ---------------------------------------------------------------- DynamoDB

/* Lettura delle righe pensata per tabelle grandi (vedi aws/services/dynamodb.py):
 * con il valore della partition key e' una Query (solo quella partizione), senza e' uno
 * Scan; in entrambi i casi una pagina alla volta, con "Carica altre righe" che riparte
 * dall'ultima chiave letta. Il filtro sugli attributi riduce le righe mostrate, non
 * quelle lette (e consumate). */
const ddb = { desc: null, items: [], next: null, params: null, seq: 0, totals: null };

const SORT_OPS = [['', 'nessuna condizione'], ['=', '='], ['<', '<'], ['<=', '≤'], ['>', '>'], ['>=', '≥'],
    ['begins_with', 'inizia con'], ['between', 'tra']];
const FILTER_OPS = [['=', '='], ['<>', '≠'], ['<', '<'], ['<=', '≤'], ['>', '>'], ['>=', '≥'],
    ['contains', 'contiene'], ['begins_with', 'inizia con'],
    ['attribute_exists', 'esiste'], ['attribute_not_exists', 'non esiste']];
const TYPE_NAMES = { S: 'stringa', N: 'numero', B: 'binario' };

function ddbKeys(desc, index) {
    const types = Object.fromEntries((desc.AttributeDefinitions || []).map(a => [a.AttributeName, a.AttributeType]));
    let schema = desc.KeySchema;
    if (index) {
        const all = [...(desc.GlobalSecondaryIndexes || []), ...(desc.LocalSecondaryIndexes || [])];
        schema = (all.find(i => i.IndexName === index) || {}).KeySchema || [];
    }
    const of = (kind) => {
        const k = schema.find(x => x.KeyType === kind);
        return k ? { name: k.AttributeName, type: types[k.AttributeName] || 'S' } : null;
    };
    return { partition: of('HASH'), sort: of('RANGE') };
}

function ddbOpen(desc) {
    ddb.desc = desc;
    ddb.items = [];
    ddb.next = null;
    ddb.totals = null;
    const opts = (list) => list.map(([v, t]) => `<option value="${escapeHtml(v)}">${escapeHtml(t)}</option>`).join('');
    const indexes = [
        ...(desc.GlobalSecondaryIndexes || []).map(i => [i.IndexName, `GSI ${i.IndexName}`]),
        ...(desc.LocalSecondaryIndexes || []).map(i => [i.IndexName, `LSI ${i.IndexName}`]),
    ];
    const size = desc.ItemCount !== undefined
        ? `<span class="badge text-bg-light border ms-1" title="Valori aggiornati da AWS circa ogni 6 ore">~${Number(desc.ItemCount).toLocaleString('it-IT')} righe · ${escapeHtml(fmtBytes(desc.TableSizeBytes))}</span>` : '';
    const attrs = [...new Set((desc.AttributeDefinitions || []).map(a => a.AttributeName))];
    ddb.title = `${escapeHtml(desc.TableName)}${size}`;
    ddbShowTable();
    setPanel('extra', 'Dati', `
        <div class="toolbar ddb-form mb-2" id="ddbForm">
            <div class="ddb-group">
                <div class="ddb-field" style="--w: 9rem"><label class="form-label" for="ddbIndex">Indice</label>
                    <select class="form-select form-select-sm" id="ddbIndex"><option value="">Tabella</option>${opts(indexes)}</select></div>
                <div class="ddb-field" style="--w: 14rem; --grow: 3"><label class="form-label text-truncate" for="ddbPk" id="ddbPkLabel">Partition key</label>
                    <input type="text" class="form-control form-control-sm" id="ddbPk" placeholder="vuoto = Scan di tutta la tabella"></div>
            </div>
            <div class="ddb-group" id="ddbSortGroup">
                <div class="ddb-field" id="ddbSortBox" style="--w: 11rem; --grow: 0"><label class="form-label text-truncate" for="ddbSortOp" id="ddbSortLabel">Sort key</label>
                    <select class="form-select form-select-sm" id="ddbSortOp">${opts(SORT_OPS)}</select></div>
                <div class="ddb-field" id="ddbSortValBox" style="--w: 8rem"><label class="form-label" for="ddbSortVal">Valore</label>
                    <input type="text" class="form-control form-control-sm" id="ddbSortVal"></div>
                <div class="ddb-field d-none" id="ddbSortVal2Box" style="--w: 8rem"><label class="form-label" for="ddbSortVal2">e</label>
                    <input type="text" class="form-control form-control-sm" id="ddbSortVal2"></div>
                <div class="ddb-field ddb-fixed" id="ddbDescBox"><div class="form-check mb-1" title="Ordine della sort key (solo Query)">
                    <input class="form-check-input" type="checkbox" id="ddbDesc"><label class="form-check-label" for="ddbDesc">Decrescente</label></div></div>
            </div>
            <div class="ddb-group">
                <div class="ddb-field" style="--w: 9rem"><label class="form-label text-truncate" for="ddbFAttr" title="Si applica dopo la lettura: riduce le righe mostrate, non quelle lette">Filtro su attributo <i class="fas fa-circle-info text-muted"></i></label>
                    <input type="text" class="form-control form-control-sm" id="ddbFAttr" list="ddbAttrs" placeholder="nessun filtro">
                    <datalist id="ddbAttrs">${attrs.map(a => `<option value="${escapeHtml(a)}">`).join('')}</datalist></div>
                <div class="ddb-field" style="--w: 7rem; --grow: 0"><label class="form-label" for="ddbFOp">Operatore</label>
                    <select class="form-select form-select-sm" id="ddbFOp">${opts(FILTER_OPS)}</select></div>
                <div class="ddb-field" style="--w: 8rem"><label class="form-label" for="ddbFVal">Valore</label>
                    <input type="text" class="form-control form-control-sm" id="ddbFVal"></div>
                <div class="ddb-field" style="--w: 6.5rem; --grow: 0"><label class="form-label" for="ddbFType">Tipo</label>
                    <select class="form-select form-select-sm" id="ddbFType"><option value="S">stringa</option><option value="N">numero</option><option value="BOOL">booleano</option></select></div>
            </div>
            <div class="ddb-group ddb-actions">
                <div class="ddb-field" style="--w: 5rem; --grow: 0"><label class="form-label" for="ddbPage">Righe</label>
                    <select class="form-select form-select-sm" id="ddbPage"><option>25</option><option selected>100</option><option>250</option><option>500</option></select></div>
                <div class="ddb-field ddb-fixed d-flex gap-1">
                    <button class="btn btn-sm btn-outline-secondary" id="ddbClear" title="Azzera chiavi e filtro"><i class="fas fa-eraser"></i></button>
                    <button class="btn btn-sm btn-primary text-nowrap" id="ddbLoad"><i class="fas fa-download me-1"></i>Carica dati</button>
                </div>
            </div>
        </div>
        <div class="footer-note mb-2" id="ddbMode"></div>
        <div id="ddbResults"><div class="empty-state">Le righe non vengono lette all'apertura: scegli chiavi e filtri e premi <strong>Carica dati</strong></div></div>`);

    const sync = () => {
        const keys = ddbKeys(desc, $('ddbIndex').value);
        $('ddbPkLabel').textContent = $('ddbPkLabel').title = `Partition key ${keys.partition.name} (${TYPE_NAMES[keys.partition.type] || keys.partition.type})`;
        const hasSort = !!keys.sort;
        $('ddbSortLabel').textContent = $('ddbSortLabel').title = hasSort ? `Sort key ${keys.sort.name} (${TYPE_NAMES[keys.sort.type] || keys.sort.type})` : 'Sort key';
        $('ddbSortGroup').classList.toggle('d-none', !hasSort);
        if (!hasSort) $('ddbSortOp').value = '';
        const op = $('ddbSortOp').value;
        const query = $('ddbPk').value !== '';
        $('ddbSortOp').disabled = $('ddbSortVal').disabled = $('ddbDesc').disabled = !query;
        $('ddbSortVal2Box').classList.toggle('d-none', op !== 'between');
        $('ddbSortValBox').classList.toggle('d-none', !hasSort || !op);
        const noValue = ['attribute_exists', 'attribute_not_exists'].includes($('ddbFOp').value);
        $('ddbFVal').disabled = $('ddbFType').disabled = noValue;
        const where = $('ddbIndex').value ? `l'indice ${$('ddbIndex').value}` : 'la tabella';
        $('ddbMode').innerHTML = query
            ? `<i class="fas fa-bolt me-1 text-success"></i><strong>Query</strong>: legge solo le righe con ${escapeHtml(keys.partition.name)} = valore indicato`
                + (op ? ' e la condizione sulla sort key' : '') + '.'
            : `<i class="fas fa-triangle-exclamation me-1 text-warning"></i><strong>Scan</strong> di ${escapeHtml(where)}, una pagina alla volta: `
                + ($('ddbFAttr').value.trim() ? `con il filtro si leggono al massimo ${Number(APP.ddbMaxRead).toLocaleString('it-IT')} righe per clic, anche se ne passano poche. ` : '')
                + 'Per tabelle grandi conviene la Query sulla partition key (o su un indice).';
    };
    ['ddbIndex', 'ddbSortOp', 'ddbFOp'].forEach(id => $(id).addEventListener('change', sync));
    ['ddbPk', 'ddbFAttr'].forEach(id => $(id).addEventListener('input', sync));
    $('ddbForm').addEventListener('keydown', (ev) => { if (ev.key === 'Enter' && ev.target.tagName === 'INPUT') ddbLoad(false); });
    $('ddbLoad').addEventListener('click', () => ddbLoad(false));
    $('ddbClear').addEventListener('click', () => {
        ['ddbPk', 'ddbSortVal', 'ddbSortVal2', 'ddbFAttr', 'ddbFVal'].forEach(id => { $(id).value = ''; });
        $('ddbSortOp').value = '';
        $('ddbDesc').checked = false;
        sync();
    });
    sync();
}

function ddbFormParams() {
    const pk = $('ddbPk').value;
    const sortOp = pk !== '' ? $('ddbSortOp').value : '';
    const fAttr = $('ddbFAttr').value.trim();
    return {
        table: ddb.desc.TableName, index: $('ddbIndex').value, pk,
        sort_op: sortOp, sort_value: sortOp ? $('ddbSortVal').value : '',
        sort_value2: sortOp === 'between' ? $('ddbSortVal2').value : '',
        descending: pk !== '' && $('ddbDesc').checked ? '1' : '',
        filter_attr: fAttr, filter_op: fAttr ? $('ddbFOp').value : '',
        filter_value: fAttr ? $('ddbFVal').value : '', filter_type: $('ddbFType').value,
        page_size: $('ddbPage').value,
    };
}

/* more = false: nuova ricerca dai campi; true: pagina successiva della ricerca precedente. */
async function ddbLoad(more) {
    if (!more) {
        ddb.params = ddbFormParams();
        ddb.items = [];
        ddb.next = null;
        ddb.totals = { scanned: 0, capacity: 0, requests: 0 };
    }
    const seq = ++ddb.seq;
    const table = ddb.desc.TableName;
    const btn = more ? $('ddbMore') : $('ddbLoad');
    if (btn) { btn.disabled = true; btn.insertAdjacentHTML('afterbegin', '<span class="spinner-border spinner-border-sm me-1"></span>'); }
    try {
        const d = await mGet('items', { ...ddb.params, ...(more && ddb.next ? { start: ddb.next } : {}) });
        if (seq !== ddb.seq || !ddb.desc || ddb.desc.TableName !== table) return;
        ddb.items = ddb.items.concat(d.items);
        ddb.next = d.next;
        ddb.totals.scanned += d.scanned;
        ddb.totals.capacity += d.capacity;
        ddb.totals.requests += 1;
        ddb.mode = d.mode;
        ddb.stopped = d.stopped;
        ddbRenderResults();
    } catch (e) {
        if (seq === ddb.seq) $('ddbResults').innerHTML = `<div class="alert alert-danger py-2">${escapeHtml(e.message)}</div>`;
    } finally {
        const b = more ? $('ddbMore') : $('ddbLoad');
        if (b) { b.disabled = false; const sp = b.querySelector('.spinner-border'); if (sp) sp.remove(); }
    }
}

function ddbCell(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'object') return `<span class="mono">${escapeHtml(JSON.stringify(v))}</span>`;
    return escapeHtml(String(v));
}

function ddbRenderResults() {
    const index = ddb.params.index;
    const keys = ddbKeys(ddb.desc, index);
    const keyCols = [...new Set([keys.partition.name, ...(keys.sort ? [keys.sort.name] : []),
        ...ddb.desc.KeySchema.map(k => k.AttributeName)])];
    const others = [...new Set(ddb.items.flatMap(i => Object.keys(i)))].filter(k => !keyCols.includes(k)).sort();
    const cols = [...keyCols, ...others].slice(0, 12);
    const t = ddb.totals;
    const info = `${ddb.mode === 'query' ? 'Query' : 'Scan'}${index ? ` su ${escapeHtml(index)}` : ''}: `
        + `<strong>${ddb.items.length.toLocaleString('it-IT')}</strong> righe mostrate, ${t.scanned.toLocaleString('it-IT')} lette`
        + ` &middot; ${t.capacity.toLocaleString('it-IT', { maximumFractionDigits: 2 })} RCU consumate`
        + (ddb.next ? ' &middot; ci sono altre righe' : ' &middot; fine dei dati');
    const table = ddb.items.length
        ? '<div class="table-responsive ddb-table"><table class="table table-sm table-hover align-middle mb-0"><thead><tr>'
            + cols.map(c => `<th${keyCols.includes(c) ? ' class="text-primary"' : ''}>${escapeHtml(c)}</th>`).join('') + '</tr></thead><tbody>'
            + ddb.items.map((r, i) => `<tr class="clickable" data-row="${i}">` + cols.map(c => `<td>${ddbCell(r[c])}</td>`).join('') + '</tr>').join('')
            + '</tbody></table></div>'
        : '<div class="empty-state">Nessuna riga con queste condizioni</div>';
    $('ddbResults').innerHTML = `<div class="small mb-1">${info}</div>`
        + (ddb.stopped ? `<div class="alert alert-warning py-1 mb-1 small">Fermato dopo ${t.scanned.toLocaleString('it-IT')} righe lette
            (manager.dynamodb_max_read in config.json): il filtro ne scarta molte. Continua con <strong>Carica altre righe</strong> o usa una Query.</div>` : '')
        + table
        + `<div class="footer-note mt-1">${cols.length < keyCols.length + others.length ? `Mostrate ${cols.length} colonne su ${keyCols.length + others.length}: ` : ''}clic su una riga per vederla intera a sinistra</div>`
        + (ddb.next ? `<div class="text-center mt-2"><button class="btn btn-sm btn-outline-primary" id="ddbMore"><i class="fas fa-angles-down me-1"></i>Carica altre righe</button></div>` : '');
    $('ddbResults').querySelectorAll('tr[data-row]').forEach(tr => tr.addEventListener('click', () => {
        $('ddbResults').querySelectorAll('tr.table-active').forEach(x => x.classList.remove('table-active'));
        tr.classList.add('table-active');
        ddbShowItem(ddb.items[Number(tr.dataset.row)]);
    }));
    if ($('ddbMore')) $('ddbMore').addEventListener('click', () => ddbLoad(true));
}

// Informazioni della tabella (con i tag) nel dettaglio, a sinistra dei dati
function ddbShowTable() {
    setPanel('detail', ddb.title, kvTable(ddb.desc));
    $('ddbResults') && $('ddbResults').querySelectorAll('tr.table-active').forEach(x => x.classList.remove('table-active'));
}

// Riga scelta nei dati: intera al posto delle informazioni, finche' non si torna indietro
function ddbShowItem(row) {
    setPanel('detail', `${ddb.title} &middot; riga`, pretty(row),
        '<button class="btn btn-sm btn-outline-secondary btn-xs" id="ddbBack"><i class="fas fa-table me-1"></i>Descrizione tabella</button>', false);
    $('ddbBack').addEventListener('click', ddbShowTable);
}

// ---------------------------------------------------------------- elenco

async function loadList() {
    $('itemList').innerHTML = loadingHtml();
    state.index = -1;
    setPanel('detail', 'Dettaglio', '<div class="empty-state">Seleziona un elemento dall\'elenco</div>');
    setPanel('extra', '&nbsp;', '');
    try {
        const d = await apiGet(`${API}/list?${query({ region: APP.region })}`);
        state.items = d.items;
        if ((d.warnings || []).length) appendAlertHtml(d.warnings.map(escapeHtml).join('<br>'), 'warning');
        renderList();
    } catch (e) {
        state.items = [];
        $('itemList').innerHTML = `<div class="alert alert-danger m-2 py-2">${escapeHtml(e.message)}</div>`;
    }
}

function renderList() {
    const spec = SERVICES[SVC];
    const q = $('itemSearch').value.trim().toLowerCase();
    const rows = state.items.map((it, i) => [it, i])
        .filter(([it]) => !q || `${spec.label(it)} ${spec.sub(it)}`.toLowerCase().includes(q))
        .sort((a, b) => String(spec.label(a[0])).localeCompare(String(spec.label(b[0])), undefined, { sensitivity: 'base' }));
    $('itemsCount').textContent = rows.length;
    $('itemList').innerHTML = rows.map(([it, i]) => `
        <div class="list-group-item ${i === state.index ? 'active' : ''}" data-i="${i}">
            <div class="d-flex justify-content-between gap-2">
                <span class="item-title">${escapeHtml(spec.label(it))}${tagIcon(it._tags)}</span>
                ${APP.region === ALL && it._region ? regionBadge(it._region) : ''}
            </div>
            <div class="item-sub">${escapeHtml(spec.sub(it))}</div>
        </div>`).join('') || '<div class="empty-state">Nessun elemento</div>';
    $('itemList').querySelectorAll('[data-i]').forEach(el => el.addEventListener('click', () => openItem(Number(el.dataset.i))));
}

async function openItem(i) {
    state.index = i;
    $('itemList').querySelectorAll('[data-i]').forEach(el => el.classList.toggle('active', Number(el.dataset.i) === i));
    setPanel('extra', '&nbsp;', '');
    await guarded('detail', () => SERVICES[SVC].open(item()));
}

/* Dopo un'azione: aggiorna la risorsa nell'elenco (tenendo la region) e riapre il dettaglio. */
function replaceItem(updated) {
    const { _region: region, _tags: tags } = item();
    state.items[state.index] = { _tags: tags, ...updated, ...(region ? { _region: region } : {}) };
    showAlert('Operazione eseguita', 'success');
    renderList();
    openItem(state.index);
}

document.addEventListener('DOMContentLoaded', () => {
    if (SERVICES[SVC].wideExtra) {
        $('detailCol').className = 'col-lg-3';
        $('extraCol').className = 'col-lg-6';
    }
    loadList();
    $('btnReload').addEventListener('click', loadList);
    $('itemSearch').addEventListener('input', debounce(renderList, 150));
});

/* Manager: gestione dei singoli servizi (ex AWS/Managers/ManagerFlask, piu' i Security Group).
 *
 * Tre colonne: elenco delle risorse, dettaglio della risorsa scelta, terzo livello
 * (sotto-risorse, azioni, log). Ogni servizio e' una voce di SERVICES con:
 *   label(item), sub(item)  testo dell'elenco
 *   open(item)              riempie dettaglio e terzo livello
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

function setPanel(which, title, html, actions = '') {
    $(`${which}Title`).innerHTML = title;
    $(`${which}Body`).innerHTML = html;
    $(`${which}Actions`).innerHTML = actions;
}

function panelLoading(which, title) { setPanel(which, title, loadingHtml()); }

function panelError(which, e) {
    $(`${which}Body`).innerHTML = `<div class="alert alert-danger py-2">${escapeHtml(e.message)}</div>`;
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
    return s ? badge(s, map[s] || 'light border') : '';
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
        open: async t => {
            panelLoading('detail', escapeHtml(t.TableName));
            panelLoading('extra', 'Tabella');
            const data = await mGet('detail', { table: t.TableName });
            const keys = (data.table.KeySchema || []).map(k => k.AttributeName);
            const others = [...new Set(data.items.flatMap(i => Object.keys(i)))].filter(k => !keys.includes(k));
            const cols = [...keys, ...others].slice(0, 8);
            setPanel('detail', `${escapeHtml(t.TableName)} &middot; ${data.items.length} righe${data.truncated ? ' (prime)' : ''}`,
                rowsTable(data.items, cols.map(c => ({
                    title: c, get: r => {
                        const v = r[c];
                        return v !== null && typeof v === 'object' ? `<span class="mono">${escapeHtml(JSON.stringify(v))}</span>` : escapeHtml(v);
                    },
                })), 'Tabella vuota')
                + (others.length + keys.length > 8 ? `<div class="footer-note mt-2">Mostrate 8 colonne su ${others.length + keys.length}</div>` : ''));
            setPanel('extra', 'Tabella', kvTable(data.table));
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
    loadList();
    $('btnReload').addEventListener('click', loadList);
    $('itemSearch').addEventListener('input', debounce(renderList, 150));
});

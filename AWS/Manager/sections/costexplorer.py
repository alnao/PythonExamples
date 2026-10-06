"""
Cost Explorer - report dei costi AWS (ex AWS/Managers/CostExplorer).

Versione web del comando:
    aws ce get-cost-and-usage --time-period Start=2026-09-17,End=2026-09-24 \\
      --granularity DAILY --metrics UnblendedCost --group-by Type=DIMENSION,Key=USAGE_TYPE

Funzionalita':
    - costi mese per mese per servizio e per tag (o region, tipo record, account)
      in barre verticali impilate, con filtri incrociati calcolati nel browser
    - i tag e i valori suggeriti vengono dal config.json unico; per Project i
      sottovalori (Valore%) si possono raggruppare sotto il padre
    - riepilogo: totale del periodo, mese in corso con stima a fine mese,
      variazione sul mese precedente, quota dei costi senza tag
    - dettaglio per usage type di un servizio, mensile o giornaliero
    - cache su disco senza scadenza, un file per mese (aws/cost_cache.py): ogni richiesta
      a Cost Explorer costa 0,01 $ e un mese letto non viene piu' riletto da solo
    - sorgente gratuita dal Data Export (CUR 2.0) su S3 (aws/cur_source.py, configurata nel
      file .env): per ogni mese vale l'export se c'e', altrimenti la cache dell'API

La pagina non chiama mai AWS da sola: chiede i dati con cache_only=1 e, se mancano,
propone "Carica i dati dal cloud" con una modale che elenca richieste e costo.

Permessi IAM necessari:
    ce:GetCostAndUsage, ce:GetCostForecast, ce:ListCostAllocationTags
    s3:ListBucket e s3:GetObject sul bucket del Data Export (se configurato)
"""

import json
import logging
import time
from datetime import date
from functools import wraps

from flask import Blueprint, jsonify, render_template, request

from aws.cost_cache import KeyedCache, MonthStore, contiguous_runs, migrate_legacy, months_between
from aws.cost_explorer import (COST_PER_API_CALL, METRICS, CostExplorer, build_filter,
                               dimension_filter, last_months, month_bounds, tag_filter)
from aws.cur_source import DIMENSION_COLUMNS, CurSource
from common import BASE_DIR, current_profile, load_config

bp = Blueprint('costexplorer', __name__)
logger = logging.getLogger(__name__)

CACHE_DIR = BASE_DIR / 'cache'

# Dimensioni ammesse come secondo raggruppamento oltre ai tag
SECOND_DIMENSIONS = {
    'REGION': 'Region',
    'RECORD_TYPE': 'Tipo record (uso, tasse, crediti...)',
    'LINKED_ACCOUNT': 'Account',
}

# Dimensioni ammesse nel dettaglio di un servizio
DRILL_DIMENSIONS = {
    'USAGE_TYPE': 'Usage type',
    'OPERATION': 'Operazione',
    'REGION': 'Region',
}

# Richieste a Cost Explorer fatte da quando e' partita l'applicazione
_api_calls = {'count': 0}


class NotCached(Exception):
    """La richiesta non e' in cache e la pagina ha chiesto di non chiamare AWS."""


# ----------------------------------------------------------------------
# Configurazione
# ----------------------------------------------------------------------

def ce_config():
    """Sezione cost_explorer del config.json unico, con tag suggeriti e region."""
    config = load_config()
    ce = dict(config['cost_explorer'])
    ce['suggested_tags'] = config['suggested_tags']
    ce['regions'] = config['regions']
    return ce


def handle_aws_errors(f):
    """Traduce qualsiasi errore AWS in una risposta JSON leggibile dalla pagina."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except NotCached:
            # non e' un errore: la pagina mostrera' il pulsante "Carica i dati dal cloud"
            return jsonify({'missing': True, **cache_meta()})
        except Exception as e:
            logger.error(f"Errore AWS in {f.__name__}: {e}")
            return jsonify({'error': str(e)}), 500
    return decorated_function


# ----------------------------------------------------------------------
# Cache su disco (vedi aws/cost_cache.py)
# ----------------------------------------------------------------------
# Nessuna scadenza: le chiamate a Cost Explorer si pagano e un mese gia' letto non
# viene riletto da solo. Con cache_only=1 nella query string AWS non viene mai
# chiamato: la pagina interroga sempre prima cosi' e chiama AWS solo dopo la conferma.

keyed_cache = KeyedCache(CACHE_DIR)

# Data Export su S3: configurazione da .env (o dalle variabili d'ambiente)
cur = CurSource(CACHE_DIR, env_file=BASE_DIR / '.env',
                service_names=ce_config().get('cur_service_names'))


def cache_only_mode():
    return request.args.get('cache_only') == '1'


def run_ce(profile, loader):
    """Esegue loader(ce) contando le richieste fatte (ognuna costa 0,01 $)."""
    ce = CostExplorer(aws_profile=profile)
    try:
        return loader(ce)
    finally:
        _api_calls['count'] += ce.api_calls


def cached_call(key_parts, loader, refresh=False):
    """
    Richiesta singola (tag, stima): ritorna (dati, timestamp, da_cache) leggendo dalla
    cache o, se manca (o con refresh), chiamando loader(ce).
    """
    if not refresh:
        data, at = keyed_cache.get(key_parts)
        if at is not None:
            return data, at, True
    if cache_only_mode():
        raise NotCached()
    data = run_ce(key_parts.get('profile'), loader)
    at = time.time()
    keyed_cache.put(key_parts, data, at)
    return data, at, False


def monthly_call(kind, dims, months, loader, refresh=False, cur_query=None, cache_only=None):
    """
    Costi divisi per mese. Per ogni mese, in ordine:
        1. il Data Export su S3 (cur_query), gratis, se ha quel mese
        2. la cache dei mesi letti con l'API di Cost Explorer
        3. l'API di Cost Explorer (a pagamento), solo se non in cache_only
    Per l'API: una richiesta per ogni blocco di mesi consecutivi mancanti (con refresh
    anche per quelli letti prima della fine del mese); i mesi gia' in cache non vengono
    toccati, neanche quando il Data Export li sostituisce.

    loader(ce, primo_mese, ultimo_mese) -> risultato di get_cost_and_usage.
    cur_query(mese) -> voce dal Data Export o None.
    cache_only: None = dal parametro della richiesta, True = mai chiamare AWS (Home).
    Ritorna ({mese: voce o None}, mesi ancora mancanti, mesi letti ora da AWS).
    """
    if cache_only is None:
        cache_only = cache_only_mode()
    store = MonthStore(CACHE_DIR, kind, dims)
    entries = {}
    for m in months:
        e = None
        if cur_query:
            try:
                e = cur_query(m)
            except Exception as ex:   # file illeggibile o altro: si ripiega sull'API
                logger.warning(f"Data Export: {m} non utilizzabile: {ex}")
        if e is None:
            e = store.get(m)
            if e is not None:
                e['source'] = 'api'
        entries[m] = e
    to_load = [m for m in months if entries[m] is None
               or (refresh and entries[m]['source'] == 'api' and not entries[m]['complete'])]
    loaded = []
    if to_load and not cache_only:
        for run in contiguous_runs(to_load):
            data = run_ce(dims['profile'], lambda ce: loader(ce, run[0], run[-1]))
            store.put_result(data, run, time.time())
            for m in run:
                entries[m] = {**store.get(m), 'source': 'api'}
            loaded += run
    missing = [m for m in months if entries[m] is None]
    return entries, missing, loaded


def months_info(entries):
    """Stato di ogni mese: in cache, completo (letto a mese finito), data di lettura."""
    return [{'month': m, 'cached': e is not None,
             'source': e.get('source') if e else None,
             'complete': bool(e and e['complete']),
             'estimated': bool(e and e['estimated']),
             'loaded_at': e['at'] if e else None} for m, e in entries.items()]


def cache_meta():
    """Contatore delle chiamate a Cost Explorer, allegato a ogni risposta."""
    return {
        'api_calls_session': _api_calls['count'],
        'api_cost_session': round(_api_calls['count'] * COST_PER_API_CALL, 2),
    }


def costs_dims(p):
    """Filtri che identificano una serie di costi per mese (anche per la vecchia cache)."""
    return {'api': 'costs', 'profile': p['profile'], 'metric': p['metric'],
            'exclude': bool(p['exclude']), 'region': p['region'], 'group': p['group'],
            'granularity': p.get('granularity') or 'MONTHLY'}


def drill_dims(p):
    return {'api': 'drilldown', 'profile': p['profile'], 'metric': p['metric'],
            'exclude': bool(p['exclude']), 'region': p['region'], 'service': p['service'],
            'dimension': p['dimension'], 'granularity': p.get('granularity') or 'MONTHLY',
            'group': p.get('group') or '', 'group_values': sorted(p.get('group_values') or [])}


def requested_months(start, end):
    """Mesi del periodo, senza quelli futuri (per cui AWS non ha dati)."""
    today = date.today().strftime('%Y-%m')
    return [m for m in months_between(start, end) if m <= today]


# ----------------------------------------------------------------------
# Parametri comuni
# ----------------------------------------------------------------------

def common_params():
    """Legge dalla query string i parametri condivisi da tutte le API dei costi."""
    ce = ce_config()
    months = last_months(int(ce['default_months']))
    metric = request.args.get('metric') or ce['default_metric']
    if metric not in METRICS:
        raise ValueError(f"Metrica non valida: {metric}")
    return {
        'profile': current_profile(),
        'start': request.args.get('start') or months['start'],
        'end': request.args.get('end') or months['end'],
        'metric': metric,
        'exclude': request.args.get('exclude') == '1',
        # region come filtro sui costi ('' = tutte): non e' la region scelta nelle altre sezioni
        'region': request.args.get('region', '').strip(),
    }


def parse_group(group):
    """'TAG:Project' -> {'Type': 'TAG', 'Key': 'Project'}; 'DIM:REGION' -> dimensione."""
    kind, _, key = (group or '').partition(':')
    if kind == 'TAG' and key:
        return {'Type': 'TAG', 'Key': key}
    if kind == 'DIM' and key in SECOND_DIMENSIONS:
        return {'Type': 'DIMENSION', 'Key': key}
    raise ValueError(f"Raggruppamento non valido: {group}")


# ----------------------------------------------------------------------
# Pagina
# ----------------------------------------------------------------------

@bp.route('/costs')
def index():
    ce = ce_config()
    return render_template('costexplorer.html',
                           default_months=int(ce['default_months']),
                           default_metric=ce['default_metric'],
                           default_group=ce['default_group'],
                           metrics=list(METRICS.keys()),
                           cost_regions=ce['regions'],
                           second_dimensions=SECOND_DIMENSIONS,
                           drill_dimensions=DRILL_DIMENSIONS,
                           suggested_tags=ce['suggested_tags'],
                           prefix_match_keys=ce['prefix_match_keys'],
                           service_aliases=ce['service_aliases'],
                           api_cost=COST_PER_API_CALL)


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------

@bp.route('/api/ce/tags')
@handle_aws_errors
def api_tags():
    """Cost allocation tag del Billing (attivi e inattivi)."""
    profile = current_profile()
    tags, at, from_cache = cached_call({'api': 'tags', 'profile': profile},
                                       lambda ce: ce.list_cost_allocation_tags(),
                                       refresh=request.args.get('refresh') == '1')
    return jsonify({'tags': tags, 'cached': from_cache, 'cached_at': at, **cache_meta()})


@bp.route('/api/ce/costs')
@handle_aws_errors
def api_costs():
    """
    Costi raggruppati per servizio e per un secondo criterio, al mese o al giorno.

    Una sola serie (SERVICE x gruppo) basta per tutti i grafici e i filtri incrociati,
    che vengono poi calcolati nel browser. I dati sono in cache mese per mese:
    months dice quali mesi ci sono (e se sono completi), missing_months quali mancano.

    Query params:
        profile, start, end (YYYY-MM), metric, exclude (1 = senza tasse/crediti/rimborsi),
        region, group ('TAG:Project' o 'DIM:REGION'...), granularity (MONTHLY | DAILY),
        months (elenco 'YYYY-MM' separati da virgola, al posto di start/end: la pagina
        chiede ad AWS esattamente i mesi che le mancano),
        cache_only (1 = non chiamare AWS), refresh (1 = rilegge i mesi incompleti)
    """
    p = common_params()
    group = request.args.get('group') or ce_config()['default_group']
    granularity = 'DAILY' if request.args.get('granularity') == 'DAILY' else 'MONTHLY'
    group_by = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}, parse_group(group)]
    filter_expr = build_filter(p['exclude'], p['region'])
    if request.args.get('months'):
        today = date.today().strftime('%Y-%m')
        months = sorted({m for m in request.args['months'].split(',') if len(m) == 7 and m <= today})
    else:
        months = requested_months(p['start'], p['end'])

    entries, missing, loaded = monthly_call(
        'costs', costs_dims({**p, 'group': group, 'granularity': granularity}), months,
        lambda ce, a, b: ce.get_cost_and_usage(month_bounds(a, b), granularity, p['metric'],
                                               group_by, filter_expr),
        refresh=request.args.get('refresh') == '1',
        cur_query=lambda m: cur.query(m, p['profile'], granularity, p['metric'], group_by,
                                      p['exclude'], p['region']))

    # period e' il giorno (o il primo del mese), month serve a tabelle e riepilogo
    rows, periods = [], []
    for m in months:
        e = entries[m]
        if not e:
            continue
        rows += [{'period': r['period'], 'month': m, 'service': r['keys'][0],
                  'group': r['keys'][1], 'amount': r['amount']} for r in e['rows']]
        periods += [{'start': x['start'], 'estimated': x['estimated']} for x in e['periods']]
    return jsonify({
        **p, 'group': group, 'granularity': granularity,
        'months': months_info(entries), 'missing_months': missing, 'loaded_months': loaded,
        'periods': periods, 'rows': rows,
        **cache_meta(),
    })


@bp.route('/api/ce/forecast')
@handle_aws_errors
def api_forecast():
    """Stima del costo da oggi a fine mese (una per giorno), con gli stessi filtri del report."""
    p = common_params()
    filter_expr = build_filter(p['exclude'], p['region'])
    today = time.strftime('%Y-%m-%d')
    data, at, from_cache = cached_call(
        forecast_key(p['profile'], p['metric'], p['exclude'], p['region'], today),
        lambda ce: ce.get_month_forecast(p['metric'], filter_expr),
        refresh=request.args.get('refresh') == '1')
    return jsonify({'forecast': data, 'cached': from_cache, 'cached_at': at, **cache_meta()})


def forecast_key(profile, metric, exclude, region, day):
    return {'api': 'forecast', 'profile': profile, 'metric': metric,
            'exclude': exclude, 'region': region, 'day': day}


@bp.route('/api/ce/drilldown')
@handle_aws_errors
def api_drilldown():
    """
    Dettaglio di un servizio per usage type (o operazione, o region).

    E' il comando del README: get-cost-and-usage ... --group-by DIMENSION,USAGE_TYPE,
    con in piu' il filtro sul servizio e, se richiesto, sui valori del gruppo.
    Anche qui la cache e' per mese.

    Query params:
        i parametri comuni, service (obbligatorio), dimension (USAGE_TYPE),
        granularity (MONTHLY | DAILY; con DAILY si usa il mese indicato in month),
        group + group_value (ripetibile) per restringere ai valori di un tag/dimensione,
        cache_only, refresh
    """
    p = common_params()
    service = request.args.get('service', '').strip()
    if not service:
        return jsonify({'error': 'parametro service obbligatorio'}), 400
    dimension = request.args.get('dimension', 'USAGE_TYPE')
    if dimension not in DRILL_DIMENSIONS:
        return jsonify({'error': f'dimensione non valida: {dimension}'}), 400
    granularity = 'DAILY' if request.args.get('granularity') == 'DAILY' else 'MONTHLY'
    month = request.args.get('month', '')
    months = requested_months(month, month) if granularity == 'DAILY' and month \
        else requested_months(p['start'], p['end'])

    extra = [dimension_filter('SERVICE', [service])]
    cur_filters = [{'column': 'service', 'values': [service]}]
    # piu' valori quando nella pagina i sottovalori sono raggruppati sotto il padre
    group, group_values = request.args.get('group', ''), sorted(request.args.getlist('group_value'))
    if group and group_values:
        g = parse_group(group)
        extra.append(tag_filter(g['Key'], group_values) if g['Type'] == 'TAG'
                     else dimension_filter(g['Key'], group_values))
        cur_filters.append({'tag': g['Key'], 'values': group_values} if g['Type'] == 'TAG'
                           else {'column': DIMENSION_COLUMNS[g['Key']], 'values': group_values})
    else:
        group, group_values = '', []
    filter_expr = build_filter(p['exclude'], p['region'], extra)

    dims = drill_dims({**p, 'service': service, 'dimension': dimension, 'granularity': granularity,
                       'group': group, 'group_values': group_values})
    entries, missing, loaded = monthly_call(
        'drilldown', dims, months,
        lambda ce, a, b: ce.get_cost_and_usage(month_bounds(a, b), granularity, p['metric'],
                                               [{'Type': 'DIMENSION', 'Key': dimension}], filter_expr),
        refresh=request.args.get('refresh') == '1',
        cur_query=lambda m: cur.query(m, p['profile'], granularity, p['metric'],
                                      [{'Type': 'DIMENSION', 'Key': dimension}], p['exclude'],
                                      p['region'], cur_filters))

    rows, periods = [], []
    for m in months:
        e = entries[m]
        if e:
            rows += [{'period': r['period'], 'key': r['keys'][0], 'amount': r['amount']} for r in e['rows']]
            periods += [x['start'] for x in e['periods']]
    return jsonify({
        'service': service, 'dimension': dimension, 'granularity': granularity,
        'period': month_bounds(months[0], months[-1]) if months else None,
        'metric': p['metric'], 'filter': filter_expr,
        'months': months_info(entries), 'missing_months': missing, 'loaded_months': loaded,
        'periods': periods, 'rows': rows,
        **cache_meta(),
    })


@bp.route('/api/ce/cur/status')
@handle_aws_errors
def api_cur_status():
    """Stato del Data Export su S3: configurazione, mesi disponibili, ultimo aggiornamento."""
    return jsonify({**cur.status(current_profile(), force=request.args.get('refresh') == '1'), **cache_meta()})


# ----------------------------------------------------------------------
# Riepilogo per la Home: solo cache e Data Export, mai chiamate a pagamento
# ----------------------------------------------------------------------

def _cached_series(profile, metric, default_group):
    """
    Serie dei costi gia' in cache per profilo e metrica, senza filtri su region e tasse:
    prima quella col raggruppamento di default, prima le mensili. I totali per servizio
    sono gli stessi qualunque sia il secondo raggruppamento.
    """
    series = []
    for f in (CACHE_DIR / 'costs').glob('*/_filtri.json'):
        try:
            dims = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if (dims.get('profile') == profile and dims.get('metric') == metric
                and not dims.get('exclude') and not dims.get('region')):
            series.append(dims)
    series.sort(key=lambda d: (d.get('group') != default_group, d.get('granularity') != 'MONTHLY'))
    return series


def _cached_month(profile, metric, group_by, series, month):
    """
    Un mese di costi senza chiamare AWS: dal Data Export se c'e', altrimenti dalla prima
    serie in cache che ha quel mese. Ritorna (voce, raggruppamento usato) o (None, None).
    """
    try:
        entry = cur.query(month, profile, 'MONTHLY', metric, group_by)
        if entry is not None:
            g = group_by[1]
            return entry, f"{'TAG' if g['Type'] == 'TAG' else 'DIM'}:{g['Key']}"
    except Exception as ex:
        logger.warning(f"Data Export: {month} non utilizzabile: {ex}")
    for dims in series:
        e = MonthStore(CACHE_DIR, 'costs', dims).get(month)
        if e is not None:
            return {**e, 'source': 'api'}, dims.get('group')
    return None, None


def cached_breakdown(profile, group):
    """
    Costi per valore di un tag (group = 'TAG:Project') nel mese piu' recente in cache
    tra gli ultimi 3, confrontati col mese prima. Solo Data Export e serie gia' in cache
    con quel raggruppamento: se mancano la Home rimanda al Cost Explorer.
    """
    ce = ce_config()
    metric = ce['default_metric']
    group_by = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}, parse_group(group)]
    period = last_months(3)
    months = requested_months(period['start'], period['end'])
    series = [d for d in _cached_series(profile, metric, group) if d.get('group') == group]

    def by_value(month):
        entry, _ = _cached_month(profile, metric, group_by, series, month)
        if entry is None:
            return None, None
        totals = {}
        for r in entry['rows']:
            totals[r['keys'][1]] = totals.get(r['keys'][1], 0) + r['amount']
        return totals, entry.get('source')

    for i in range(len(months) - 1, -1, -1):
        last, source = by_value(months[i])
        if last is None:
            continue
        prev = by_value(months[i - 1])[0] if i > 0 else None
        items = [{'key': k, 'amount': round(a, 4),
                  'previous': None if prev is None else round(prev.get(k, 0), 4)}
                 for k, a in sorted(last.items(), key=lambda kv: -kv[1]) if a]
        return {'group': group, 'month': months[i], 'source': source,
                'previous_cached': prev is not None, 'items': items}
    return {'group': group, 'month': None, 'items': []}


def cached_summary(profile):
    """
    Costi degli ultimi 3 mesi per la Home. Per ogni mese: Data Export se c'e', altrimenti
    una serie gia' in cache (mensile o giornaliera). Se un mese manca non si chiama AWS:
    la Home rimanda al Cost Explorer.
    """
    ce = ce_config()
    metric, group = ce['default_metric'], ce['default_group']
    period = last_months(3)
    months = requested_months(period['start'], period['end'])
    group_by = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}, parse_group(group)]
    series = _cached_series(profile, metric, group)

    out_months, rows_by_month = [], {}
    for m in months:
        entry, used_group = _cached_month(profile, metric, group_by, series, m)
        if entry is None:
            out_months.append({'month': m, 'cached': False})
            continue
        rows = entry['rows']
        rows_by_month[m] = (rows, used_group)
        out_months.append({
            'month': m, 'cached': True, 'source': entry.get('source'),
            'complete': bool(entry.get('complete')), 'loaded_at': entry.get('at'),
            'group': used_group, 'total': round(sum(r['amount'] for r in rows), 4),
        })

    # servizi del mese piu' recente con dati, confrontati col mese prima
    cached = [m for m in months if m in rows_by_month]
    services, untagged = [], None
    if cached:
        last = cached[-1]
        prev = months[months.index(last) - 1] if months.index(last) > 0 else None
        by_service = {}
        for r in rows_by_month[last][0]:
            by_service[r['keys'][0]] = by_service.get(r['keys'][0], 0) + r['amount']
        prev_by_service = {}
        for r in (rows_by_month.get(prev, ([], None))[0] if prev else []):
            prev_by_service[r['keys'][0]] = prev_by_service.get(r['keys'][0], 0) + r['amount']
        services = [{'service': s, 'amount': round(a, 4), 'previous': round(prev_by_service.get(s, 0), 4)}
                    for s, a in sorted(by_service.items(), key=lambda kv: -kv[1]) if a]
        used_group = rows_by_month[last][1] or ''
        if used_group.startswith('TAG:'):
            total = sum(r['amount'] for r in rows_by_month[last][0])
            amount = sum(r['amount'] for r in rows_by_month[last][0] if r['keys'][1] == '')
            untagged = {'month': last, 'key': used_group[4:], 'amount': round(amount, 4),
                        'total': round(total, 4)}

    forecast, _ = keyed_cache.get(forecast_key(profile, metric, False, '', time.strftime('%Y-%m-%d')))
    return {
        'profile': profile, 'metric': metric, 'months': out_months,
        'services': services, 'untagged': untagged, 'forecast': forecast,
        'cur_enabled': cur.enabled,
    }


# La cache della versione precedente (una voce per richiesta) viene convertita in
# quella per mese: i dati gia' pagati si riusano
migrate_legacy(CACHE_DIR, costs_dims, drill_dims)

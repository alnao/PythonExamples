"""
Tag Manager - gestione dei tag delle risorse AWS (ex AWS/Managers/TagManager).

Versione web del comando:
    aws resourcegroupstaggingapi get-resources --region "$R"

Funzionalita':
    - tabella di tutte le risorse di una region, o di tutte le region della lista
      ("Tutte"), con tutti i dati e i tag
    - due sorgenti dati: la Tagging API (che vede solo le risorse gia' taggate
      almeno una volta) e AWS Resource Explorer (che le vede tutte), unite di default
    - filtri: senza tag, con tag, con una chiave specifica, con chiave=valore,
      senza una chiave specifica, per servizio e per testo libero
    - aggiunta e rimozione dei tag, sulla singola risorsa o in massa (con conferma)
    - report multi-region con una colonna per ogni tag suggerito

Permessi IAM necessari:
    tag:GetResources, tag:GetTagKeys, tag:GetTagValues,
    tag:TagResources, tag:UntagResources, ec2:DescribeRegions,
    resource-explorer-2:GetDefaultView, resource-explorer-2:Search
"""

import logging
import time

from flask import Blueprint, jsonify, render_template, request

from aws.tag_manager import TagManager, parse_arn
from common import (ALL, GLOBAL_REGION, api_errors, aws_session, current_profile, current_region,
                    load_config, region_list, run_parallel, save_config_value)

bp = Blueprint('tagmanager', __name__)
logger = logging.getLogger(__name__)

# Cache in memoria delle risorse gia' lette: la get_resources su account grandi
# e' lenta, quindi il risultato viene riusato finche' non si chiede il refresh
# o non scade (tag_manager.cache_ttl). Ogni voce e' {'data': {...}, 'at': timestamp}.
_cache = {}


def cache_ttl():
    return int(load_config()['tag_manager']['cache_ttl'])


def cache_get(key):
    """Ritorna (dati, timestamp) se la voce esiste e non e' scaduta, altrimenti (None, None)."""
    voce = _cache.get(key)
    if not voce or time.time() - voce['at'] > cache_ttl():
        _cache.pop(key, None)
        return None, None
    return voce['data'], voce['at']


def cache_set(key, data):
    """Salva la voce e ritorna (dati, timestamp) come cache_get."""
    _cache[key] = {'data': data, 'at': time.time()}
    return data, _cache[key]['at']


def invalidate_cache(profile, region):
    """Svuota la cache di quella coppia profilo/region per tutte le sorgenti dati."""
    for chiave in [k for k in _cache if k.startswith(f"{profile}|{region}|")]:
        del _cache[chiave]


def region_resources(profile, region, source, refresh):
    """
    Risorse di una region (dalla cache se c'e'): (dati, timestamp, da_cache).
    Si leggono sempre tutte (comprese quelle senza tag) e si filtra dopo: e' l'unico
    modo per poter mostrare anche le "untagged".
    """
    key = f"{profile}|{region}|{source}"
    dati, at = (None, None) if refresh else cache_get(key)
    if dati is not None:
        return dati, at, True
    dati, at = cache_set(key, TagManager(region_name=region, aws_profile=profile).get_all_resources(source))
    return dati, at, False


def multi_region_resources(profile, region, source, refresh):
    """
    Risorse di una o di tutte le region, lette in parallelo.
    Ritorna (risorse, warnings, da_cache, data della region in cache da piu' tempo).
    """
    results = run_parallel(region_list(region),
                           lambda r: region_resources(profile, r, source, refresh))
    resources, warnings = [], []
    any_cached, oldest_at = False, None
    for r, res, err in results:
        if err:
            warnings.append(f"{r}: {err}")
            continue
        dati, at, from_cache = res
        if from_cache:
            any_cached = True
            oldest_at = at if oldest_at is None else min(oldest_at, at)
        for risorsa in dati['resources']:
            # la region serve per le modifiche quando nella pagina e' scelto "Tutte"
            risorsa['region'] = risorsa.get('region') or r
            resources.append(risorsa)
        prefix = f"{r}: " if region == ALL else ''
        warnings.extend(prefix + w for w in dati.get('warnings', []))
    return resources, warnings, any_cached, oldest_at


# ----------------------------------------------------------------------
# Tag delle risorse per Manager e Panoramic
# ----------------------------------------------------------------------

class TagLookup:
    """
    Tag delle risorse per ARN, per le icone di Manager e Panoramic.

    Legge la Tagging API di tutte le region della lista (piu' us-east-1 per i servizi
    globali) usando la stessa cache del Tag Manager: una risorsa che non compare non ha
    tag (la Tagging API elenca solo quelle taggate almeno una volta). Per le region che
    non si riescono a leggere i tag restano sconosciuti (None) e non si mostra nessuna icona.

    Le voci da risolvere sono ('inline', tags) quando l'elenco di AWS contiene gia' i tag,
    oppure ('arn', arn) con '{account}' e '{region}' da sostituire.
    """

    def __init__(self, profile):
        self.profile = profile
        self._index = None
        self._account = None

    def _load(self):
        regions = list(dict.fromkeys(load_config()['regions'] + [GLOBAL_REGION]))
        results = run_parallel(regions, lambda r: region_resources(self.profile, r, 'tagging', False))
        self._index, self.read_regions = {}, set()
        for r, res, err in results:
            if err:
                continue
            self.read_regions.add(r)
            for risorsa in res[0]['resources']:
                self._index[risorsa['arn']] = risorsa['tags']

    @property
    def account(self):
        if self._account is None:
            try:
                self._account = aws_session(self.profile).client('sts').get_caller_identity()['Account']
            except Exception as e:
                logger.warning(f"Account non leggibile: {e}")
                self._account = ''
        return self._account

    def resolve(self, entry, region=''):
        """Tag {chiave: valore} della risorsa, oppure None se non si possono sapere."""
        if not entry:
            return None
        kind, value = entry
        if kind == 'inline':
            return normalize_tags(value)
        if not value:
            return None
        if '{account}' in value:
            if not self.account:
                return None
            value = value.replace('{account}', self.account)
        value = value.replace('{region}', region or '')
        if self._index is None:
            self._load()
        arn_region = parse_arn(value)['region'] or GLOBAL_REGION
        if value in self._index:
            return self._index[value]
        # region non letta (errore o fuori lista): meglio nessuna icona che un falso allarme
        return {} if arn_region in self.read_regions or not parse_arn(value)['region'] else None


def normalize_tags(tags):
    """Tag come dizionario da [{'Key', 'Value'}], [{'key', 'value'}] o gia' dizionario."""
    if not tags:
        return {}
    if isinstance(tags, dict):
        return {str(k): '' if v is None else str(v) for k, v in tags.items()}
    out = {}
    for t in tags:
        key = t.get('Key', t.get('key'))
        if key is not None:
            out[key] = t.get('Value', t.get('value', '')) or ''
    return out


# ----------------------------------------------------------------------
# Pagine
# ----------------------------------------------------------------------

def page_data():
    config = load_config()
    suggested_tags = config.get('suggested_tags', {})
    return {
        # Per la datalist dei suggerimenti servono solo le chiavi
        'suggested_tag_keys': list(suggested_tags.keys()) if isinstance(suggested_tags, dict) else [],
        'suggested_tags': suggested_tags,
        'compliant_tags': config.get('compliant_tags', {}),
        'tag_config': config['tag_manager'],
    }


@bp.route('/tags')
def index():
    """Pagina principale."""
    return render_template('tagmanager.html', **page_data())


@bp.route('/tags/report')
def report_page():
    """Pagina report aggregata su tutte le region."""
    return render_template('tagmanager_report.html', **page_data())


# ----------------------------------------------------------------------
# API di lettura
# ----------------------------------------------------------------------

@bp.route('/api/tags/report/resources')
@api_errors
def api_report_resources():
    """Ritorna le risorse aggregate su tutte le region configurate.

    Query params:
        profile: profilo AWS (opzionale, default quello della navbar)
        refresh: 1 per ignorare la cache
    """
    config = load_config()
    profile = current_profile()
    resources, warnings, any_cached, oldest_at = multi_region_resources(
        profile, ALL, 'both', request.args.get('refresh') == '1')
    # Ordina per region, service, tipo, nome
    resources.sort(key=lambda r: (r.get('region', ''), r.get('service', ''), r.get('resource_type', ''), r.get('name', '')))
    return jsonify({
        'regions': config['regions'],
        'profile': profile,
        'resources': resources,
        'warnings': warnings,
        'total': len(resources),
        'cached': any_cached,
        'cached_at': oldest_at,
        'cache_ttl': cache_ttl(),
    })


@bp.route('/api/tags/resources')
@api_errors
def get_resources():
    """
    Elenca le risorse della region (o di tutte) applicando il filtro richiesto.

    Parametri:
        region ('__all__' = tutte le region della lista), profile
        source: both | tagging | explorer (sorgente dei dati, vedi TagManager)
        filter_mode: all | untagged | tagged | with_key | with_key_value | without_key
        tag_key, tag_value: usati dai filtri sui tag
        refresh: 1 per ignorare la cache e rileggere da AWS
    """
    profile, region = current_profile(), current_region()
    source = request.args.get('source', 'both')
    filter_mode = request.args.get('filter_mode', 'all')
    tag_key = request.args.get('tag_key', '').strip()
    tag_value = request.args.get('tag_value', '').strip()

    resources, warnings, from_cache, cached_at = multi_region_resources(
        profile, region, source, request.args.get('refresh') == '1')
    resources.sort(key=lambda r: (r['service'], r['resource_type'], r['name']))
    filtered = apply_filter(resources, filter_mode, tag_key, tag_value)

    return jsonify({
        'region': region,
        'profile': profile,
        'source': source,
        'filter_mode': filter_mode,
        'resources': filtered,
        'summary': TagManager.build_summary(resources),
        'filtered_count': len(filtered),
        'warnings': warnings,
        'cached': from_cache,
        'cached_at': cached_at,
        'cache_ttl': cache_ttl(),
    })


def apply_filter(resources, filter_mode, tag_key, tag_value):
    """Applica il filtro sui tag alla lista di risorse gia' letta da AWS."""
    if filter_mode == 'untagged':
        # Le risorse di sistema senza tag non sono un problema: non si mostrano
        # (coerente con il contatore "senza tag" di build_summary).
        return [r for r in resources if not r['tags'] and not r.get('is_system')]
    if filter_mode == 'tagged':
        return [r for r in resources if r['tags']]
    if filter_mode == 'with_key' and tag_key:
        return [r for r in resources if tag_key in r['tags']]
    if filter_mode == 'without_key' and tag_key:
        return [r for r in resources if tag_key not in r['tags']]
    if filter_mode == 'with_key_value' and tag_key:
        return [r for r in resources if r['tags'].get(tag_key) == tag_value]
    return resources


@bp.route('/api/tags/tag-keys')
@api_errors
def get_tag_keys():
    """Elenca le chiavi tag presenti nella region, o in tutte (per i suggerimenti della UI)."""
    profile = current_profile()
    results = run_parallel(region_list(current_region()),
                           lambda r: TagManager(region_name=r, aws_profile=profile).get_tag_keys())
    keys = set()
    for _, res, _ in results:
        keys.update(res or [])
    return jsonify({'tag_keys': sorted(keys)})


@bp.route('/api/tags/tag-values')
@api_errors
def get_tag_values():
    """Elenca i valori di una chiave tag nella region, o in tutte."""
    key = request.args.get('key', '').strip()
    if not key:
        return jsonify({'error': 'parametro key obbligatorio'}), 400
    profile = current_profile()
    results = run_parallel(region_list(current_region()),
                           lambda r: TagManager(region_name=r, aws_profile=profile).get_tag_values(key))
    values = set()
    for _, res, _ in results:
        values.update(res or [])
    return jsonify({'tag_values': sorted(values)})


@bp.route('/api/tags/regions/refresh', methods=['POST'])
@api_errors
def refresh_regions():
    """Rilegge da AWS le region abilitate e le salva in config.json (tendine region)."""
    region = current_region()
    if region == ALL:
        region = load_config()['default_region']
    regions = TagManager(region_name=region, aws_profile=current_profile()).list_regions()
    save_config_value('regions', regions)
    return jsonify({'message': f'Salvate {len(regions)} region in config.json', 'regions': regions})


# ----------------------------------------------------------------------
# API di scrittura
# ----------------------------------------------------------------------

def arns_by_region(data):
    """
    Raggruppa gli ARN per region. Con "Tutte" la pagina manda la region di ogni risorsa
    ({arn: region}); se manca si usa quella dell'ARN o la region scelta.
    """
    region = current_region()
    per_arn = data.get('regions') or {}
    groups = {}
    for arn in data.get('arns', []):
        r = per_arn.get(arn) or (region if region != ALL else '') or parse_arn(arn)['region'] \
            or load_config()['default_region']
        groups.setdefault(r, []).append(arn)
    return groups


def apply_by_region(data, operation):
    """Esegue operation(manager, arns) per ogni region coinvolta e unisce gli esiti."""
    profile = current_profile()
    result = {'succeeded': [], 'failed': {}, 'failed_details': {}}
    for r, arns in arns_by_region(data).items():
        esito = operation(TagManager(region_name=r, aws_profile=profile), arns)
        result['succeeded'] += esito['succeeded']
        result['failed'].update(esito['failed'])
        result['failed_details'].update(esito['failed_details'])
        invalidate_cache(profile, r)
    return result


@bp.route('/api/tags/add', methods=['POST'])
@api_errors
def add_tags():
    """
    Aggiunge o aggiorna i tag su una o piu' risorse.

    Body: {region, profile, arns: [...], regions: {arn: region}, tags: {chiave: valore}}
    """
    data = request.json or {}
    tags = data.get('tags', {})
    if not data.get('arns') or not tags:
        return jsonify({'error': 'arns e tags sono obbligatori'}), 400
    result = apply_by_region(data, lambda manager, arns: manager.tag_resources(arns, tags))
    return jsonify({
        'message': f"{len(result['succeeded'])} risorse aggiornate, {len(result['failed'])} errori",
        **result
    })


@bp.route('/api/tags/remove', methods=['POST'])
@api_errors
def remove_tags():
    """
    Rimuove una o piu' chiavi tag da una o piu' risorse.

    Body: {region, profile, arns: [...], regions: {arn: region}, tag_keys: [...]}
    """
    data = request.json or {}
    tag_keys = data.get('tag_keys', [])
    if not data.get('arns') or not tag_keys:
        return jsonify({'error': 'arns e tag_keys sono obbligatori'}), 400
    result = apply_by_region(data, lambda manager, arns: manager.untag_resources(arns, tag_keys))
    return jsonify({
        'message': f"{len(result['succeeded'])} risorse aggiornate, {len(result['failed'])} errori",
        **result
    })

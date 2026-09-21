"""
TagManager - gestione dei tag delle risorse AWS con Flask e Bootstrap.

Versione web del comando:
    aws resourcegroupstaggingapi get-resources --region "$R"

Funzionalita':
    - selezione della region da una lista parametrica (config.json / AWS_REGIONS)
    - tabella di tutte le risorse della region con tutti i dati e i tag
    - due sorgenti dati: la Tagging API (che vede solo le risorse gia' taggate
      almeno una volta) e AWS Resource Explorer (che le vede tutte), unite di default
    - filtri: senza tag, con tag, con una chiave specifica, con chiave=valore,
      senza una chiave specifica, per servizio e per testo libero
    - aggiunta e rimozione dei tag, sulla singola risorsa o in massa

Per eseguirlo:
    - installare python3 e pip3
    - installare le librerie con il requirements.txt
        pip3 install -r requirements.txt
    - configurare le credenziali AWS (~/.aws/credentials o variabili d'ambiente)
    - lanciare lo script:
        python3 app.py
    - aprire il browser alla pagina:
        http://localhost:5002

Permessi IAM necessari:
    tag:GetResources, tag:GetTagKeys, tag:GetTagValues,
    tag:TagResources, tag:UntagResources, ec2:DescribeRegions,
    resource-explorer-2:GetDefaultView, resource-explorer-2:Search
"""

import json
import logging
import os
import time
from functools import wraps
from pathlib import Path

import boto3
from flask import Flask, jsonify, render_template, request

from tag_manager import TagManager

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).parent / 'config.json'

# Cache in memoria delle risorse gia' lette: la get_resources su account grandi
# e' lenta, quindi il risultato viene riusato finche' non si chiede il refresh
# o non scade (CACHE_TTL). Ogni voce e' {'data': {...}, 'at': timestamp}.
CACHE_TTL = 3600  # secondi
_cache = {}


def cache_get(key):
    """Ritorna (dati, timestamp) se la voce esiste e non e' scaduta, altrimenti (None, None)."""
    voce = _cache.get(key)
    if not voce or time.time() - voce['at'] > CACHE_TTL:
        _cache.pop(key, None)
        return None, None
    return voce['data'], voce['at']


def cache_set(key, data):
    """Salva la voce e ritorna (dati, timestamp) come cache_get."""
    _cache[key] = {'data': data, 'at': time.time()}
    return data, _cache[key]['at']


# ----------------------------------------------------------------------
# Configurazione
# ----------------------------------------------------------------------

def load_config():
    """
    Legge la lista parametrica delle region da config.json.

    La variabile d'ambiente AWS_REGIONS (es. "eu-west-1,us-east-1") ha priorita'
    sul file, cosi' come AWS_REGION e AWS_PROFILE per i valori di default.
    """
    config = {'default_region': 'eu-central-1', 'default_profile': 'default',
              'regions': ['eu-central-1', 'eu-west-1', 'us-east-1'], 'suggested_tag_keys': [],
              'suggested_tags': {}}

    if CONFIG_FILE.exists():
        try:
            config.update(json.loads(CONFIG_FILE.read_text()))
        except json.JSONDecodeError as e:
            logger.error(f"config.json non valido, uso i default: {e}")

    if os.getenv('AWS_REGIONS'):
        config['regions'] = [r.strip() for r in os.getenv('AWS_REGIONS').split(',') if r.strip()]
    config['default_region'] = os.getenv('AWS_REGION', config['default_region'])
    config['default_profile'] = os.getenv('AWS_PROFILE', config['default_profile'])

    if config['default_region'] not in config['regions']:
        config['regions'].insert(0, config['default_region'])

    return config


def save_regions(regions):
    """Riscrive la lista delle region dentro config.json mantenendo il resto."""
    config = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
    config['regions'] = regions
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + '\n')


def list_profiles():
    """Elenca i profili AWS configurati sulla macchina."""
    try:
        profiles = boto3.Session().available_profiles
        return profiles if profiles else ['default']
    except Exception as e:
        logger.warning(f"Impossibile leggere i profili AWS: {e}")
        return ['default']


def get_manager():
    """Crea il TagManager con region e profilo indicati nella richiesta."""
    config = load_config()
    data = request.json if request.method == 'POST' and request.is_json else {}
    region = request.args.get('region') or data.get('region') or config['default_region']
    profile = request.args.get('profile') or data.get('profile') or config['default_profile']
    return TagManager(region_name=region, aws_profile=profile), region, profile


def invalidate_cache(profile, region):
    """Svuota la cache di quella coppia profilo/region per tutte le sorgenti dati."""
    for chiave in [k for k in _cache if k.startswith(f"{profile}|{region}|")]:
        del _cache[chiave]


def handle_aws_errors(f):
    """Traduce qualsiasi errore AWS in una risposta JSON leggibile dalla pagina."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Errore AWS in {f.__name__}: {e}")
            return jsonify({'error': str(e)}), 500
    return decorated_function


# ----------------------------------------------------------------------
# Pagina
# ----------------------------------------------------------------------

@app.route('/')
def index():
    """Pagina principale."""
    config = load_config()
    suggested_tags = config.get('suggested_tags', {})
    # Per la datalist dei suggerimenti, servono solo le chiavi
    suggested_tag_keys = list(suggested_tags.keys()) if isinstance(suggested_tags, dict) else config.get('suggested_tag_keys', [])
    compliant_tags = config.get('compliant_tags', {})
    return render_template('index.html',
                           regions=config['regions'],
                           profiles=list_profiles(),
                           default_region=config['default_region'],
                           default_profile=config['default_profile'],
                           suggested_tag_keys=suggested_tag_keys,
                           suggested_tags=suggested_tags,
                           compliant_tags=compliant_tags)


@app.route('/report')
def report_page():
    """Pagina report aggregata su tutte le region."""
    config = load_config()
    suggested_tags = config.get('suggested_tags', {})
    # Per la datalist dei suggerimenti, servono solo le chiavi
    suggested_tag_keys = list(suggested_tags.keys()) if isinstance(suggested_tags, dict) else config.get('suggested_tag_keys', [])
    return render_template('report.html',
                           regions=config['regions'],
                           suggested_tag_keys=suggested_tag_keys,
                           suggested_tags=suggested_tags)


@app.route('/api/report/resources')
@handle_aws_errors
def api_report_resources():
    """Ritorna le risorse aggregate su tutte le region configurate.

    Query params:
        profile: profilo AWS (opzionale)
        refresh: 1 per ignorare la cache
    """
    config = load_config()
    profile = request.args.get('profile') or config['default_profile']
    refresh = request.args.get('refresh') == '1'

    all_resources = []
    all_warnings = []
    # Basta una region servita dalla cache perche' il report sia "in cache";
    # come data si riporta la piu' vecchia tra le region in cache.
    any_cached = False
    oldest_at = None

    for region in config['regions']:
        manager = TagManager(region_name=region, aws_profile=profile)
        cache_key = f"{profile}|{region}|both"
        dati, cached_at = (None, None) if refresh else cache_get(cache_key)
        if dati is None:
            dati, cached_at = cache_set(cache_key, manager.get_all_resources())
        else:
            any_cached = True
            oldest_at = cached_at if oldest_at is None else min(oldest_at, cached_at)
        for r in dati['resources']:
            # Assicura il campo region e mantiene l'origine
            r['region'] = r.get('region') or region
            all_resources.append(r)
        if dati.get('warnings'):
            all_warnings.extend([f"{region}: {w}" for w in dati.get('warnings', [])])

    # Ordina per region, service, tipo, nome
    all_resources.sort(key=lambda r: (r.get('region', ''), r.get('service', ''), r.get('resource_type', ''), r.get('name', '')))

    return jsonify({
        'regions': config['regions'],
        'profile': profile,
        'resources': all_resources,
        'warnings': all_warnings,
        'total': len(all_resources),
        'cached': any_cached,
        'cached_at': oldest_at,
        'cache_ttl': CACHE_TTL,
    })


# ----------------------------------------------------------------------
# API di lettura
# ----------------------------------------------------------------------

@app.route('/api/resources')
@handle_aws_errors
def get_resources():
    """
    Elenca le risorse della region applicando il filtro richiesto.

    Parametri:
        region, profile
        source: both | tagging | explorer (sorgente dei dati, vedi TagManager)
        filter_mode: all | untagged | tagged | with_key | with_key_value | without_key
        tag_key, tag_value: usati dai filtri sui tag
        refresh: 1 per ignorare la cache e rileggere da AWS
    """
    manager, region, profile = get_manager()
    source = request.args.get('source', 'both')
    filter_mode = request.args.get('filter_mode', 'all')
    tag_key = request.args.get('tag_key', '').strip()
    tag_value = request.args.get('tag_value', '').strip()
    refresh = request.args.get('refresh') == '1'

    cache_key = f"{profile}|{region}|{source}"
    dati, cached_at = (None, None) if refresh else cache_get(cache_key)
    from_cache = dati is not None
    if not from_cache:
        # Si leggono sempre tutte le risorse (comprese quelle senza tag) e si
        # filtra dopo: e' l'unico modo per poter mostrare anche le "untagged".
        dati, cached_at = cache_set(cache_key, manager.get_all_resources(source))
    resources = dati['resources']

    filtered = apply_filter(resources, filter_mode, tag_key, tag_value)

    return jsonify({
        'region': region,
        'profile': profile,
        'source': source,
        'filter_mode': filter_mode,
        'resources': filtered,
        'summary': TagManager.build_summary(resources),
        'filtered_count': len(filtered),
        'warnings': dati['warnings'],
        'cached': from_cache,
        'cached_at': cached_at,
        'cache_ttl': CACHE_TTL,
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


@app.route('/api/tag-keys')
@handle_aws_errors
def get_tag_keys():
    """Elenca le chiavi tag presenti nella region (per i suggerimenti della UI)."""
    manager, _, _ = get_manager()
    return jsonify({'tag_keys': manager.get_tag_keys()})


@app.route('/api/tag-values')
@handle_aws_errors
def get_tag_values():
    """Elenca i valori di una chiave tag nella region."""
    manager, _, _ = get_manager()
    key = request.args.get('key', '').strip()
    if not key:
        return jsonify({'error': 'parametro key obbligatorio'}), 400
    return jsonify({'tag_values': manager.get_tag_values(key)})


@app.route('/api/regions/refresh', methods=['POST'])
@handle_aws_errors
def refresh_regions():
    """Rilegge da AWS le region abilitate e le salva in config.json."""
    manager, _, _ = get_manager()
    regions = manager.list_regions()
    save_regions(regions)
    return jsonify({'message': f'Salvate {len(regions)} region in config.json', 'regions': regions})


# ----------------------------------------------------------------------
# API di scrittura
# ----------------------------------------------------------------------

@app.route('/api/tags/add', methods=['POST'])
@handle_aws_errors
def add_tags():
    """
    Aggiunge o aggiorna i tag su una o piu' risorse.

    Body: {region, profile, arns: [...], tags: {chiave: valore}}
    """
    manager, region, profile = get_manager()
    data = request.json or {}
    arns = data.get('arns', [])
    tags = data.get('tags', {})

    if not arns or not tags:
        return jsonify({'error': 'arns e tags sono obbligatori'}), 400

    result = manager.tag_resources(arns, tags)
    invalidate_cache(profile, region)
    return jsonify({
        'message': f"{len(result['succeeded'])} risorse aggiornate, {len(result['failed'])} errori",
        **result
    })


@app.route('/api/tags/remove', methods=['POST'])
@handle_aws_errors
def remove_tags():
    """
    Rimuove una o piu' chiavi tag da una o piu' risorse.

    Body: {region, profile, arns: [...], tag_keys: [...]}
    """
    manager, region, profile = get_manager()
    data = request.json or {}
    arns = data.get('arns', [])
    tag_keys = data.get('tag_keys', [])

    if not arns or not tag_keys:
        return jsonify({'error': 'arns e tag_keys sono obbligatori'}), 400

    result = manager.untag_resources(arns, tag_keys)
    invalidate_cache(profile, region)
    return jsonify({
        'message': f"{len(result['succeeded'])} risorse aggiornate, {len(result['failed'])} errori",
        **result
    })


@app.route('/api/config/suggested-tags', methods=['POST'])
def save_suggested_tags():
    """
    Salva i tag consigliati nel config.json.
    
    Body: {suggested_tags: {tagName: value, ...}}
    I tag con valore vuoto non vengono salvati (rimossi se presenti).
    """
    data = request.json or {}
    suggested_tags = data.get('suggested_tags', {})
    
    if not isinstance(suggested_tags, dict):
        return jsonify({'error': 'suggested_tags deve essere un dizionario'}), 400
    
    try:
        config = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
        
        # Filtra i tag: mantieni solo quelli con valore non vuoto
        filtered_tags = {k: v for k, v in suggested_tags.items() if v and v.strip()}
        
        config['suggested_tags'] = filtered_tags
        CONFIG_FILE.write_text(json.dumps(config, indent=2) + '\n')
        logger.info(f"Salvati {len(filtered_tags)} tag consigliati in config.json")
        return jsonify({'message': f"Salvati {len(filtered_tags)} tag consigliati"})
    except Exception as e:
        logger.error(f"Errore nel salvataggio dei suggested tags: {e}")
        return jsonify({'error': f"Errore nel salvataggio: {e}"}), 500


@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Risorsa non trovata'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Errore interno del server'}), 500


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)

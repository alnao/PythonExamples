"""
Parti comuni dell'AlNao AWS Manager.

    - configurazione unica (config.json), con le variabili d'ambiente che hanno la precedenza
    - profilo e region scelti nella pagina: stanno nella sessione Flask, ma ogni API
      accetta anche i parametri profile e region (per le operazioni su una risorsa di una
      region precisa quando nella pagina e' scelto "Tutte")
    - sessioni boto3 e chiamate in parallelo sulle region
    - serializzazione JSON delle risposte di boto3 (date, Decimal di DynamoDB...)
"""

import copy
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from decimal import Decimal
from functools import wraps
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from flask import jsonify, request, session
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / 'config.json'

# Valore delle tendine region che significa "tutte le region della lista"
ALL = '__all__'

# Region usata per i servizi globali (S3, CloudFront, IAM, Route 53)
GLOBAL_REGION = 'us-east-1'

# Valori di default, sovrascritti da config.json: le sezioni di un tool (dizionari)
# vengono unite chiave per chiave, cosi' un parametro nuovo ha sempre un valore
DEFAULTS = {
    'port': 5042,
    'default_profile': 'default',
    'default_region': 'eu-central-1',
    'regions': ['eu-central-1', 'eu-west-1', 'us-east-1'],
    'max_workers': 8,
    'suggested_tags': {},
    'compliant_tags': {'sets': []},
    'resources_skipped': {'entries': []},
    'tag_manager': {
        'required_tags': ['Project', 'Name', 'Environment', 'ManagedBy'],
        'prefix_match_keys': ['Project'],
        'cache_ttl': 3600,
        'page_size': 50,
    },
    'cost_explorer': {
        'default_months': 1,
        'default_metric': 'UnblendedCost',
        'default_group': 'TAG:Project',
        'prefix_match_keys': ['Project'],
        'cur_service_names': {},
        'service_aliases': {},
    },
    'panoramic': {
        'main_services': ['vpc', 'ec2', 'rds', 's3', 'cloudfront', 'lambda', 'dynamodb',
                          'apigateway', 'sqs', 'sns'],
    },
    'manager': {
        'max_upload_mb': 10,
        'list_limit': 500,
        'logs_limit': 100,
    },
}
SECTIONS = ('tag_manager', 'cost_explorer', 'panoramic', 'manager')


# ----------------------------------------------------------------------
# Configurazione
# ----------------------------------------------------------------------

def load_config():
    """
    Legge config.json (a ogni chiamata: le modifiche valgono senza riavviare).

    AWS_REGIONS (es. "eu-west-1,us-east-1") sostituisce la lista delle region,
    AWS_REGION e AWS_PROFILE i valori di default.
    """
    config = copy.deepcopy(DEFAULTS)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError as e:
            logger.error(f"config.json non valido, uso i default: {e}")
            data = {}
        for key, value in data.items():
            if key in SECTIONS and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value

    if os.getenv('AWS_REGIONS'):
        config['regions'] = [r.strip() for r in os.getenv('AWS_REGIONS').split(',') if r.strip()]
    config['default_region'] = os.getenv('AWS_REGION', config['default_region'])
    config['default_profile'] = os.getenv('AWS_PROFILE', config['default_profile'])
    if config['default_region'] not in config['regions']:
        config['regions'].insert(0, config['default_region'])
    return config


def save_config_value(key, value):
    """Riscrive una chiave di primo livello di config.json mantenendo il resto."""
    data = json.loads(CONFIG_FILE.read_text()) if CONFIG_FILE.exists() else {}
    data[key] = value
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def list_profiles():
    """Profili AWS configurati sulla macchina."""
    try:
        profiles = boto3.Session().available_profiles
        return profiles if profiles else ['default']
    except Exception as e:
        logger.warning(f"Impossibile leggere i profili AWS: {e}")
        return ['default']


# ----------------------------------------------------------------------
# Profilo e region della richiesta
# ----------------------------------------------------------------------

def _request_value(name):
    """Parametro dalla query string, da un form o dal corpo JSON della richiesta."""
    value = request.args.get(name)
    if not value and request.form:
        value = request.form.get(name)
    if not value:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            value = data.get(name)
    return value or None


def current_profile():
    """Profilo della richiesta: parametro 'profile', altrimenti quello scelto nella navbar."""
    return _request_value('profile') or session.get('profile') or load_config()['default_profile']


def current_region(allow_all=True):
    """
    Region della richiesta: parametro 'region', altrimenti quella scelta nella pagina.
    Con allow_all=False "Tutte" non e' accettato (operazioni su una region precisa).
    """
    region = _request_value('region') or session.get('region') or load_config()['default_region']
    if region == ALL and not allow_all:
        raise ValueError('Questa operazione vale per una sola region: sceglierne una al posto di "Tutte"')
    return region


def region_list(region):
    """Le region su cui lavorare: tutte quelle della lista con ALL, altrimenti quella indicata."""
    return list(load_config()['regions']) if region == ALL else [region]


# ----------------------------------------------------------------------
# boto3
# ----------------------------------------------------------------------

def aws_session(profile=None, region=None):
    """
    Sessione boto3 per profilo e region. Con il profilo 'default' non si passa il nome,
    cosi' valgono anche le credenziali nelle variabili d'ambiente.
    Ogni thread deve usare la sua sessione: le sessioni boto3 non sono thread-safe.
    """
    if profile and profile != 'default':
        return boto3.Session(profile_name=profile, region_name=region)
    return boto3.Session(region_name=region)


def error_message(e):
    """Testo leggibile di un errore AWS."""
    if isinstance(e, ClientError):
        err = e.response.get('Error', {})
        return f"{err.get('Code', 'Errore')}: {err.get('Message', str(e))}"
    return str(e)


def run_parallel(items, fn, max_workers=None):
    """
    Esegue fn(item) per ogni elemento in parallelo (tipicamente una chiamata per region).
    Ritorna [(item, risultato, errore)] nello stesso ordine: un errore su un elemento
    non ferma gli altri.
    """
    items = list(items)
    if not items:
        return []
    workers = max_workers or int(load_config().get('max_workers', 8))

    def safe(item):
        try:
            return item, fn(item), None
        except Exception as e:
            logger.warning(f"Errore su {item}: {e}")
            return item, None, error_message(e)

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(items)))) as executor:
        return list(executor.map(safe, items))


def api_errors(f):
    """Traduce qualsiasi errore in una risposta JSON leggibile dalla pagina."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except HTTPException:
            raise
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Errore in {f.__name__}: {e}")
            return jsonify({'error': error_message(e)}), 500
    return decorated_function


class JsonProvider(DefaultJSONProvider):
    """JSON delle risposte: date ISO, Decimal di DynamoDB come numeri, chiavi nell'ordine dato."""

    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return int(o) if o.is_finite() and o == o.to_integral_value() else float(o)
        if isinstance(o, (set, frozenset)):
            return list(o)
        if isinstance(o, (bytes, bytearray)):
            return o.decode('utf-8', errors='replace')
        return DefaultJSONProvider.default(o)

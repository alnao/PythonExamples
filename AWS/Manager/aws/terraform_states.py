"""
Risorse gestite da Terraform, lette dagli state salvati su S3 (backend s3).

Per ogni bucket si elencano i file che finiscono con uno dei suffissi configurati
(.tfstate; i .tfstate.backup restano fuori), si scaricano in parallelo e da ognuno si
tengono solo i campi che servono alla pagina: indirizzo, tipo, nome, id, ARN, region e
tag. Il resto degli attributi non lascia mai il server: gli state contengono spesso
password e chiavi in chiaro.

Formato supportato: state versione 4 (Terraform 0.12 e successivi).

Una cache in memoria per (profilo, bucket, file, ETag) evita di riscaricare uno state
che non e' cambiato.
"""

import json
import logging
import threading

from common import GLOBAL_REGION, aws_session, run_parallel

logger = logging.getLogger(__name__)

_cache = {}
_cache_lock = threading.Lock()

# Attributi che danno il nome leggibile di una risorsa, in ordine di preferenza
NAME_ATTRIBUTES = ('name', 'bucket', 'function_name', 'table_name', 'cluster_name', 'identifier',
                   'domain_name', 'repository_name', 'role_name', 'queue_name', 'topic_name', 'alias')


def _s3(profile):
    # il client segue da solo il redirect verso la region del bucket
    return aws_session(profile, GLOBAL_REGION).client('s3')


def list_states(profile, bucket, suffixes, max_states):
    """File di state del bucket: [{'key', 'size', 'last_modified', 'etag'}] (al massimo max_states)."""
    out, truncated = [], False
    for page in _s3(profile).get_paginator('list_objects_v2').paginate(Bucket=bucket):
        for o in page.get('Contents', []):
            if any(o['Key'].endswith(s) for s in suffixes):
                if len(out) >= max_states:
                    truncated = True
                    break
                out.append({'key': o['Key'], 'size': o['Size'], 'last_modified': o['LastModified'],
                            'etag': o['ETag'].strip('"')})
        if truncated:
            break
    return out, truncated


def _provider(p):
    """'provider["registry.terraform.io/hashicorp/aws"].west' -> 'hashicorp/aws.west'."""
    if not p:
        return ''
    inner = p.split('"')[1] if '"' in p else p
    alias = p.rsplit('].', 1)[1] if '].' in p else ''
    return inner.replace('registry.terraform.io/', '') + (f'.{alias}' if alias else '')


def _tags(attrs):
    """Tag della risorsa: tags_all (con i default_tags del provider), poi tags, poi i blocchi tag."""
    for key in ('tags_all', 'tags'):
        t = attrs.get(key)
        if isinstance(t, dict) and t:
            return {str(k): '' if v is None else str(v) for k, v in t.items()}
    blocks = attrs.get('tag')
    if isinstance(blocks, list):
        return {str(b['key']): str(b.get('value', '')) for b in blocks if isinstance(b, dict) and 'key' in b}
    return {}


def _region(attrs):
    """Region dagli attributi: 'region', l'ARN, la zona; 'global' per un ARN senza region."""
    if isinstance(attrs.get('region'), str) and attrs['region']:
        return attrs['region']
    arn = attrs.get('arn')
    if isinstance(arn, str) and arn.startswith('arn:'):
        parts = arn.split(':')
        if len(parts) > 3:
            return parts[3] or 'global'
    az = attrs.get('availability_zone')
    if isinstance(az, str) and len(az) > 2 and az[-1].isalpha():
        return az[:-1]
    return ''


def _name(attrs, tags):
    for a in NAME_ATTRIBUTES:
        if isinstance(attrs.get(a), str) and attrs[a]:
            return attrs[a]
    return tags.get('Name', '')


def parse_state(text):
    """Riassunto di uno state v4: versione, serial e righe delle risorse (solo i campi sicuri)."""
    state = json.loads(text)
    version = state.get('version')
    if version != 4:
        raise ValueError(f"state versione {version} non supportato (serve la 4, Terraform 0.12+)")
    rows = []
    for r in state.get('resources', []):
        base = '.'.join(x for x in (r.get('module'), 'data' if r.get('mode') == 'data' else '',
                                    r.get('type'), r.get('name')) if x)
        for inst in r.get('instances', []) or [{}]:
            attrs = inst.get('attributes') or {}
            index = inst.get('index_key')
            address = base + ('' if index is None else f'[{json.dumps(index)}]')
            tags = _tags(attrs)
            rows.append({
                'address': address, 'module': r.get('module', ''), 'mode': r.get('mode', 'managed'),
                'type': r.get('type', ''), 'name': _name(attrs, tags), 'id': str(attrs.get('id') or ''),
                'arn': attrs.get('arn') if isinstance(attrs.get('arn'), str) else '',
                'region': _region(attrs), 'provider': _provider(r.get('provider', '')),
                'tags': tags, 'tagged': 'tags' in attrs or 'tags_all' in attrs or 'tag' in attrs,
            })
    return {'terraform_version': state.get('terraform_version', ''), 'serial': state.get('serial'),
            'lineage': state.get('lineage', ''), 'outputs': len(state.get('outputs') or {}), 'rows': rows}


def read_state(profile, bucket, obj):
    """Scarica e riassume uno state; dalla cache se l'ETag non e' cambiato."""
    key = (profile, bucket, obj['key'])
    with _cache_lock:
        hit = _cache.get(key)
    if hit and hit[0] == obj['etag']:
        return hit[1], True
    body = _s3(profile).get_object(Bucket=bucket, Key=obj['key'])['Body'].read()
    summary = parse_state(body)
    with _cache_lock:
        _cache[key] = (obj['etag'], summary)
    return summary, False


def collect(profile, buckets, suffixes, max_states):
    """
    Risorse di tutti gli state dei bucket indicati.

    Ritorna {'buckets': [{'bucket', 'states', 'truncated', 'error'}],
             'states': [{'bucket', 'key', 'last_modified', 'size', 'terraform_version', 'serial',
                         'resources', 'cached', 'error'}],
             'resources': [riga + 'bucket', 'state']}
    """
    listed = run_parallel(buckets, lambda b: list_states(profile, b, suffixes, max_states))
    bucket_info, files = [], []
    for b, res, err in listed:
        if err:
            bucket_info.append({'bucket': b, 'states': 0, 'truncated': False, 'error': err})
            continue
        objs, truncated = res
        bucket_info.append({'bucket': b, 'states': len(objs), 'truncated': truncated, 'error': None})
        files += [(b, o) for o in objs]

    states, resources = [], []
    for (b, o), res, err in run_parallel(files, lambda f: read_state(profile, f[0], f[1])):
        info = {'bucket': b, 'key': o['key'], 'last_modified': o['last_modified'], 'size': o['size']}
        if err:
            states.append({**info, 'error': err, 'resources': 0})
            continue
        summary, cached = res
        states.append({**info, 'terraform_version': summary['terraform_version'], 'serial': summary['serial'],
                       'outputs': summary['outputs'], 'cached': cached, 'error': None,
                       'resources': sum(1 for r in summary['rows'] if r['mode'] == 'managed')})
        resources += [{**r, 'bucket': b, 'state': o['key']} for r in summary['rows']]
    return {'buckets': bucket_info, 'states': states, 'resources': resources}

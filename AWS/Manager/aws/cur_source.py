"""
Sorgente dei costi da AWS Data Exports (CUR 2.0) su S3.

A differenza delle API di Cost Explorer (0,01 $ a richiesta) leggere i file dell'export
e' praticamente gratis: AWS li scrive nel bucket fino a qualche volta al giorno e qui
vengono letti solo quando cambiano (ETag), ridotti a una tabella giornaliera compatta e
tenuti in cache/cur/.

Struttura dei file scritti da Data Exports:
    s3://<bucket>/<prefix>/<export>/data/BILLING_PERIOD=2026-09/<export>-00001.snappy.parquet

Da quella tabella si calcolano le stesse serie che l'app chiede a Cost Explorer (costi per
servizio x tag/dimensione, dettaglio di un servizio per usage type...), con i nomi dei
servizi convertiti in quelli di Cost Explorer, cosi' i mesi letti dall'export e quelli
letti con l'API si possono mettere negli stessi grafici.

Configurazione (variabili d'ambiente, vedi .env.example):
    CUR_S3_BUCKET, CUR_S3_PREFIX, CUR_S3_REGION, CUR_EXPORT_NAME, CUR_AWS_PROFILE, CUR_LIST_TTL
"""

import io
import json
import logging
import os
import re
import threading
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import boto3

from aws.cost_cache import cache_key, month_complete

logger = logging.getLogger(__name__)

# Nomi dei servizi come li restituisce Cost Explorer (dimensione SERVICE), a partire dal
# line_item_product_code dell'export. Per i codici non elencati si usa il product_name del
# prodotto; si possono aggiungere o correggere voci in config.json (cur_service_names).
SERVICE_NAMES = {
    'AmazonApiGateway': 'Amazon API Gateway',
    'AmazonCloudFront': 'Amazon CloudFront',
    'AmazonCloudWatch': 'AmazonCloudWatch',
    'AmazonDynamoDB': 'Amazon DynamoDB',
    'AmazonECR': 'Amazon EC2 Container Registry (ECR)',
    'AmazonECS': 'Amazon Elastic Container Service',
    'AmazonEFS': 'Amazon Elastic File System',
    'AmazonEKS': 'Amazon Elastic Kubernetes Service',
    'AmazonElastiCache': 'Amazon ElastiCache',
    'AmazonMemoryDB': 'Amazon MemoryDB',
    'AmazonRDS': 'Amazon Relational Database Service',
    'AmazonRekognition': 'Amazon Rekognition',
    'AmazonRoute53': 'Amazon Route 53',
    'AmazonS3': 'Amazon Simple Storage Service',
    'AmazonSNS': 'Amazon Simple Notification Service',
    'AmazonStates': 'AWS Step Functions',
    'AmazonTextract': 'Amazon Textract',
    'AmazonVPC': 'Amazon Virtual Private Cloud',
    'AWSCertificateManager': 'AWS Certificate Manager',
    'AWSCloudFormation': 'AWS CloudFormation',
    'AWSCloudShell': 'AWS CloudShell',
    'AWSCloudTrail': 'AWS CloudTrail',
    'AWSConfig': 'AWS Config',
    'AWSELB': 'Amazon Elastic Load Balancing',
    'AWSEvents': 'CloudWatch Events',
    'AWSGlue': 'AWS Glue',
    'AWSLambda': 'AWS Lambda',
    'AWSQueueService': 'Amazon Simple Queue Service',
    'AWSSecretsManager': 'AWS Secrets Manager',
    'AWSServiceCatalog': 'AWS Service Catalog',
    'AWSSystemsManager': 'AWS Systems Manager',
    'AWSXRay': 'AWS X-Ray',
    'awskms': 'AWS Key Management Service',
}

# Famiglie di prodotto che Cost Explorer mette in "EC2 - Compute"; il resto di AmazonEC2
# (dischi EBS, snapshot, NAT, trasferimento dati...) finisce in "EC2 - Other"
EC2_COMPUTE_FAMILIES = {'Compute Instance', 'Compute Instance (bare metal)', 'Dedicated Host'}

# Tipi di riga legati a Savings Plans e Reserved Instances: con questi il costo
# ammortizzato va calcolato diversamente e l'app lascia la metrica a Cost Explorer
AMORTIZATION_TYPES = {'SavingsPlanCoveredUsage', 'SavingsPlanNegation', 'SavingsPlanRecurringFee',
                      'SavingsPlanUpfrontFee', 'DiscountedUsage', 'RIFee'}

# Colonne della tabella giornaliera ridotta (una riga per combinazione, importi sommati)
FACT_COLUMNS = ['day', 'service', 'usage_type', 'operation', 'region', 'record_type',
                'account', 'tags', 'unblended', 'net_unblended', 'blended']

# Da dimensione (dell'app) a colonna della tabella
DIMENSION_COLUMNS = {
    'SERVICE': 'service', 'USAGE_TYPE': 'usage_type', 'OPERATION': 'operation',
    'REGION': 'region', 'RECORD_TYPE': 'record_type', 'LINKED_ACCOUNT': 'account',
}

METRIC_COLUMNS = {'UnblendedCost': 'unblended', 'NetUnblendedCost': 'net_unblended',
                  'BlendedCost': 'blended', 'AmortizedCost': 'unblended',
                  'NetAmortizedCost': 'net_unblended'}

READ_COLUMNS = ['line_item_usage_start_date', 'line_item_product_code', 'line_item_usage_type',
                'line_item_operation', 'line_item_line_item_type', 'line_item_unblended_cost',
                'line_item_net_unblended_cost', 'line_item_blended_cost', 'line_item_usage_account_id',
                'product_region_code', 'product_product_family', 'product', 'resource_tags', 'tags',
                'bill_invoice_id']


def _load_env_file(path: Path):
    """Legge un file .env (CHIAVE=valore) senza sovrascrivere le variabili gia' impostate."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _user_tags(raw) -> Dict[str, str]:
    """
    Tag utente dalla colonna resource_tags (mappa). Le chiavi arrivano normalizzate dal
    CUR 2.0 ('user_project', 'user_cost_center' per CostCenter) o come 'user:Project';
    i tag generati da AWS ('aws_...') si scartano.
    """
    if not raw:
        return {}
    items = raw.items() if isinstance(raw, dict) else raw   # pyarrow: lista di coppie
    out = {}
    for k, v in items:
        if k is None or v in (None, ''):
            continue
        for p in ('user_', 'user:'):
            if k.startswith(p):
                out[k[len(p):]] = v
                break
    return out


def _norm_key(k: str) -> str:
    """Chiave di tag confrontabile: CostCenter, cost_center e cost-center diventano costcenter."""
    return re.sub(r'[^0-9a-z]', '', k.lower())


def _tag_value(tags_json: str, key: str) -> str:
    """
    Valore di un tag in una riga ('' se manca). Il CUR 2.0 normalizza le chiavi
    (CostCenter -> cost_center): si confrontano senza maiuscole ne' separatori.
    """
    if not tags_json:
        return ''
    tags = json.loads(tags_json)
    if key in tags:
        return tags[key]
    want = _norm_key(key)
    return next((v for k, v in tags.items() if _norm_key(k) == want), '')


def _map_get(raw, *keys):
    if not raw:
        return None
    d = dict(raw) if not isinstance(raw, dict) else raw
    for k in keys:
        if d.get(k):
            return d[k]
    return None


class CurSource:
    """Costi dai file del Data Export su S3, con cache locale dei mesi gia' elaborati."""

    def __init__(self, cache_dir: Path, env_file: Optional[Path] = None, service_names: Optional[Dict] = None):
        if env_file:
            _load_env_file(env_file)
        self.bucket = os.getenv('CUR_S3_BUCKET', '').strip()
        self.prefix = os.getenv('CUR_S3_PREFIX', '').strip().strip('/')
        self.region = os.getenv('CUR_S3_REGION', '').strip() or None
        self.export_name = os.getenv('CUR_EXPORT_NAME', '').strip()
        self.profile = os.getenv('CUR_AWS_PROFILE', '').strip() or None
        self.list_ttl = int(os.getenv('CUR_LIST_TTL', '600'))
        self.dir = cache_dir / 'cur' / cache_key({'b': self.bucket, 'p': self.prefix, 'e': self.export_name})[:12]
        self.service_names = {**SERVICE_NAMES, **(service_names or {})}
        self._listing = None        # {mese: {'files': [...], 'last_modified': ts}}
        self._listed_at = 0.0
        self._error = None
        self._lock = threading.Lock()
        self._build_lock = threading.Lock()   # un mese si elabora una volta sola
        self._memo = {}             # mese -> (firma dei file, tabella)

    @property
    def enabled(self) -> bool:
        return bool(self.bucket)

    # ------------------------------------------------------------------
    # S3
    # ------------------------------------------------------------------

    def _s3(self, profile: Optional[str]):
        session = boto3.Session(profile_name=self.profile or profile or None)
        return session.client('s3', region_name=self.region)

    def listing(self, profile: Optional[str] = None, force: bool = False) -> Dict:
        """
        File Parquet dell'export per mese. L'elenco viene riletto al massimo ogni
        CUR_LIST_TTL secondi (una LIST su S3 costa frazioni di centesimo).
        """
        if not self.enabled:
            return {}
        with self._lock:
            if not force and self._listing is not None and time.time() - self._listed_at < self.list_ttl:
                return self._listing
            months = {}
            try:
                s3 = self._s3(profile)
                paginator = s3.get_paginator('list_objects_v2')
                base = f"{self.prefix}/" if self.prefix else ''
                for page in paginator.paginate(Bucket=self.bucket, Prefix=base):
                    for obj in page.get('Contents', []):
                        key = obj['Key']
                        if not key.endswith('.parquet') or '/data/' not in key or 'BILLING_PERIOD=' not in key:
                            continue
                        if self.export_name and f"/{self.export_name}/" not in f"/{key}":
                            continue
                        month = key.split('BILLING_PERIOD=', 1)[1][:7]
                        m = months.setdefault(month, {'files': [], 'last_modified': 0.0, 'size': 0})
                        ts = obj['LastModified'].timestamp()
                        m['files'].append({'key': key, 'etag': obj['ETag'].strip('"'), 'size': obj['Size'],
                                           'last_modified': ts})
                        m['last_modified'] = max(m['last_modified'], ts)
                        m['size'] += obj['Size']
                self._error = None
            except Exception as e:   # permessi, bucket sbagliato, rete: l'app continua con l'API
                logger.warning(f"Data Export: impossibile leggere s3://{self.bucket}/{self.prefix}: {e}")
                self._error = str(e)
                months = self._listing or {}
            self._listing = months
            self._listed_at = time.time()
            return months

    # ------------------------------------------------------------------
    # Elaborazione di un mese
    # ------------------------------------------------------------------

    def month_table(self, month: str, profile: Optional[str] = None) -> Optional[Dict]:
        """
        Tabella giornaliera del mese, oppure None se l'export non ha quel mese.
        Si riscarica solo quando cambiano i file (ETag).
        """
        info = self.listing(profile).get(month)
        if not info:
            return None
        signature = sorted(f['etag'] for f in info['files'])
        memo = self._memo.get(month)
        if memo and memo[0] == signature:
            return memo[1]
        with self._build_lock:
            memo = self._memo.get(month)
            if memo and memo[0] == signature:
                return memo[1]
            return self._load_or_build(month, info, signature, profile)

    def _load_or_build(self, month: str, info: Dict, signature: List[str], profile: Optional[str]) -> Dict:
        """Tabella dalla cache locale se i file non sono cambiati, altrimenti da S3."""
        path = self.dir / f"{month}.json"
        if path.exists():
            try:
                table = json.loads(path.read_text())
                if table.get('signature') == signature:
                    self._memo[month] = (signature, table)
                    return table
            except json.JSONDecodeError:
                pass

        logger.info(f"Data Export: elaboro {month} ({len(info['files'])} file, {info['size'] // 1024} KB)")
        table = self._build_month(month, info, profile)
        table['signature'] = signature
        self.dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(table))
        self._memo[month] = (signature, table)
        return table

    def _build_month(self, month: str, info: Dict, profile: Optional[str]) -> Dict:
        import pyarrow.parquet as pq   # importato qui: serve solo se l'export e' configurato

        s3 = self._s3(profile)
        facts = {}
        record_types = set()
        finalized = False
        unknown_products = set()
        lines = 0
        for f in info['files']:
            body = s3.get_object(Bucket=self.bucket, Key=f['key'])['Body'].read()
            pf = pq.ParquetFile(io.BytesIO(body))
            cols = [c for c in READ_COLUMNS if c in pf.schema_arrow.names]
            for batch in pf.iter_batches(columns=cols, batch_size=20000):
                data = batch.to_pydict()
                n = batch.num_rows
                get = lambda c, i: data[c][i] if c in data else None   # noqa: E731
                for i in range(n):
                    lines += 1
                    start = get('line_item_usage_start_date', i)
                    day = start.strftime('%Y-%m-%d') if start else f"{month}-01"
                    if not day.startswith(month):
                        day = f"{month}-01"
                    code = get('line_item_product_code', i) or ''
                    rtype = get('line_item_line_item_type', i) or ''
                    record_types.add(rtype)
                    if get('bill_invoice_id', i):
                        finalized = True
                    service = self._service_name(code, rtype, get('product_product_family', i),
                                                 get('product', i), unknown_products)
                    tags = _user_tags(get('resource_tags', i)) or _user_tags(get('tags', i))
                    key = (day, service, get('line_item_usage_type', i) or '',
                           get('line_item_operation', i) or '', get('product_region_code', i) or 'global',
                           rtype, get('line_item_usage_account_id', i) or '',
                           json.dumps(tags, sort_keys=True) if tags else '')
                    u = float(get('line_item_unblended_cost', i) or 0)
                    nu = get('line_item_net_unblended_cost', i)
                    b = get('line_item_blended_cost', i)
                    acc = facts.setdefault(key, [0.0, 0.0, 0.0])
                    acc[0] += u
                    acc[1] += float(nu) if nu is not None else u
                    acc[2] += float(b) if b is not None else u
        return {
            'month': month,
            'at': info['last_modified'],
            'files': len(info['files']),
            'size': info['size'],
            'lines': lines,
            'finalized': finalized,
            'amortization_lines': bool(record_types & AMORTIZATION_TYPES),
            'unknown_products': sorted(unknown_products),
            'columns': FACT_COLUMNS,
            'rows': [list(k) + v for k, v in facts.items()],
        }

    def _service_name(self, code, rtype, family, product, unknown) -> str:
        """Nome del servizio come in Cost Explorer."""
        if rtype == 'Tax':
            return 'Tax'
        if code == 'AmazonEC2':
            return 'Amazon Elastic Compute Cloud - Compute' if family in EC2_COMPUTE_FAMILIES else 'EC2 - Other'
        if code in self.service_names:
            return self.service_names[code]
        name = _map_get(product, 'product_name', 'productName', 'ProductName')
        if not name:
            unknown.add(code)
        return name or code or 'Sconosciuto'

    # ------------------------------------------------------------------
    # Interrogazioni (stesso formato di MonthStore)
    # ------------------------------------------------------------------

    def query(self, month: str, profile: Optional[str], granularity: str, metric: str,
              group_by: List[Dict], exclude: bool = False, region: str = '',
              filters: Optional[List[Dict]] = None) -> Optional[Dict]:
        """
        Serie del mese con lo stesso formato delle voci di MonthStore, oppure None se
        l'export non ha il mese o non puo' dare la metrica richiesta.

        group_by: come per Cost Explorer ({'Type': 'DIMENSION'|'TAG', 'Key': ...})
        filters: [{'column' o 'tag': ..., 'values': [...]}] in AND
        """
        table = self.month_table(month, profile)
        if table is None:
            return None
        # con Savings Plans o RI il costo ammortizzato non e' la semplice somma: si lascia a Cost Explorer
        if metric in ('AmortizedCost', 'NetAmortizedCost') and table['amortization_lines']:
            return None
        col = {c: i for i, c in enumerate(table['columns'])}
        mi = col[METRIC_COLUMNS.get(metric, 'unblended')]

        def value(row, g):
            if g['Type'] == 'TAG':
                return _tag_value(row[col['tags']], g['Key'])
            return row[col[DIMENSION_COLUMNS[g['Key']]]]

        def keep(row):
            if exclude and row[col['record_type']] in ('Tax', 'Credit', 'Refund'):
                return False
            if region and row[col['region']] != region:
                return False
            for f in filters or []:
                v = _tag_value(row[col['tags']], f['tag']) if 'tag' in f else row[col[f['column']]]
                if v not in f['values']:
                    return False
            return True

        daily = granularity == 'DAILY'
        sums = {}
        for row in table['rows']:
            if not keep(row):
                continue
            period = row[col['day']] if daily else f"{month}-01"
            key = (period, tuple(value(row, g) for g in group_by))
            sums[key] = sums.get(key, 0.0) + row[mi]

        # i periodi come li restituisce Cost Explorer: ogni giorno fino a oggi, o il mese
        estimated = not table['finalized']
        if daily:
            y, m = map(int, month.split('-'))
            last = min(date(y + (m == 12), m % 12 + 1, 1).toordinal() - 1, date.today().toordinal())
            periods = [date.fromordinal(d).isoformat() for d in range(date(y, m, 1).toordinal(), last + 1)]
        else:
            periods = [f"{month}-01"]
        return {
            'month': month,
            'at': table['at'],
            'complete': month_complete(month, table['at']),
            'estimated': estimated,
            'unit': 'USD',
            'source': 'cur',
            'periods': [{'start': p, 'estimated': estimated} for p in periods],
            'rows': [{'period': p, 'keys': list(k), 'amount': a} for (p, k), a in sorted(sums.items())],
        }

    def status(self, profile: Optional[str] = None, force: bool = False) -> Dict:
        """Stato dell'export per la pagina: configurazione, mesi disponibili, errori."""
        if not self.enabled:
            return {'enabled': False}
        listing = self.listing(profile, force=force)
        months = []
        for m in sorted(listing):
            info = listing[m]
            t = self._memo.get(m, (None, None))[1]
            months.append({
                'month': m, 'files': len(info['files']), 'size': info['size'],
                'last_modified': info['last_modified'],
                'lines': t['lines'] if t else None,
                'finalized': t['finalized'] if t else None,
                'unknown_products': t['unknown_products'] if t else [],
            })
        return {
            'enabled': True, 'bucket': self.bucket, 'prefix': self.prefix, 'region': self.region,
            'export': self.export_name, 'error': self._error, 'checked_at': self._listed_at,
            'list_ttl': self.list_ttl, 'months': months,
        }

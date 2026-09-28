"""
Classe di lettura dei costi AWS tramite le API di Cost Explorer.

Equivalente SDK del comando:
    aws ce get-cost-and-usage --time-period Start=2026-09-17,End=2026-09-24 \\
      --granularity DAILY --metrics UnblendedCost --group-by Type=DIMENSION,Key=USAGE_TYPE

Le API usate sono:
    - get_cost_and_usage         -> costi raggruppati per al massimo 2 dimensioni/tag
    - get_cost_forecast          -> stima dei costi fino a fine mese
    - list_cost_allocation_tags  -> chiavi tag attive (o no) come cost allocation tag

Attenzione: ogni richiesta alle API di Cost Explorer costa 0,01 $ (anche le pagine
successive di una stessa richiesta), per questo la classe conta le chiamate fatte e
l'applicazione tiene in cache i risultati.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import boto3

logger = logging.getLogger(__name__)

# Cost Explorer e' un servizio globale con endpoint unico in us-east-1
CE_REGION = 'us-east-1'

# Costo di una singola richiesta API a Cost Explorer (listino AWS)
COST_PER_API_CALL = 0.01

# Metriche accettate da get_cost_and_usage e nome corrispondente per get_cost_forecast
METRICS = {
    'UnblendedCost': 'UNBLENDED_COST',
    'AmortizedCost': 'AMORTIZED_COST',
    'NetUnblendedCost': 'NET_UNBLENDED_COST',
    'NetAmortizedCost': 'NET_AMORTIZED_COST',
    'BlendedCost': 'BLENDED_COST',
}

# Record type esclusi con l'opzione "escludi tasse, crediti e rimborsi"
EXCLUDED_RECORD_TYPES = ['Tax', 'Credit', 'Refund']


def month_bounds(start_month: str, end_month: str) -> Dict[str, str]:
    """
    Converte un intervallo di mesi 'YYYY-MM' nelle date richieste da Cost Explorer.

    La data di fine per AWS e' esclusiva: si usa il primo giorno del mese successivo,
    ma senza superare domani (per il mese in corso i dati arrivano fino a oggi).
    """
    start = datetime.strptime(start_month, '%Y-%m').date()
    end = datetime.strptime(end_month, '%Y-%m').date()
    if end < start:
        start, end = end, start
    end_excl = date(end.year + (end.month == 12), end.month % 12 + 1, 1)
    end_excl = min(end_excl, date.today() + timedelta(days=1))
    return {'Start': start.isoformat(), 'End': end_excl.isoformat()}


def last_months(n: int) -> Dict[str, str]:
    """Ritorna i mesi 'YYYY-MM' di inizio e fine degli ultimi n mesi (mese corrente compreso)."""
    today = date.today()
    y, m = today.year, today.month - (n - 1)
    while m <= 0:
        m += 12
        y -= 1
    return {'start': f"{y:04d}-{m:02d}", 'end': today.strftime('%Y-%m')}


def build_filter(exclude_record_types: bool = False, region: str = '',
                 extra: Optional[List[Dict]] = None) -> Optional[Dict]:
    """
    Costruisce l'espressione Filter di Cost Explorer combinando le condizioni in AND.

    Args:
        exclude_record_types: se True esclude tasse, crediti e rimborsi (RECORD_TYPE)
        region: se valorizzata limita i costi a quella region (dimensione REGION)
        extra: altre espressioni gia' pronte da mettere in AND
    """
    parts = []
    if exclude_record_types:
        parts.append({'Not': {'Dimensions': {'Key': 'RECORD_TYPE', 'Values': EXCLUDED_RECORD_TYPES}}})
    if region:
        parts.append({'Dimensions': {'Key': 'REGION', 'Values': [region]}})
    parts.extend(extra or [])
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else {'And': parts}


def tag_filter(key: str, values: List[str]) -> Dict:
    """
    Filtro su uno o piu' valori di un tag; il valore vuoto significa "senza quel tag".

    Cost Explorer non permette di mettere ABSENT ed EQUALS nella stessa condizione,
    quindi se servono entrambi le due condizioni vanno in OR.
    """
    named = [v for v in values if v != '']
    absent = {'Tags': {'Key': key, 'MatchOptions': ['ABSENT']}}
    equals = {'Tags': {'Key': key, 'Values': named, 'MatchOptions': ['EQUALS']}}
    if not named:
        return absent
    return {'Or': [absent, equals]} if len(named) < len(values) else equals


def dimension_filter(key: str, values: List[str]) -> Dict:
    return {'Dimensions': {'Key': key, 'Values': values}}


class CostExplorer:
    """Lettura dei costi da AWS Cost Explorer per un profilo AWS."""

    def __init__(self, aws_profile: Optional[str] = None):
        session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
        self.client = session.client('ce', region_name=CE_REGION)
        # Numero di richieste fatte da questa istanza (ognuna costa COST_PER_API_CALL)
        self.api_calls = 0

    # ------------------------------------------------------------------
    # Tag
    # ------------------------------------------------------------------

    def list_cost_allocation_tags(self) -> List[Dict]:
        """
        Elenca le chiavi tag conosciute dal Billing, attive e inattive.

        Solo i tag con stato Active possono essere usati nei raggruppamenti: gli altri
        esistono sulle risorse ma Cost Explorer non li considera.
        """
        tags, token = [], None
        while True:
            kwargs = {'MaxResults': 1000}
            if token:
                kwargs['NextToken'] = token
            resp = self.client.list_cost_allocation_tags(**kwargs)
            self.api_calls += 1
            for t in resp.get('CostAllocationTags', []):
                tags.append({
                    'key': t['TagKey'],
                    'type': t.get('Type', ''),
                    'status': t.get('Status', ''),
                    'last_updated': _iso(t.get('LastUpdatedDate')),
                    'last_used': _iso(t.get('LastUsedDate')),
                })
            token = resp.get('NextToken')
            if not token:
                break
        # prima i tag attivi, poi alfabetico
        tags.sort(key=lambda t: (t['status'] != 'Active', t['key'].lower()))
        return tags

    # ------------------------------------------------------------------
    # Costi
    # ------------------------------------------------------------------

    def get_cost_and_usage(self, time_period: Dict[str, str], granularity: str, metric: str,
                           group_by: List[Dict], filter_expr: Optional[Dict] = None) -> Dict:
        """
        Legge i costi con get_cost_and_usage seguendo tutte le pagine.

        Args:
            time_period: {'Start': 'YYYY-MM-DD', 'End': 'YYYY-MM-DD'} (End esclusivo)
            granularity: MONTHLY | DAILY
            metric: una delle chiavi di METRICS
            group_by: al massimo 2 elementi {'Type': 'DIMENSION'|'TAG', 'Key': ...}
            filter_expr: espressione Filter opzionale (vedi build_filter)

        Returns:
            {'rows': [{'period', 'estimated', 'keys', 'amount', 'unit'}],
             'periods': [{'start', 'end', 'estimated'}], 'unit': 'USD'}
            Le chiavi dei gruppi TAG arrivano come "Chiave$valore": qui viene tolto
            il prefisso, quindi il valore vuoto significa "senza tag".
        """
        if metric not in METRICS:
            raise ValueError(f"Metrica non valida: {metric}")

        kwargs = {
            'TimePeriod': time_period,
            'Granularity': granularity,
            'Metrics': [metric],
        }
        if group_by:
            kwargs['GroupBy'] = group_by[:2]
        if filter_expr:
            kwargs['Filter'] = filter_expr

        tag_positions = [i for i, g in enumerate(group_by[:2]) if g['Type'] == 'TAG']
        rows, periods, unit = [], {}, 'USD'
        token = None
        while True:
            if token:
                kwargs['NextPageToken'] = token
            resp = self.client.get_cost_and_usage(**kwargs)
            self.api_calls += 1
            for result in resp.get('ResultsByTime', []):
                period = result['TimePeriod']['Start']
                periods[period] = {
                    'start': period,
                    'end': result['TimePeriod']['End'],
                    'estimated': bool(result.get('Estimated')),
                }
                if not group_by:
                    m = result.get('Total', {}).get(metric, {})
                    rows.append({'period': period, 'keys': [],
                                 'amount': float(m.get('Amount', 0)), 'unit': m.get('Unit', unit)})
                    continue
                for g in result.get('Groups', []):
                    keys = list(g['Keys'])
                    for i in tag_positions:
                        keys[i] = keys[i].split('$', 1)[1] if '$' in keys[i] else keys[i]
                    m = g['Metrics'][metric]
                    unit = m.get('Unit', unit)
                    rows.append({'period': period, 'keys': keys,
                                 'amount': float(m.get('Amount', 0)), 'unit': unit})
            token = resp.get('NextPageToken')
            if not token:
                break

        return {
            'rows': rows,
            'periods': sorted(periods.values(), key=lambda p: p['start']),
            'unit': unit,
        }

    def get_month_forecast(self, metric: str, filter_expr: Optional[Dict] = None) -> Optional[Dict]:
        """
        Stima dei costi da oggi alla fine del mese corrente.

        Ritorna None quando AWS non ha abbastanza storico per la previsione
        (DataUnavailableException) o quando il mese e' gia' finito.
        """
        today = date.today()
        end = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
        if today >= end:
            return None
        kwargs = {
            'TimePeriod': {'Start': today.isoformat(), 'End': end.isoformat()},
            'Metric': METRICS[metric],
            'Granularity': 'MONTHLY',
            'PredictionIntervalLevel': 80,
        }
        if filter_expr:
            kwargs['Filter'] = filter_expr
        try:
            resp = self.client.get_cost_forecast(**kwargs)
        except self.client.exceptions.DataUnavailableException as e:
            logger.info(f"Previsione non disponibile: {e}")
            return None
        finally:
            self.api_calls += 1
        results = resp.get('ForecastResultsByTime', [{}])
        return {
            'start': kwargs['TimePeriod']['Start'],
            'end': kwargs['TimePeriod']['End'],
            'amount': float(resp['Total']['Amount']),
            'unit': resp['Total'].get('Unit', 'USD'),
            'lower': float(results[0].get('PredictionIntervalLowerBound', 0)) if results else None,
            'upper': float(results[0].get('PredictionIntervalUpperBound', 0)) if results else None,
        }


def _iso(value) -> str:
    """boto3 restituisce datetime per alcuni campi e stringhe per altri."""
    if not value:
        return ''
    return value.isoformat() if hasattr(value, 'isoformat') else str(value)

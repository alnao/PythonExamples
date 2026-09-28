"""
Cache su disco delle risposte di Cost Explorer, senza scadenza.

Ogni richiesta a Cost Explorer costa 0,01 $: quello che e' stato letto una volta non
viene mai buttato ne' riletto da solo. Due forme:

    - richieste singole (elenco dei tag, stima di fine mese):
          cache/<sha1 della richiesta>.json
    - costi e dettagli di un servizio, UN FILE PER MESE:
          cache/<tipo>/<sha1 dei filtri>/<YYYY-MM>.json
      Una richiesta per un periodo legge da AWS solo i mesi che mancano e non tocca
      gli altri: settembre letto a settembre resta valido anche a ottobre.

Un mese letto prima della sua fine e' "incompleto" (complete = False): resta in cache
con la data di lettura e si rilegge solo quando lo chiede l'utente.
"""

import hashlib
import json
import logging
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def cache_key(parts: Dict) -> str:
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def months_between(start: str, end: str) -> List[str]:
    """Mesi 'YYYY-MM' da start a end compresi."""
    if end < start:
        start, end = end, start
    y, m = map(int, start.split('-'))
    out = []
    while f"{y:04d}-{m:02d}" <= end:
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def contiguous_runs(months: List[str]) -> List[List[str]]:
    """Raggruppa i mesi in blocchi consecutivi: ogni blocco e' una sola richiesta ad AWS."""
    runs = []
    for m in sorted(months):
        if runs and months_between(runs[-1][-1], m)[1:2] == [m]:
            runs[-1].append(m)
        else:
            runs.append([m])
    return runs


def month_complete(month: str, at: float) -> bool:
    """Il mese era gia' finito quando e' stato letto?"""
    y, m = map(int, month.split('-'))
    first_next = date(y + (m == 12), m % 12 + 1, 1)
    return datetime.fromtimestamp(at).date() >= first_next


class KeyedCache:
    """Una risposta per file, identificata dai parametri della richiesta."""

    def __init__(self, base: Path):
        self.base = base

    def get(self, parts: Dict):
        """(dati, timestamp) oppure (None, None) se la richiesta non e' in cache."""
        path = self.base / f"{cache_key(parts)}.json"
        if not path.exists():
            return None, None
        try:
            voce = json.loads(path.read_text())
            return voce['data'], voce['at']
        except (json.JSONDecodeError, KeyError):
            return None, None

    def put(self, parts: Dict, data, at: float):
        self.base.mkdir(parents=True, exist_ok=True)
        path = self.base / f"{cache_key(parts)}.json"
        path.write_text(json.dumps({'at': at, 'request': parts, 'data': data}))


class MonthStore:
    """
    Risultati di get_cost_and_usage divisi per mese, per una combinazione di filtri
    (dims: profilo, metrica, raggruppamento, granularita'...).
    """

    def __init__(self, base: Path, kind: str, dims: Dict):
        self.dims = dims
        self.dir = base / kind / cache_key(dims)[:20]

    def get(self, month: str) -> Optional[Dict]:
        path = self.dir / f"{month}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            return None

    def put_result(self, data: Dict, months: List[str], at: float, only_if_newer: bool = False):
        """
        Salva un risultato di CostExplorer.get_cost_and_usage mese per mese.

        data['rows'] e data['periods'] vengono divisi per mese; anche un mese senza
        costi viene salvato (vuoto), cosi' non risulta mancante.
        """
        self.dir.mkdir(parents=True, exist_ok=True)
        # i filtri in chiaro, per chi apre la cartella
        (self.dir / '_filtri.json').write_text(json.dumps(self.dims, indent=2, sort_keys=True))
        for month in months:
            if only_if_newer:
                old = self.get(month)
                if old and old['at'] >= at:
                    continue
            periods = [p for p in data['periods'] if p['start'][:7] == month]
            entry = {
                'month': month,
                'at': at,
                'complete': month_complete(month, at),
                'estimated': any(p['estimated'] for p in periods),
                'unit': data.get('unit', 'USD'),
                'periods': periods,
                'rows': [r for r in data['rows'] if r['period'][:7] == month],
            }
            (self.dir / f"{month}.json").write_text(json.dumps(entry))


def migrate_legacy(base: Path, costs_dims, drill_dims):
    """
    Converte i file della cache precedente (una voce per richiesta, con scadenza) nella
    cache per mese. I dati erano gia' stati pagati: vengono riusati, non riletti.
    I file convertiti vengono spostati in cache/legacy/, non cancellati.

    costs_dims / drill_dims: funzioni request -> dims, le stesse usate dalle API.
    """
    if not base.exists():
        return
    moved = 0
    for f in sorted(base.glob('*.json'), key=lambda p: p.stat().st_mtime):
        try:
            voce = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        req = voce.get('request', {})
        api = req.get('api')
        if api not in ('costs', 'drilldown') or 'period' not in req:
            continue
        start = req['period']['Start'][:7]
        end_day = datetime.strptime(req['period']['End'], '%Y-%m-%d').date() - timedelta(days=1)
        months = months_between(start, end_day.strftime('%Y-%m'))
        dims = costs_dims(req) if api == 'costs' else drill_dims(req)
        MonthStore(base, api, dims).put_result(voce['data'], months, voce['at'], only_if_newer=True)
        legacy = base / 'legacy'
        legacy.mkdir(exist_ok=True)
        shutil.move(str(f), str(legacy / f.name))
        moved += 1
    if moved:
        logger.info(f"Cache: convertiti {moved} file nel formato per mese (originali in cache/legacy)")

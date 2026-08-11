"""
Classe di gestione dei tag delle risorse AWS tramite le API resourcegroupstaggingapi.

Equivalente SDK del comando:
    aws resourcegroupstaggingapi get-resources --region "$R"

Le API usate sono:
    - get_resources    -> elenco risorse taggabili (con e senza tag) della region
    - get_tag_keys     -> tutte le chiavi tag presenti nella region
    - get_tag_values   -> tutti i valori di una chiave nella region
    - tag_resources    -> aggiunta/modifica tag (max 20 ARN per chiamata)
    - untag_resources  -> rimozione tag (max 20 ARN per chiamata)
"""

import logging
import re
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

# Limite imposto da AWS sul numero di ARN per singola chiamata di tag/untag
MAX_ARN_PER_CALL = 20

# Sorgenti dati disponibili per l'elenco delle risorse
SOURCE_TAGGING = 'tagging'    # resourcegroupstaggingapi: solo risorse gia' taggate almeno una volta
SOURCE_EXPLORER = 'explorer'  # resource-explorer-2: tutte le risorse indicizzate
SOURCE_BOTH = 'both'          # unione delle due (default)


def parse_arn(arn: str) -> Dict[str, str]:
    """
    Estrae le informazioni contenute in un ARN.

    Formati gestiti:
        arn:aws:s3:::nome-bucket
        arn:aws:lambda:eu-west-1:123456789012:function:nome-funzione
        arn:aws:ec2:eu-west-1:123456789012:instance/i-0123456789

    Returns:
        Dizionario con partition, service, region, account, resource_type, name
        e resource_type_filter (il formato "servizio:tipo" usato dai filtri AWS)
    """
    info = {
        'partition': '', 'service': '', 'region': '', 'account': '',
        'resource_type': '', 'name': arn, 'resource_type_filter': ''
    }

    parts = arn.split(':', 5)
    if len(parts) < 6 or parts[0] != 'arn':
        return info

    info['partition'] = parts[1]
    info['service'] = parts[2]
    info['region'] = parts[3]
    info['account'] = parts[4]

    resource = parts[5]
    if '/' in resource:
        resource_type, name = resource.split('/', 1)
    elif ':' in resource:
        resource_type, name = resource.split(':', 1)
    else:
        resource_type, name = '', resource

    info['resource_type'] = resource_type
    info['name'] = name
    info['resource_type_filter'] = f"{parts[2]}:{resource_type}" if resource_type else parts[2]
    return info


def check_taggable(arn: str) -> Dict:
    """
    Dice se un ARN e' accettato dalle API di tagging, prima di provarci.

    Non tutte le risorse elencate sono taggabili, e AWS lo comunica solo dopo il
    tentativo con messaggi poco leggibili. Le regole qui sotto sono verificate
    interrogando direttamente le API AWS:

        arn:aws:lambda:...:function:NOME           -> OK
        arn:aws:lambda:...:function:NOME:$LATEST   -> "Tags on function aliases and
                                                       versions are not supported"
        arn:aws:lambda:...:layer:NOME              -> "Unsupported resource type for tagging"
        arn:aws:lambda:...:layer:NOME:2            -> ValidationException sul formato ARN

    Tutto cio' che non rientra in questi casi e' considerato taggabile: se poi AWS
    rifiuta, l'errore viene comunque riportato in chiaro all'utente.

    Returns:
        {'taggable': bool, 'reason': str, 'alternative': str}
        'alternative' contiene l'ARN da usare al suo posto, quando esiste.
    """
    info = parse_arn(arn)
    esito = {'taggable': True, 'reason': '', 'alternative': ''}

    if info['service'] != 'lambda':
        return esito

    if info['resource_type'] == 'layer':
        esito.update({
            'taggable': False,
            'reason': 'I layer Lambda non supportano il tagging '
                      '(AWS: "Unsupported resource type for tagging").',
        })
    elif info['resource_type'] == 'function' and ':' in info['name']:
        # arn:...:function:NOME:$LATEST oppure :1 -> il tag va sulla funzione
        esito.update({
            'taggable': False,
            'reason': 'Versioni e alias delle funzioni Lambda non supportano il tagging: '
                      'il tag va messo sulla funzione.',
            'alternative': arn.rsplit(':', 1)[0],
        })

    return esito


def readable_error(messaggio: str) -> str:
    """
    Rende leggibile un errore di AWS prima di mostrarlo in pagina.

    Le ValidationException sugli ARN contengono l'intera espressione regolare
    accettata dal servizio: informazione inutile per l'utente e lunga righe.
    Il testo completo resta comunque disponibile in 'failed_details'.
    """
    if 'failed to satisfy constraint' in messaggio and 'regular expression pattern' in messaggio:
        valore = re.search(r"Value '([^']*)'", messaggio)
        arn = valore.group(1) if valore else ''
        info = parse_arn(arn)
        dettaglio = check_taggable(arn)['reason']
        return (f"ARN non accettato dalle API di tagging di {info['service'] or 'AWS'}"
                + (f": {dettaglio}" if dettaglio else
                   ' (formato non valido per questo servizio, tipico di versioni, '
                   'alias e sotto-risorse).'))
    return messaggio


class TagManager:
    """
    Gestore dei tag delle risorse AWS di una singola region.
    """

    def __init__(self, region_name: str, aws_profile: Optional[str] = None):
        """
        Inizializza il client resourcegroupstaggingapi.

        Args:
            region_name: region AWS su cui operare
            aws_profile: profilo AWS da usare (opzionale, altrimenti quello di default)
        """
        self.logger = logging.getLogger(__name__)
        self.region_name = region_name
        self.aws_profile = aws_profile

        if aws_profile and aws_profile != 'default':
            session = boto3.Session(profile_name=aws_profile, region_name=region_name)
        else:
            session = boto3.Session(region_name=region_name)

        self.session = session
        self.client = session.client('resourcegroupstaggingapi')

    # ------------------------------------------------------------------
    # Lettura
    # ------------------------------------------------------------------

    def get_resources(self,
                      tag_filters: Optional[List[Dict]] = None,
                      resource_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Elenca tutte le risorse taggabili della region, comprese quelle senza tag.

        Args:
            tag_filters: filtri lato AWS, es. [{'Key': 'Environment', 'Values': ['prod']}]
                         (con Values vuoto filtra per sola presenza della chiave)
            resource_types: filtri sul tipo, es. ['ec2:instance', 's3']

        Returns:
            Lista di dizionari con arn, tags (dict), e i campi estratti dall'ARN
        """
        kwargs = {'ResourcesPerPage': 100}
        if tag_filters:
            kwargs['TagFilters'] = tag_filters
        if resource_types:
            kwargs['ResourceTypeFilters'] = resource_types

        resources = []
        try:
            paginator = self.client.get_paginator('get_resources')
            for page in paginator.paginate(**kwargs):
                for item in page.get('ResourceTagMappingList', []):
                    resources.append(self._format_resource(item))
        except ClientError as e:
            self.logger.error(f"Errore nel recupero delle risorse: {e}")
            raise

        resources.sort(key=lambda r: (r['service'], r['resource_type'], r['name']))
        self.logger.info(f"Trovate {len(resources)} risorse nella region {self.region_name}")
        return resources

    def _format_resource(self, item: Dict) -> Dict:
        """Trasforma un elemento di ResourceTagMappingList nel formato usato dalla UI."""
        arn = item.get('ResourceARN', '')
        tags = {t['Key']: t['Value'] for t in item.get('Tags', [])}
        info = parse_arn(arn)
        return {
            'arn': arn,
            'tags': tags,
            'tag_count': len(tags),
            'service': info['service'],
            'region': info['region'] or self.region_name,
            'account': info['account'],
            'resource_type': info['resource_type'],
            'resource_type_filter': info['resource_type_filter'],
            'name': info['name'],
            'source': SOURCE_TAGGING,
            **check_taggable(arn),
        }

    def search_resource_explorer(self) -> Dict:
        """
        Elenca le risorse della region usando AWS Resource Explorer.

        Serve perche' get_resources restituisce solo le risorse "tagged or previously
        tagged": quelle mai taggate (route di API Gateway, parameter group di MemoryDB,
        versioni di Lambda, chiavi KMS, event bus...) non compaiono. Resource Explorer
        invece indicizza tutto, ed e' la sorgente usata dal Tag Editor della console.

        Attenzione: i tag riportati da Resource Explorer provengono da un indice
        aggiornato in modo asincrono, quindi possono essere leggermente arretrati.

        Returns:
            {'resources': [...], 'warnings': [...]}
            Se Resource Explorer non e' attivo nella region la lista e' vuota e il
            motivo viene riportato tra i warning, senza sollevare eccezioni.
        """
        warnings = []
        try:
            client = self.session.client('resource-explorer-2')
            view_arn = client.get_default_view().get('ViewArn')
            if not view_arn:
                return {'resources': [], 'warnings': [
                    f"Resource Explorer non ha una vista di default nella region {self.region_name}."]}

            resources = []
            completo = True
            paginator = client.get_paginator('search')
            for page in paginator.paginate(QueryString=f"region:{self.region_name}", ViewArn=view_arn):
                for item in page.get('Resources', []):
                    resources.append(self._format_re_resource(item))
                # Con piu' di 1000 risorse l'indice segnala il risultato come parziale.
                if not page.get('Count', {}).get('Complete', True):
                    completo = False

            if not completo:
                warnings.append(
                    'Resource Explorer ha restituito un elenco parziale (limite di 1000 risorse '
                    'per ricerca): filtrare per servizio per vedere le restanti.')

            self.logger.info(f"Resource Explorer: {len(resources)} risorse in {self.region_name}")
            return {'resources': resources, 'warnings': warnings}

        except ClientError as e:
            codice = e.response.get('Error', {}).get('Code', '')
            self.logger.warning(f"Resource Explorer non utilizzabile in {self.region_name}: {e}")
            if codice in ('ResourceNotFoundException', 'ValidationException'):
                messaggio = (f"Resource Explorer non e' attivo nella region {self.region_name} "
                             f"(nessun indice o vista di default): elenco limitato alle risorse "
                             f"gia' taggate almeno una volta.")
            elif codice in ('AccessDeniedException', 'UnauthorizedException'):
                messaggio = ("Permessi mancanti per Resource Explorer (servono "
                             "resource-explorer-2:GetDefaultView e resource-explorer-2:Search).")
            else:
                messaggio = f"Resource Explorer non disponibile: {e}"
            return {'resources': [], 'warnings': [messaggio]}

    def _format_re_resource(self, item: Dict) -> Dict:
        """
        Trasforma un elemento di Resource Explorer nel formato usato dalla UI.

        Servizio e tipo arrivano dai campi dedicati (piu' affidabili del parsing
        dell'ARN), i tag dalla proprieta' 'tags' della vista.
        """
        arn = item.get('Arn', '')
        info = parse_arn(arn)

        tags = {}
        for prop in item.get('Properties', []):
            if prop.get('Name') == 'tags':
                tags = {t['Key']: t.get('Value', '') for t in prop.get('Data', [])}

        resource_type = item.get('ResourceType', '')
        return {
            'arn': arn,
            'tags': tags,
            'tag_count': len(tags),
            'service': item.get('Service') or info['service'],
            'region': item.get('Region') or self.region_name,
            'account': item.get('OwningAccountId') or info['account'],
            # ResourceType di Resource Explorer e' gia' nel formato "servizio:tipo"
            'resource_type': resource_type.split(':', 1)[1] if ':' in resource_type else info['resource_type'],
            'resource_type_filter': resource_type or info['resource_type_filter'],
            'name': info['name'],
            'source': SOURCE_EXPLORER,
            'last_reported_at': str(item.get('LastReportedAt', '')),
            **check_taggable(arn),
        }

    def get_all_resources(self, source: str = SOURCE_BOTH) -> Dict:
        """
        Elenca le risorse della region unendo le due sorgenti disponibili.

        Args:
            source: 'tagging' (solo Tagging API), 'explorer' (solo Resource Explorer)
                    oppure 'both' (default: unione delle due)

        Returns:
            {'resources': [...], 'warnings': [...]}
            Per le risorse presenti in entrambe le sorgenti valgono i tag della
            Tagging API, che sono sempre aggiornati, e il campo source vale 'both'.
        """
        warnings = []

        if source == SOURCE_TAGGING:
            return {'resources': self.get_resources(), 'warnings': warnings}

        esito = self.search_resource_explorer()
        warnings.extend(esito['warnings'])
        unite = {r['arn']: r for r in esito['resources']}

        if source == SOURCE_EXPLORER:
            resources = list(unite.values())
        else:
            for r in self.get_resources():
                if r['arn'] in unite:
                    r['source'] = SOURCE_BOTH
                    r['last_reported_at'] = unite[r['arn']].get('last_reported_at', '')
                    # Il tipo di Resource Explorer e' piu' preciso di quello dedotto dall'ARN.
                    r['resource_type'] = unite[r['arn']]['resource_type'] or r['resource_type']
                    r['resource_type_filter'] = unite[r['arn']]['resource_type_filter']
                unite[r['arn']] = r
            resources = list(unite.values())

        resources.sort(key=lambda r: (r['service'], r['resource_type'], r['name']))
        return {'resources': resources, 'warnings': warnings}

    def get_tag_keys(self) -> List[str]:
        """Elenca tutte le chiavi tag utilizzate nella region."""
        keys = []
        try:
            paginator = self.client.get_paginator('get_tag_keys')
            for page in paginator.paginate():
                keys.extend(page.get('TagKeys', []))
        except ClientError as e:
            self.logger.error(f"Errore nel recupero delle chiavi tag: {e}")
            raise
        return sorted(keys)

    def get_tag_values(self, key: str) -> List[str]:
        """Elenca tutti i valori assegnati a una chiave tag nella region."""
        values = []
        try:
            paginator = self.client.get_paginator('get_tag_values')
            for page in paginator.paginate(Key=key):
                values.extend(page.get('TagValues', []))
        except ClientError as e:
            self.logger.error(f"Errore nel recupero dei valori del tag {key}: {e}")
            raise
        return sorted(v for v in values if v)

    def list_regions(self) -> List[str]:
        """Elenca le region abilitate sull'account, usando ec2 describe_regions."""
        try:
            ec2 = self.session.client('ec2')
            response = ec2.describe_regions(AllRegions=False)
            return sorted(r['RegionName'] for r in response.get('Regions', []))
        except ClientError as e:
            self.logger.error(f"Errore nel recupero delle region: {e}")
            raise

    # ------------------------------------------------------------------
    # Scrittura
    # ------------------------------------------------------------------

    def tag_resources(self, arns: List[str], tags: Dict[str, str]) -> Dict:
        """
        Aggiunge (o sovrascrive) i tag indicati sulle risorse passate.

        Le chiamate sono spezzate a blocchi di 20 ARN come richiesto da AWS.

        Args:
            arns: lista di ARN da taggare
            tags: dizionario chiave/valore dei tag da applicare

        Returns:
            {'succeeded': [...], 'failed': {arn: messaggio}}
        """
        return self._apply_in_chunks(
            arns,
            lambda chunk: self.client.tag_resources(ResourceARNList=chunk, Tags=tags),
            f"aggiunta tag {list(tags.keys())}"
        )

    def untag_resources(self, arns: List[str], tag_keys: List[str]) -> Dict:
        """
        Rimuove le chiavi tag indicate dalle risorse passate.

        Args:
            arns: lista di ARN da modificare
            tag_keys: chiavi dei tag da rimuovere

        Returns:
            {'succeeded': [...], 'failed': {arn: messaggio}}
        """
        return self._apply_in_chunks(
            arns,
            lambda chunk: self.client.untag_resources(ResourceARNList=chunk, TagKeys=tag_keys),
            f"rimozione tag {tag_keys}"
        )

    def _apply_in_chunks(self, arns: List[str], call, descrizione: str) -> Dict:
        """
        Esegue l'operazione su blocchi di MAX_ARN_PER_CALL ARN e raccoglie gli esiti.

        AWS non solleva eccezione sui singoli ARN falliti: li restituisce dentro
        FailedResourcesMap, quindi vanno letti e riportati esplicitamente.
        """
        result = {'succeeded': [], 'failed': {}, 'failed_details': {}}

        for i in range(0, len(arns), MAX_ARN_PER_CALL):
            chunk = arns[i:i + MAX_ARN_PER_CALL]
            try:
                response = call(chunk)
                failed = response.get('FailedResourcesMap', {})
            except ClientError as e:
                self.logger.error(f"Errore durante la {descrizione}: {e}")
                for arn in chunk:
                    result['failed'][arn] = readable_error(str(e))
                    result['failed_details'][arn] = str(e)
                continue

            for arn in chunk:
                if arn in failed:
                    errore = failed[arn]
                    testo = errore.get('ErrorMessage') or errore.get('ErrorCode', 'errore sconosciuto')
                    result['failed'][arn] = readable_error(testo)
                    result['failed_details'][arn] = testo
                else:
                    result['succeeded'].append(arn)

        self.logger.info(
            f"Operazione '{descrizione}': {len(result['succeeded'])} ok, {len(result['failed'])} errori"
        )
        return result

    # ------------------------------------------------------------------
    # Statistiche
    # ------------------------------------------------------------------

    @staticmethod
    def build_summary(resources: List[Dict]) -> Dict:
        """Calcola i contatori mostrati nelle card di riepilogo."""
        untagged = sum(1 for r in resources if not r['tags'])
        services = {}
        tag_keys = {}
        sources = {}
        for r in resources:
            services[r['service']] = services.get(r['service'], 0) + 1
            sources[r.get('source', SOURCE_TAGGING)] = sources.get(r.get('source', SOURCE_TAGGING), 0) + 1
            for key in r['tags']:
                tag_keys[key] = tag_keys.get(key, 0) + 1

        return {
            'total': len(resources),
            'untagged': untagged,
            'tagged': len(resources) - untagged,
            'services': dict(sorted(services.items(), key=lambda kv: -kv[1])),
            'tag_keys': dict(sorted(tag_keys.items(), key=lambda kv: -kv[1])),
            'sources': sources,
        }

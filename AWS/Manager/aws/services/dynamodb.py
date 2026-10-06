"""
DynamoDB: tabelle, descrizione e lettura delle righe a pagine.

Pensato per tabelle anche molto grandi:
    - aprire una tabella legge solo la descrizione (DescribeTable, non consuma letture)
    - le righe si leggono a richiesta, una pagina alla volta: Query se e' indicato il
      valore della partition key (della tabella o di un indice), altrimenti Scan
    - la pagina successiva riparte da LastEvaluatedKey, che la pagina rimanda indietro
    - con un filtro sugli attributi lo Scan legge comunque tutte le righe che attraversa:
      si ferma dopo max_read righe lette anche se ne ha trovate meno di quelle chieste
    - ogni risposta riporta righe lette, righe trovate e capacita' consumata (RCU)
"""

import base64
import json
from decimal import Decimal, InvalidOperation

from boto3.dynamodb.types import Binary, TypeDeserializer

from aws.services import paginate

# Operatori sulla sort key (KeyConditionExpression) e sui filtri (FilterExpression)
SORT_OPERATORS = ('=', '<', '<=', '>', '>=', 'begins_with', 'between')
FILTER_OPERATORS = ('=', '<>', '<', '<=', '>', '>=', 'contains', 'begins_with',
                    'attribute_exists', 'attribute_not_exists')


def _plain(value):
    """Valore deserializzato pronto per il JSON: i binari diventano base64."""
    if isinstance(value, Binary):
        return base64.b64encode(value.value).decode()
    if isinstance(value, (bytes, bytearray)):
        return base64.b64encode(value).decode()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, set, frozenset)):
        return [_plain(v) for v in value]
    return value


def _typed(value, kind, label):
    """Valore scritto nella pagina -> attributo DynamoDB del tipo indicato (S, N, BOOL)."""
    if kind == 'N':
        try:
            Decimal(value.strip())
        except (InvalidOperation, AttributeError):
            raise ValueError(f"{label}: '{value}' non e' un numero")
        return {'N': value.strip()}
    if kind == 'BOOL':
        if value.strip().lower() not in ('true', 'false'):
            raise ValueError(f"{label}: per un booleano scrivere true o false")
        return {'BOOL': value.strip().lower() == 'true'}
    if kind == 'S':
        return {'S': value}
    raise ValueError(f"{label}: il tipo {kind} non e' supportato nei filtri (solo stringhe e numeri)")


class AwsDynamoDB:
    def __init__(self, session):
        self.client = session.client('dynamodb')

    def tables(self):
        return [{'TableName': t} for t in paginate(self.client, 'list_tables', 'TableNames')]

    def describe(self, table):
        return self.client.describe_table(TableName=table)['Table']

    @staticmethod
    def key_schema(desc, index=''):
        """
        Chiavi della tabella o di un suo indice: {'partition': (nome, tipo), 'sort': (nome, tipo) | None}.
        """
        types = {a['AttributeName']: a['AttributeType'] for a in desc.get('AttributeDefinitions', [])}
        schema = desc['KeySchema']
        if index:
            indexes = desc.get('GlobalSecondaryIndexes', []) + desc.get('LocalSecondaryIndexes', [])
            found = next((i for i in indexes if i['IndexName'] == index), None)
            if not found:
                raise ValueError(f"Indice sconosciuto: {index}")
            schema = found['KeySchema']
        keys = {k['KeyType']: k['AttributeName'] for k in schema}
        return {
            'partition': (keys['HASH'], types.get(keys['HASH'], 'S')),
            'sort': (keys['RANGE'], types.get(keys['RANGE'], 'S')) if 'RANGE' in keys else None,
        }

    def read(self, table, index='', pk='', sort_op='', sort_value='', sort_value2='',
             filter_attr='', filter_op='', filter_value='', filter_type='S',
             descending=False, page_size=100, max_read=5000, start=None):
        """
        Una pagina di righe. Con pk e' una Query (legge solo le righe di quella partizione,
        eventualmente ristrette dalla condizione sulla sort key), senza e' uno Scan.
        Il filtro sugli attributi si applica dopo la lettura: riduce le righe mostrate,
        non quelle lette (e pagate).

        Ritorna {'items', 'mode', 'next' (chiave da cui ripartire o None), 'scanned',
                 'count', 'capacity' (RCU consumate), 'stopped' (fermato da max_read)}.
        """
        desc = self.describe(table)
        keys = self.key_schema(desc, index)
        names, values = {}, {}

        def name(attr):
            alias = f"#n{len(names)}"
            names[alias] = attr
            return alias

        def val(attr_value):
            alias = f":v{len(values)}"
            values[alias] = attr_value
            return alias

        params = {'TableName': table, 'ReturnConsumedCapacity': 'TOTAL'}
        if index:
            params['IndexName'] = index

        mode = 'scan'
        if pk != '':
            mode = 'query'
            p_name, p_type = keys['partition']
            cond = f"{name(p_name)} = {val(_typed(pk, p_type, p_name))}"
            if sort_op and keys['sort']:
                s_name, s_type = keys['sort']
                if sort_op not in SORT_OPERATORS:
                    raise ValueError(f"Operatore non valido: {sort_op}")
                n = name(s_name)
                if sort_op == 'between':
                    cond += (f" AND {n} BETWEEN {val(_typed(sort_value, s_type, s_name))}"
                             f" AND {val(_typed(sort_value2, s_type, s_name))}")
                elif sort_op == 'begins_with':
                    cond += f" AND begins_with({n}, {val(_typed(sort_value, s_type, s_name))})"
                else:
                    cond += f" AND {n} {sort_op} {val(_typed(sort_value, s_type, s_name))}"
            params['KeyConditionExpression'] = cond
            params['ScanIndexForward'] = not descending
        elif sort_op:
            raise ValueError("La condizione sulla sort key richiede il valore della partition key")

        if filter_attr:
            if filter_op not in FILTER_OPERATORS:
                raise ValueError(f"Operatore di filtro non valido: {filter_op}")
            n = name(filter_attr)
            if filter_op in ('attribute_exists', 'attribute_not_exists'):
                params['FilterExpression'] = f"{filter_op}({n})"
            elif filter_op in ('contains', 'begins_with'):
                params['FilterExpression'] = f"{filter_op}({n}, {val(_typed(filter_value, filter_type, filter_attr))})"
            else:
                params['FilterExpression'] = f"{n} {filter_op} {val(_typed(filter_value, filter_type, filter_attr))}"

        if names:
            params['ExpressionAttributeNames'] = names
        if values:
            params['ExpressionAttributeValues'] = values
        if start:
            params['ExclusiveStartKey'] = json.loads(start) if isinstance(start, str) else start

        # richieste successive finche' non ci sono page_size righe o si sono lette max_read righe
        call = self.client.query if mode == 'query' else self.client.scan
        raw, scanned, capacity, last, stopped = [], 0, 0.0, None, False
        while True:
            params['Limit'] = min(page_size - len(raw), 1000) if not filter_attr else min(page_size, 1000)
            resp = call(**params)
            raw += resp.get('Items', [])
            scanned += resp.get('ScannedCount', 0)
            capacity += (resp.get('ConsumedCapacity') or {}).get('CapacityUnits', 0)
            last = resp.get('LastEvaluatedKey')
            if not last or len(raw) >= page_size:
                break
            if scanned >= max_read:
                stopped = True
                break
            params['ExclusiveStartKey'] = last

        # con un filtro una richiesta puo' restituire piu' righe di quelle che mancano:
        # si tengono le prime e si riparte dalla chiave dell'ultima mostrata
        if len(raw) > page_size:
            raw = raw[:page_size]
            last = self._key_of(raw[-1], desc, index)

        deserializer = TypeDeserializer()
        items = [{k: _plain(deserializer.deserialize(v)) for k, v in item.items()} for item in raw]
        return {
            'items': items, 'mode': mode, 'index': index,
            'next': json.dumps(last) if last else None,
            'scanned': scanned, 'count': len(items),
            'capacity': round(capacity, 2), 'stopped': stopped,
        }

    def _key_of(self, item, desc, index):
        """Chiave di ripartenza di una riga: chiavi della tabella piu' quelle dell'indice."""
        attrs = [k['AttributeName'] for k in desc['KeySchema']]
        if index:
            keys = self.key_schema(desc, index)
            attrs += [keys['partition'][0]] + ([keys['sort'][0]] if keys['sort'] else [])
        return {a: item[a] for a in dict.fromkeys(attrs) if a in item}

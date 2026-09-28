"""DynamoDB: tabelle, descrizione e prime righe (scan limitato)."""

from boto3.dynamodb.types import TypeDeserializer

from aws.services import paginate


class AwsDynamoDB:
    def __init__(self, session):
        self.client = session.client('dynamodb')

    def tables(self):
        return [{'TableName': t} for t in paginate(self.client, 'list_tables', 'TableNames')]

    def describe(self, table):
        return self.client.describe_table(TableName=table)['Table']

    def scan(self, table, limit=500):
        """
        Prime righe della tabella, al massimo limit: su tabelle grandi uno scan completo
        costa letture e tempo. Ritorna le righe come dizionari Python.
        """
        deserializer = TypeDeserializer()
        items = paginate(self.client, 'scan', 'Items', limit=limit, TableName=table,
                         PaginationConfig={'PageSize': min(limit, 1000)})
        rows = [{k: deserializer.deserialize(v) for k, v in item.items()} for item in items]
        return {'items': rows, 'truncated': len(rows) >= limit}

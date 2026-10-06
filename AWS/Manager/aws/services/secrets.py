"""Secrets Manager: segreti, metadati e versioni; il valore si legge solo a richiesta."""

from aws.services import paginate


class AwsSecrets:
    def __init__(self, session):
        self.client = session.client('secretsmanager')

    def secrets(self):
        return paginate(self.client, 'list_secrets', 'SecretList')

    def describe(self, secret_id):
        return self.client.describe_secret(SecretId=secret_id)

    def value(self, secret_id):
        """Valore della versione corrente (AWSCURRENT): testo o binario."""
        v = self.client.get_secret_value(SecretId=secret_id)
        return {'SecretString': v.get('SecretString'), 'Binary': 'SecretBinary' in v,
                'VersionId': v.get('VersionId'), 'CreatedDate': v.get('CreatedDate')}

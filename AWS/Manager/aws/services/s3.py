"""Bucket S3: elenco, proprieta', navigazione per cartelle, download con URL firmato e upload."""

from botocore.config import Config
from botocore.exceptions import ClientError

# Codici di errore che significano "configurazione assente" (non un errore vero)
MISSING_CODES = {
    'NoSuchPublicAccessBlockConfiguration', 'ServerSideEncryptionConfigurationNotFoundError',
    'OwnershipControlsNotFoundError', 'NoSuchBucketPolicy', 'NoSuchLifecycleConfiguration',
    'NoSuchWebsiteConfiguration', 'NoSuchCORSConfiguration', 'ObjectLockConfigurationNotFoundError',
    'ReplicationConfigurationNotFoundError',
}


def _read(fn, describe, absent):
    """Una proprieta' del bucket: describe(risposta), absent se non configurata."""
    try:
        return describe(fn())
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code', '')
        if code in MISSING_CODES:
            return absent
        if code in ('AccessDenied', 'AllAccessDisabled'):
            return 'accesso negato'
        return f"errore: {code or e}"


class AwsS3:
    def __init__(self, session):
        self.session = session
        self.client = session.client('s3')

    def bucket_list(self):
        return self.client.list_buckets().get('Buckets', [])

    def bucket_region(self, bucket):
        """Region del bucket (LocationConstraint vuoto = us-east-1)."""
        return self.client.get_bucket_location(Bucket=bucket).get('LocationConstraint') or 'us-east-1'

    def bucket_info(self, bucket):
        """
        Proprieta' principali del bucket ({etichetta: testo}), lette con un client nella
        region del bucket. Sono letture della configurazione (richieste GET, costo trascurabile).
        """
        region = self.bucket_region(bucket)
        c = self.session.client('s3', region_name=region)

        def versioning(r):
            status = r.get('Status') or 'mai attivato'
            return status + (f" (MFA delete: {r['MFADelete']})" if r.get('MFADelete') else '')

        def encryption(r):
            rules = r.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
            out = []
            for rule in rules:
                d = rule.get('ApplyServerSideEncryptionByDefault', {})
                text = d.get('SSEAlgorithm', '?')
                if d.get('KMSMasterKeyID'):
                    text += f" ({d['KMSMasterKeyID']})"
                if rule.get('BucketKeyEnabled'):
                    text += ', bucket key'
                out.append(text)
            return '; '.join(out) or 'nessuna'

        def public_block(r):
            conf = r.get('PublicAccessBlockConfiguration', {})
            off = [k for k, v in conf.items() if not v]
            return 'tutto bloccato' if not off else 'non attivi: ' + ', '.join(off)

        def policy_status(r):
            return 'pubblica' if r.get('PolicyStatus', {}).get('IsPublic') else 'non pubblica'

        def website(r):
            index = r.get('IndexDocument', {}).get('Suffix')
            redirect = r.get('RedirectAllRequestsTo', {}).get('HostName')
            return f"attivo (index {index})" if index else f"redirect a {redirect}" if redirect else 'attivo'

        def eventbridge(r):
            # EventBridgeConfiguration presente (anche vuoto) = eventi del bucket inviati a EventBridge
            others = sum(len(r.get(k, [])) for k in ('LambdaFunctionConfigurations', 'QueueConfigurations',
                                                     'TopicConfigurations'))
            text = 'attivo' if 'EventBridgeConfiguration' in r else 'disattivato'
            return text + (f" (altre notifiche: {others})" if others else '')

        def logging_(r):
            t = r.get('LoggingEnabled')
            return f"s3://{t['TargetBucket']}/{t.get('TargetPrefix', '')}" if t else 'disattivato'

        return {
            'Region': region,
            'Versioning': _read(lambda: c.get_bucket_versioning(Bucket=bucket), versioning, ''),
            'EventBridge': _read(lambda: c.get_bucket_notification_configuration(Bucket=bucket),
                                 eventbridge, 'disattivato'),
            'Crittografia': _read(lambda: c.get_bucket_encryption(Bucket=bucket), encryption, 'nessuna'),
            'Blocco accesso pubblico': _read(lambda: c.get_public_access_block(Bucket=bucket),
                                             public_block, 'non configurato'),
            'Policy': _read(lambda: c.get_bucket_policy_status(Bucket=bucket), policy_status, 'nessuna'),
            'Proprieta\' oggetti': _read(lambda: c.get_bucket_ownership_controls(Bucket=bucket),
                                         lambda r: ', '.join(x.get('ObjectOwnership', '?') for x in
                                                             r.get('OwnershipControls', {}).get('Rules', [])),
                                         'non configurata (ACL attive)'),
            'Lifecycle': _read(lambda: c.get_bucket_lifecycle_configuration(Bucket=bucket),
                               lambda r: f"{len(r.get('Rules', []))} regole", 'nessuna regola'),
            'Replica': _read(lambda: c.get_bucket_replication(Bucket=bucket),
                             lambda r: f"{len(r.get('ReplicationConfiguration', {}).get('Rules', []))} regole",
                             'disattivata'),
            'Object Lock': _read(lambda: c.get_object_lock_configuration(Bucket=bucket),
                                 lambda r: r.get('ObjectLockConfiguration', {}).get('ObjectLockEnabled', 'no'),
                                 'disattivato'),
            'Sito web statico': _read(lambda: c.get_bucket_website(Bucket=bucket), website, 'disattivato'),
            'CORS': _read(lambda: c.get_bucket_cors(Bucket=bucket),
                          lambda r: f"{len(r.get('CORSRules', []))} regole", 'nessuna regola'),
            'Log degli accessi': _read(lambda: c.get_bucket_logging(Bucket=bucket), logging_, 'disattivato'),
        }

    def object_list(self, bucket, prefix='', limit=1000):
        """
        Cartelle (CommonPrefixes) e oggetti allo stesso livello del prefisso.
        L'oggetto "cartella" vuoto con lo stesso nome del prefisso viene tolto.
        """
        folders, objects = [], []
        paginator = self.client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
            folders += [p['Prefix'] for p in page.get('CommonPrefixes', [])]
            objects += [o for o in page.get('Contents', []) if o['Key'] not in (prefix, prefix + '/')]
            if len(folders) + len(objects) >= limit:
                return {'folders': folders, 'objects': objects, 'truncated': True}
        return {'folders': folders, 'objects': objects, 'truncated': False}

    def presigned_url(self, bucket, key, expires=3600):
        """URL di download valido un'ora, firmato nella region del bucket."""
        client = self.session.client('s3', region_name=self.bucket_region(bucket),
                                     config=Config(signature_version='s3v4'))
        return client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key},
                                             ExpiresIn=expires)

    def upload(self, bucket, key, fileobj):
        self.client.upload_fileobj(fileobj, bucket, key)

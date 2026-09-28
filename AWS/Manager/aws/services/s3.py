"""Bucket S3: elenco, navigazione per cartelle, download con URL firmato e upload."""

from botocore.config import Config


class AwsS3:
    def __init__(self, session):
        self.session = session
        self.client = session.client('s3')

    def bucket_list(self):
        return self.client.list_buckets().get('Buckets', [])

    def bucket_region(self, bucket):
        """Region del bucket (LocationConstraint vuoto = us-east-1)."""
        return self.client.get_bucket_location(Bucket=bucket).get('LocationConstraint') or 'us-east-1'

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

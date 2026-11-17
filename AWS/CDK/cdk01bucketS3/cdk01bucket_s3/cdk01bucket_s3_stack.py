"""Bucket S3 privato, il primo esempio CDK del repository.

- nome del bucket aws-py-cdk01-bucket-<account> (naming.py: i nomi dei bucket sono unici in tutto AWS)
- versioning attivo: le versioni precedenti dei file spariscono dopo 30 giorni
- cifratura lato server (SSE-S3), accesso pubblico bloccato, solo richieste HTTPS
- al destroy il bucket si svuota e si cancella (auto_delete_objects)
"""

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
)
from constructs import Construct


class Cdk01BucketS3Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(self, "Bucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(id="versioni-precedenti",
                                              noncurrent_version_expiration=Duration.days(30))],
            # esempio: al destroy si cancellano anche i file (e tutte le loro versioni)
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "BucketArn", value=self.bucket.bucket_arn)

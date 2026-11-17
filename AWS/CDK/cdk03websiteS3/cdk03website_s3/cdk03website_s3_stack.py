"""Sito statico pubblico servito dall'endpoint website di S3.

- bucket con hosting statico (index.html, error.html) e lettura pubblica degli oggetti
- le pagine della cartella web/ vengono caricate da CDK al deploy (BucketDeployment)
- niente enforce_ssl: l'endpoint website di S3 risponde solo in HTTP, la regola "solo HTTPS"
  bloccherebbe tutte le richieste con un 403 (per l'HTTPS vedi il cdk04 con CloudFront)
- al destroy il bucket si svuota e si cancella

Per rendere pubblico un bucket il "Blocco dell'accesso pubblico" a livello di account deve essere disattivato
(vedi README): se e' attivo il deploy fallisce sulla bucket policy.
"""

import os

from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")


class Cdk03WebsiteS3Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(self, "WebsiteBucket",
            website_index_document="index.html",
            website_error_document="error.html",
            encryption=s3.BucketEncryption.S3_MANAGED,
            # solo la policy pubblica di lettura: le ACL restano bloccate
            block_public_access=s3.BlockPublicAccess(block_public_acls=True, ignore_public_acls=True,
                                                     block_public_policy=False, restrict_public_buckets=False),
            public_read_access=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        s3deploy.BucketDeployment(self, "WebsiteDeployment",
            sources=[s3deploy.Source.asset(WEB_DIR)],
            destination_bucket=self.bucket,
            log_group=logs.LogGroup(self, "WebsiteDeploymentLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "WebsiteUrl", value=self.bucket.bucket_website_url)

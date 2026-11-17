"""Sito statico in HTTPS con CloudFront davanti a un bucket S3 privato.

- bucket privato (accesso pubblico bloccato, solo HTTPS): lo legge solo CloudFront con Origin Access Control (OAC)
- distribuzione CloudFront con redirect da HTTP a HTTPS, index.html come pagina iniziale, compressione
- le pagine della cartella web/ vengono caricate da CDK al deploy, con l'invalidazione della cache di CloudFront
- al destroy il bucket si svuota e si cancella

La prima versione usava una Origin Access Identity (OAI, ormai superata) e un bucket pubblico: con OAC
il bucket resta privato e la policy autorizza solo questa distribuzione.
"""

import os

from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")


class Cdk04CloudFrontStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bucket = s3.Bucket(self, "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.distribution = cloudfront.Distribution(self, "Distribution",
            comment=f"{self.stack_name} sito statico",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,  # solo Europa e Nord America: costa meno
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(self.bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True))

        s3deploy.BucketDeployment(self, "SiteDeployment",
            sources=[s3deploy.Source.asset(WEB_DIR)],
            destination_bucket=self.bucket,
            distribution=self.distribution, distribution_paths=["/*"],
            log_group=logs.LogGroup(self, "SiteDeploymentLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=self.distribution.distribution_id)
        CfnOutput(self, "SiteUrl", value=f"https://{self.distribution.distribution_domain_name}")

from aws_cdk import (CfnOutput,RemovalPolicy,
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_s3 as s3,
)
from constructs import Construct

class Cdk03WebsiteS3Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        bucket = s3.Bucket(self, "MyBucket",
            bucket_name="prova-alberto-website", # specify a unique bucket name
            versioned=True, # enable versioning for the bucket
            encryption=s3.BucketEncryption.S3_MANAGED, # use S3-managed encryption
            #access_control=s3.BucketAccessControl.PUBLIC_READ,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,#: typing.Optional[builtins.bool] = None,
                ignore_public_acls=False,#: typing.Optional[builtins.bool] = None,
                restrict_public_buckets=False,#: typing.Optional[builtins.bool] = None,
            ),
            website_index_document="index.html",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            enforce_ssl=True
        )
        bucket.grant_public_access()
        CfnOutput(self, 'BucketName', value=bucket.bucket_name)
        CfnOutput(self, 'BucketDomainName', value=bucket.bucket_domain_name)
        CfnOutput(self, 'BucketRegionalDomainName', value=bucket.bucket_regional_domain_name)

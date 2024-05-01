from aws_cdk import (    Stack,RemovalPolicy )
from constructs import Construct
import aws_cdk.aws_s3 as s3

class Cdk01BucketS3Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(self,
            id="01BucketS3", 
            bucket_name="cdk-01-bucket-s3", 
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY
        )
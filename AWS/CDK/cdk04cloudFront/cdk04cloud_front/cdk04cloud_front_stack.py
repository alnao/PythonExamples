from aws_cdk import (
    Stack,CfnOutput,
    aws_s3 as s3,RemovalPolicy,
    aws_cloudfront as cf,
)
from constructs import Construct

#see https://github.com/aws-samples/deploy-cloudfront-in-china-with-cdk/blob/main/Python/lib/cloudfront_in_china_stack.py
#see https://www.reddit.com/r/aws/comments/12tqqpw/aws_cdk_api_s3_putbucketpolicy_access_denied_and/
class Cdk04CloudFrontStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket(self, "formazione-alberto-cf",
            bucket_name="formazione-alberto-cf", 
            #see https://www.reddit.com/r/aws/comments/12tqqpw/aws_cdk_api_s3_putbucketpolicy_access_denied_and/
            access_control=s3.BucketAccessControl.PRIVATE,
            #access_control=s3.BucketAccessControl.PUBLIC_READ,
            #block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
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
    #def altro(self,bucket):
        bucket.grant_public_access()
        oai = cf.OriginAccessIdentity(self, 'MyOriginAccessIdentity')
        oai.apply_removal_policy(RemovalPolicy.DESTROY)
        bucket.grant_read(oai)
        oai_id = 'origin-access-identity/cloudfront/{}'.format(oai.origin_access_identity_id)

        # Replace the value with your IAM server certificate ID.
        #iam_cert_id = 'YOUR_CERTIFICATE_ID'
        # Replace the value with your alternate domain names for the cloudfront distribution
        #cname = ['www1.example.com.cn', 'www2.example.com.cn']


        cf_distribution = cf.CfnDistribution(
            self, 'MyCloudfrontDistribution',
            distribution_config=cf.CfnDistribution.DistributionConfigProperty(
                # Create cache behaviors with legacy cache settings
                default_cache_behavior=cf.CfnDistribution.DefaultCacheBehaviorProperty(
                    target_origin_id=bucket.bucket_name,
                    viewer_protocol_policy='redirect-to-https',
                    compress=True,
                    forwarded_values=cf.CfnDistribution.ForwardedValuesProperty(
                        query_string=False
                    )
                ),
                enabled=True,
#                aliases=cname,
                default_root_object='index.html',
                http_version='http2',
                ipv6_enabled=False,
                origins=[
                    cf.CfnDistribution.OriginProperty(
                        id=bucket.bucket_name,
                        domain_name=bucket.bucket_regional_domain_name,
                        s3_origin_config=cf.CfnDistribution.S3OriginConfigProperty(
                            origin_access_identity=oai_id
                        )
                    )
                ],
#                viewer_certificate=cf.CfnDistribution.ViewerCertificateProperty(
#                    iam_certificate_id=iam_cert_id,
#                    minimum_protocol_version='TLSv1.2_2021',
#                    ssl_support_method='sni-only'
#                )
            )
        )

        CfnOutput(self, 'BucketName', value=bucket.bucket_name)
        CfnOutput(self, 'BucketDomainName', value=bucket.bucket_domain_name)
        CfnOutput(self, 'BucketRegionalDomainName', value=bucket.bucket_regional_domain_name)
        CfnOutput(self, 'DistributionId', value=cf_distribution.attr_id)

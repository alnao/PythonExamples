import tempfile

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk33bedrock_serverless.cdk33bedrock_serverless_stack import Cdk33BedrockServerlessStack


def template():
    app = core.App()
    # cartella vuota al posto del layer creato da build_layer.sh
    stack = Cdk33BedrockServerlessStack(app, "cdk33-bedrock-serverless", layer_dir=tempfile.mkdtemp(),
                                   env=core.Environment(account="123456789012", region="eu-central-1"))
    return assertions.Template.from_stack(stack)


def test_vector_index():
    t = template()
    t.resource_count_is("AWS::S3Vectors::VectorBucket", 1)
    t.has_resource_properties("AWS::S3Vectors::Index", {
        "DataType": "float32",
        "Dimension": 1024,
        "DistanceMetric": "cosine",
        "MetadataConfiguration": {"NonFilterableMetadataKeys": ["text"]},
    })


def test_lambdas():
    t = template()
    t.has_resource_properties("AWS::Lambda::Function", {"Handler": "api.handler", "Runtime": "python3.13", "Timeout": 29})
    t.has_resource_properties("AWS::Lambda::Function", {"Handler": "ingest.handler", "Runtime": "python3.13",
                                                         "Timeout": 900, "MemorySize": 3008})
    t.has_resource_properties("AWS::Lambda::EventInvokeConfig", {"MaximumRetryAttempts": 0})


def test_api_and_site():
    t = template()
    t.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "ANY /api/{proxy+}"})
    t.resource_count_is("AWS::CloudFront::Distribution", 1)
    t.has_resource_properties("AWS::CloudFront::Distribution", {
        "DistributionConfig": assertions.Match.object_like({
            "DefaultRootObject": "index.html",
            "CacheBehaviors": [assertions.Match.object_like({"PathPattern": "/api/*"})],
        }),
    })


def test_buckets_are_private():
    t = template()
    t.has_resource_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True,
                                           "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
    })
    t.resource_count_is("AWS::SecretsManager::Secret", 1)


def test_fixed_names():
    t = template()
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "alnao-dev-cdk-cdk33bedrockserverless-documents"})
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "alnao-dev-cdk-cdk33bedrockserverless-site"})
    t.has_resource_properties("AWS::S3Vectors::VectorBucket", {"VectorBucketName": "alnao-dev-cdk-cdk33bedrockserverless-vectors"})
    for name in ("Api", "Ingest", "BucketNotifications", "AutoDeleteObjects", "BucketDeployment"):
        t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": f"Cdk33BedrockServerless-{name}"})
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/Cdk33BedrockServerless/{name}"})
        t.has_resource_properties("AWS::IAM::Role", {"RoleName": f"cdk33-bedrock-serverless-{name}ServiceRole"})
    t.has_resource_properties("AWS::IAM::Policy", {"PolicyName": "cdk33-bedrock-serverless-ApiServicePolicy"})
    t.has_resource_properties("AWS::SecretsManager::Secret", {"Name": "Cdk33BedrockServerless-ApiKey"})


def test_name_lengths():
    """Nomi entro i limiti di AWS: ruoli e Lambda 64 caratteri, bucket 63."""
    t = template()
    for kind, prop, limit in (("AWS::IAM::Role", "RoleName", 64), ("AWS::Lambda::Function", "FunctionName", 64),
                              ("AWS::S3::Bucket", "BucketName", 63), ("AWS::S3Vectors::VectorBucket", "VectorBucketName", 63)):
        for resource in t.find_resources(kind).values():
            assert len(resource["Properties"][prop]) <= limit, resource["Properties"][prop]


def test_log_retention_one_week():
    """Ogni log group conserva i log al massimo una settimana (e ha un nome fisso)."""
    groups = template().find_resources("AWS::Logs::LogGroup")
    assert len(groups) == 5
    assert all(g["Properties"]["RetentionInDays"] <= 7 for g in groups.values())

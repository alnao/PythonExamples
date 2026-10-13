import tempfile

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk32wiki_s3_vector.cdk32wiki_s3_vector_stack import Cdk32WikiS3VectorStack


def template():
    app = core.App()
    # cartella vuota al posto del layer creato da build_layer.sh
    stack = Cdk32WikiS3VectorStack(app, "wiki", layer_dir=tempfile.mkdtemp(),
                                   env=core.Environment(account="123456789012", region="eu-central-1"))
    return assertions.Template.from_stack(stack)


def test_vector_index():
    t = template()
    t.has_resource_properties("AWS::S3Vectors::VectorBucket", {"VectorBucketName": "alnao-dev-cdk-cdk32wikis3vector-vectors"})
    t.has_resource_properties("AWS::S3Vectors::Index", {
        "IndexName": "wiki", "DataType": "float32", "Dimension": 1024, "DistanceMetric": "cosine",
        "MetadataConfiguration": {"NonFilterableMetadataKeys": ["text"]},
    })


def test_lambdas_and_names():
    t = template()
    for name in ("Api", "Ingest", "BucketNotifications", "AutoDeleteObjects", "BucketDeployment"):
        t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": f"Cdk32WikiS3Vector-{name}"})
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/Cdk32WikiS3Vector/{name}"})
        t.has_resource_properties("AWS::IAM::Role", {"RoleName": f"wiki-{name}ServiceRole"})
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "alnao-dev-cdk-cdk32wikis3vector-files"})
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "alnao-dev-cdk-cdk32wikis3vector-site"})


def test_api_and_site():
    t = template()
    t.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "ANY /api/{proxy+}"})
    t.has_resource_properties("AWS::CloudFront::Distribution", {
        "DistributionConfig": assertions.Match.object_like({
            "CacheBehaviors": [assertions.Match.object_like({"PathPattern": "/api/*"})]}),
    })


def test_only_embedding_model():
    """Nessun modello di chat: le Lambda possono usare solo Titan Embeddings."""
    t = template()
    policies = t.find_resources("AWS::IAM::Policy")
    resources = [str(s.get("Resource")) for p in policies.values()
                 for s in p["Properties"]["PolicyDocument"]["Statement"] if "bedrock:InvokeModel" in str(s["Action"])]
    assert resources and all("titan-embed-text-v2" in r for r in resources)


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

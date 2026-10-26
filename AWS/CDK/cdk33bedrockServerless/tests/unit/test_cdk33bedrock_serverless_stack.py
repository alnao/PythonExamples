import re
import tempfile

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk33bedrock_serverless.cdk33bedrock_serverless_stack import Cdk33BedrockServerlessStack
from cdk33bedrock_serverless.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::ApiGatewayV2::Integration", "AWS::ApiGatewayV2::Route", "AWS::CloudFront::OriginAccessControl",
    "AWS::IAM::Policy", "AWS::Lambda::EventInvokeConfig", "AWS::Lambda::LayerVersion",
    "AWS::Lambda::Permission", "AWS::S3::BucketPolicy",
}


def template():
    app = core.App()
    apply_tags(app)
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


def test_all_resources_tagged():
    """Ogni risorsa che accetta tag ha i 6 tag standard; un tipo nuovo senza tag fa fallire il test."""
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = resource["Properties"].get("Tags", [])
        tags = tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_inference_profiles():
    """I modelli si chiamano con profili dell'applicazione (con i tag), cosi' il costo di Bedrock ha il Project."""
    t = template()
    profiles = t.find_resources("AWS::Bedrock::ApplicationInferenceProfile")
    sources = {p["Properties"]["InferenceProfileName"]: p["Properties"]["ModelSource"]["CopyFrom"]
               for p in profiles.values()}
    assert sources == {
        "Cdk33BedrockServerless-Embedding": "arn:aws:bedrock:eu-central-1::foundation-model/amazon.titan-embed-text-v2:0",
        "Cdk33BedrockServerless-Chat": "arn:aws:bedrock:eu-central-1:123456789012:inference-profile/eu.amazon.nova-lite-v1:0",
        "Cdk33BedrockServerless-Image": "arn:aws:bedrock:eu-central-1:123456789012:inference-profile/eu.amazon.nova-lite-v1:0",
    }
    # nome e descrizione accettano solo lettere, numeri, ":" e "." separati da uno spazio, "_" o "-"
    for p in profiles.values():
        for prop in ("InferenceProfileName", "Description"):
            assert re.fullmatch(r"([0-9a-zA-Z:.][ _-]?)+", p["Properties"][prop]), p["Properties"][prop]
    for handler in ("api.handler", "ingest.handler"):
        fn = next(iter(t.find_resources("AWS::Lambda::Function", {"Properties": {"Handler": handler}}).values()))
        env = fn["Properties"]["Environment"]["Variables"]
        for key, name in (("EMBEDDING_MODEL", "Embedding"), ("CHAT_MODEL", "Chat"), ("IMAGE_MODEL", "Image")):
            assert env[key] == {"Fn::GetAtt": [f"{name}Profile", "InferenceProfileArn"]}
    statements = [s for p in t.find_resources("AWS::IAM::Policy").values()
                  for s in p["Properties"]["PolicyDocument"]["Statement"] if s["Action"] == "bedrock:InvokeModel"]
    assert len(statements) == 2
    for name in ("Embedding", "Chat", "Image"):
        assert all({"Fn::GetAtt": [f"{name}Profile", "InferenceProfileArn"]} in s["Resource"] for s in statements)

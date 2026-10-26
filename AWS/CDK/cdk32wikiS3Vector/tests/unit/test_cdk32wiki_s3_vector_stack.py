import re
import tempfile

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk32wiki_s3_vector.cdk32wiki_s3_vector_stack import Cdk32WikiS3VectorStack
from cdk32wiki_s3_vector.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::ApiGatewayV2::Integration", "AWS::ApiGatewayV2::Route", "AWS::CloudFront::OriginAccessControl",
    "AWS::IAM::Policy", "AWS::Lambda::LayerVersion", "AWS::Lambda::Permission", "AWS::S3::BucketPolicy",
}


def template():
    app = core.App()
    apply_tags(app)
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
    """Nessun modello di chat: le Lambda possono usare solo Titan Embeddings, tramite il profilo con i tag."""
    t = template()
    titan = "arn:aws:bedrock:eu-central-1::foundation-model/amazon.titan-embed-text-v2:0"
    profile = {"Fn::GetAtt": ["EmbeddingProfile", "InferenceProfileArn"]}
    t.has_resource_properties("AWS::Bedrock::ApplicationInferenceProfile", {
        "InferenceProfileName": "Cdk32WikiS3Vector-Embedding", "ModelSource": {"CopyFrom": titan}})
    policies = t.find_resources("AWS::IAM::Policy")
    resources = [s["Resource"] for p in policies.values()
                 for s in p["Properties"]["PolicyDocument"]["Statement"] if "bedrock:InvokeModel" in str(s["Action"])]
    assert len(resources) == 2 and all(r == [profile, titan] for r in resources)
    for handler in ("api.handler", "ingest.handler"):
        t.has_resource_properties("AWS::Lambda::Function", {
            "Handler": handler, "Environment": {"Variables": assertions.Match.object_like({"EMBEDDING_MODEL": profile})}})
    # nome e descrizione accettano solo lettere, numeri, ":" e "." separati da uno spazio, "_" o "-"
    for p in t.find_resources("AWS::Bedrock::ApplicationInferenceProfile").values():
        for prop in ("InferenceProfileName", "Description"):
            assert re.fullmatch(r"([0-9a-zA-Z:.][ _-]?)+", p["Properties"][prop]), p["Properties"][prop]


def test_all_resources_tagged():
    """Ogni risorsa che accetta tag ha i 6 tag standard; un tipo nuovo senza tag fa fallire il test."""
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = resource["Properties"].get("Tags", [])
        tags = tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


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

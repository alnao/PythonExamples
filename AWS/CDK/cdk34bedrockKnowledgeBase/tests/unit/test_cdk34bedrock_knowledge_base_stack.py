import re

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk34bedrock_knowledge_base.cdk34bedrock_knowledge_base_stack import Cdk34BedrockKnowledgeBaseStack
from cdk34bedrock_knowledge_base.tags import TAGS, apply_tags

TITAN = "arn:aws:bedrock:eu-central-1::foundation-model/amazon.titan-embed-text-v2:0"
INDEX_ARN = {"Fn::GetAtt": ["Index", "IndexArn"]}
KB_ARN = {"Fn::GetAtt": ["KnowledgeBase", "KnowledgeBaseArn"]}
CHAT_PROFILE = {"Fn::GetAtt": ["ChatProfile", "InferenceProfileArn"]}

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::ApiGatewayV2::Integration", "AWS::ApiGatewayV2::Route", "AWS::Bedrock::DataSource",
    "AWS::CloudFront::OriginAccessControl", "AWS::IAM::Policy", "AWS::Lambda::LayerVersion",
    "AWS::Lambda::Permission", "AWS::S3::BucketPolicy", "AWS::SQS::QueuePolicy",
}


def template():
    app = core.App()
    apply_tags(app)
    stack = Cdk34BedrockKnowledgeBaseStack(app, "cdk34-kb", env=core.Environment(account="123456789012", region="eu-central-1"))
    return assertions.Template.from_stack(stack)


def statements(t, logical_prefix):
    """Statement delle policy (inline nei ruoli o AWS::IAM::Policy) il cui ID logico inizia con logical_prefix."""
    found = []
    for logical_id, policy in t.find_resources("AWS::IAM::Policy").items():
        if logical_id.startswith(logical_prefix):
            found.extend(policy["Properties"]["PolicyDocument"]["Statement"])
    for logical_id, role in t.find_resources("AWS::IAM::Role").items():
        if logical_id.startswith(logical_prefix):
            for p in role["Properties"].get("Policies", []):
                found.extend(p["PolicyDocument"]["Statement"])
    return found


def test_vector_index_for_knowledge_base():
    """Testo e metadati di Bedrock non filtrabili: filtrabili supererebbero i 2 KB per vettore."""
    t = template()
    t.has_resource_properties("AWS::S3Vectors::VectorBucket", {"VectorBucketName": "alnao-dev-cdk-cdk34bedrockknowledgebase-vectors"})
    t.has_resource_properties("AWS::S3Vectors::Index", {
        "IndexName": "docs", "DataType": "float32", "Dimension": 1024, "DistanceMetric": "cosine",
        "MetadataConfiguration": {"NonFilterableMetadataKeys": ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]},
    })


def test_knowledge_base_and_data_source():
    t = template()
    t.has_resource_properties("AWS::Bedrock::KnowledgeBase", {
        "Name": "Cdk34BedrockKnowledgeBase",
        "KnowledgeBaseConfiguration": {"Type": "VECTOR", "VectorKnowledgeBaseConfiguration": {
            "EmbeddingModelArn": TITAN,
            "EmbeddingModelConfiguration": {"BedrockEmbeddingModelConfiguration": {"Dimensions": 1024, "EmbeddingDataType": "FLOAT32"}},
        }},
        "StorageConfiguration": {"Type": "S3_VECTORS", "S3VectorsConfiguration": {"IndexArn": INDEX_ARN}},
    })
    t.has_resource_properties("AWS::Bedrock::DataSource", {
        "DataDeletionPolicy": "DELETE",
        "DataSourceConfiguration": {"Type": "S3", "S3Configuration": assertions.Match.object_like({"InclusionPrefixes": ["uploads/"]})},
        "VectorIngestionConfiguration": {"ChunkingConfiguration": {
            "ChunkingStrategy": "FIXED_SIZE", "FixedSizeChunkingConfiguration": {"MaxTokens": 300, "OverlapPercentage": 20}}},
    })


def test_knowledge_base_role():
    """Ruolo assumibile solo da Bedrock per le Knowledge Base dell'account, con le policy inline nel ruolo."""
    t = template()
    t.has_resource_properties("AWS::IAM::Role", {
        "RoleName": "cdk34-kb-KnowledgeBaseServiceRole",
        "AssumeRolePolicyDocument": {"Statement": [assertions.Match.object_like({
            "Principal": {"Service": "bedrock.amazonaws.com"},
            "Condition": {"StringEquals": {"aws:SourceAccount": "123456789012"},
                          "ArnLike": {"aws:SourceArn": "arn:aws:bedrock:eu-central-1:123456789012:knowledge-base/*"}},
        })]},
    })
    found = statements(t, "KnowledgeBaseRole")
    by_action = {str(s["Action"]): s["Resource"] for s in found}
    assert by_action["bedrock:InvokeModel"] == TITAN
    assert by_action[str(["s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:DeleteVectors",
                          "s3vectors:QueryVectors", "s3vectors:GetIndex"])] == INDEX_ARN
    assert "s3:GetObject" in by_action and "s3:ListBucket" in by_action
    # nessuna AWS::IAM::Policy separata: la Knowledge Base deve trovare i permessi gia' alla creazione
    assert not [k for k in t.find_resources("AWS::IAM::Policy") if k.startswith("KnowledgeBaseRole")]


def test_chat_profile_and_api_permissions():
    """Le risposte passano dal profilo con i tag; l'Api usa la Knowledge Base e solo il modello di chat."""
    t = template()
    t.has_resource_properties("AWS::Bedrock::ApplicationInferenceProfile", {
        "InferenceProfileName": "Cdk34BedrockKnowledgeBase-Chat",
        "ModelSource": {"CopyFrom": "arn:aws:bedrock:eu-central-1:123456789012:inference-profile/eu.amazon.nova-lite-v1:0"},
    })
    for p in t.find_resources("AWS::Bedrock::ApplicationInferenceProfile").values():
        for prop in ("InferenceProfileName", "Description"):
            assert re.fullmatch(r"([0-9a-zA-Z:.][ _-]?)+", p["Properties"][prop]), p["Properties"][prop]
    t.has_resource_properties("AWS::Lambda::Function", {
        "Handler": "api.handler", "Environment": {"Variables": assertions.Match.object_like({"CHAT_MODEL": CHAT_PROFILE})}})
    api = {str(s["Action"]): s["Resource"] for s in statements(t, "ApiServiceRole")}
    assert api[str(["bedrock:Retrieve", "bedrock:StartIngestionJob", "bedrock:ListIngestionJobs",
                    "bedrock:ListKnowledgeBaseDocuments"])] == KB_ARN
    assert api["bedrock:InvokeModel"][0] == CHAT_PROFILE
    assert all("nova-lite" in str(r) for r in api["bedrock:InvokeModel"][1:])
    sync = {str(s["Action"]): s["Resource"] for s in statements(t, "SyncServiceRole")}
    assert sync["bedrock:StartIngestionJob"] == KB_ARN


def test_sync_queue():
    """Eventi S3 di uploads/ in coda SQS, letti a gruppi dalla Lambda Sync; dopo 30 tentativi nella coda degli errori."""
    t = template()
    t.has_resource_properties("AWS::SQS::Queue", {
        "QueueName": "Cdk34BedrockKnowledgeBase-Sync", "VisibilityTimeout": 120,
        "RedrivePolicy": assertions.Match.object_like({"maxReceiveCount": 30})})
    t.has_resource_properties("AWS::SQS::Queue", {"QueueName": "Cdk34BedrockKnowledgeBase-SyncFailed"})
    t.has_resource_properties("AWS::Lambda::EventSourceMapping", {
        "BatchSize": 100, "MaximumBatchingWindowInSeconds": 20, "ScalingConfig": {"MaximumConcurrency": 2}})
    notifications = t.find_resources("Custom::S3BucketNotifications")
    configs = [c for n in notifications.values() for c in n["Properties"]["NotificationConfiguration"].get("QueueConfigurations", [])]
    assert sorted(c["Events"][0] for c in configs) == ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    assert all(c["Filter"]["Key"]["FilterRules"] == [{"Name": "prefix", "Value": "uploads/"}] for c in configs)
    # la coda deve restare nascosta piu' a lungo della Lambda che la legge
    sync_fn = next(iter(t.find_resources("AWS::Lambda::Function", {"Properties": {"Handler": "sync.handler"}}).values()))
    assert sync_fn["Properties"]["Timeout"] < 120


def test_api_and_site():
    t = template()
    t.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "ANY /api/{proxy+}"})
    t.has_resource_properties("AWS::CloudFront::Distribution", {
        "DistributionConfig": assertions.Match.object_like({
            "DefaultRootObject": "index.html",
            "CacheBehaviors": [assertions.Match.object_like({"PathPattern": "/api/*"})],
        }),
    })
    t.has_resource_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True,
                                           "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
    })


def test_fixed_names():
    t = template()
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "alnao-dev-cdk-cdk34bedrockknowledgebase-documents"})
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "alnao-dev-cdk-cdk34bedrockknowledgebase-site"})
    for name in ("Api", "Sync", "BucketNotifications", "AutoDeleteObjects", "BucketDeployment"):
        t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": f"Cdk34BedrockKnowledgeBase-{name}"})
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/Cdk34BedrockKnowledgeBase/{name}"})
        t.has_resource_properties("AWS::IAM::Role", {"RoleName": f"cdk34-kb-{name}ServiceRole"})
    t.has_resource_properties("AWS::SecretsManager::Secret", {"Name": "Cdk34BedrockKnowledgeBase-ApiKey"})


def test_name_lengths():
    """Nomi entro i limiti di AWS: ruoli e Lambda 64 caratteri, bucket 63 (con il nome dello stack di app.py)."""
    app = core.App()
    stack = Cdk34BedrockKnowledgeBaseStack(app, "Cdk34BedrockKnowledgeBaseStack",
                                           env=core.Environment(account="123456789012", region="eu-central-1"))
    t = assertions.Template.from_stack(stack)
    for kind, prop, limit in (("AWS::IAM::Role", "RoleName", 64), ("AWS::Lambda::Function", "FunctionName", 64),
                              ("AWS::S3::Bucket", "BucketName", 63), ("AWS::S3Vectors::VectorBucket", "VectorBucketName", 63),
                              ("AWS::SQS::Queue", "QueueName", 80)):
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

import re
import tempfile

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk32wiki_s3_vector.cdk32wiki_s3_vector_stack import Cdk32WikiS3VectorStack
from cdk32wiki_s3_vector.naming import check_template
from cdk32wiki_s3_vector.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::ApiGatewayV2::Integration", "AWS::ApiGatewayV2::Route", "AWS::CloudFront::OriginAccessControl",
    "AWS::IAM::Policy", "AWS::Lambda::LayerVersion", "AWS::Lambda::Permission", "AWS::S3::BucketPolicy",
}


STACK_NAME = "aws-py-cdk32"


def template():
    app = core.App()
    apply_tags(app)
    # cartella vuota al posto del layer creato da build_layer.sh
    stack = Cdk32WikiS3VectorStack(app, STACK_NAME, layer_dir=tempfile.mkdtemp(),
                                   env=core.Environment(account="123456789012", region="eu-central-1"))
    return assertions.Template.from_stack(stack)


def test_vector_index():
    t = template()
    t.has_resource_properties("AWS::S3Vectors::VectorBucket", {"VectorBucketName": "aws-py-cdk32-vectors"})
    t.has_resource_properties("AWS::S3Vectors::Index", {
        "IndexName": "aws-py-cdk32-wiki", "DataType": "float32", "Dimension": 1024, "DistanceMetric": "cosine",
        "MetadataConfiguration": {"NonFilterableMetadataKeys": ["text"]},
    })


def test_lambdas_and_names():
    t = template()
    names = {f["Properties"]["FunctionName"] for f in t.find_resources("AWS::Lambda::Function").values()}
    assert names == {"aws-py-cdk32-api", "aws-py-cdk32-ingest", "aws-py-cdk32-bucket-notifications-handler",
                     "aws-py-cdk32-s3-auto-delete-objects-handler", "aws-py-cdk32-cdk-bucket-deployment"}
    for name in names:
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/aws/lambda/{name}"})
    for role in t.find_resources("AWS::IAM::Role").values():
        assert role["Properties"]["RoleName"].startswith("aws-py-cdk32-") and role["Properties"]["RoleName"].endswith("-eu-central-1")
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "aws-py-cdk32-files-123456789012"})
    t.has_resource_properties("AWS::S3::Bucket", {"BucketName": "aws-py-cdk32-site-123456789012"})


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
        "InferenceProfileName": "aws-py-cdk32-embedding", "ModelSource": {"CopyFrom": titan}})
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


def test_lambdas_cannot_create_log_groups():
    """Al destroy le ultime righe di log arrivano dopo la cancellazione del log group: senza
    logs:CreateLogGroup Lambda non puo' ricrearlo senza tag e senza scadenza."""
    t = template()
    roles = t.find_resources("AWS::IAM::Role")
    policies = t.find_resources("AWS::IAM::Policy")
    for fn in t.find_resources("AWS::Lambda::Function").values():
        role_id = fn["Properties"]["Role"]["Fn::GetAtt"][0]
        role = roles[role_id]["Properties"]
        assert "ManagedPolicyArns" not in role, role_id
        statements = [s for p in role.get("Policies", []) for s in p["PolicyDocument"]["Statement"]]
        statements += [s for p in policies.values() if {"Ref": role_id} in p["Properties"]["Roles"]
                       for s in p["Properties"]["PolicyDocument"]["Statement"]]
        assert not [s for s in statements if "logs:CreateLogGroup" in str(s["Action"]) or s["Action"] in ("logs:*", "*")]
        log_group = fn["Properties"]["LoggingConfig"]["LogGroup"]["Ref"]  # il proprio log group, e solo quello
        assert {"Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": {"Fn::GetAtt": [log_group, "Arn"]}} in statements


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk32-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
    region) e ha il tag Name uguale al nome; le risorse senza nome (EC2, EFS, CloudFront, ...) hanno solo il tag Name."""
    assert check_template(template().to_json(), STACK_NAME) == []


def test_stack_tags(monkeypatch):
    """Lo stack CloudFormation ha i tag standard e Name uguale al suo nome: CDK li passa allo stack al deploy e
    CloudFormation li copia sulle risorse che non li hanno gia' (il Name scritto sulla risorsa vince)."""
    stacks, from_stack = [], assertions.Template.from_stack
    monkeypatch.setattr(assertions.Template, "from_stack",
                        staticmethod(lambda stack, *args, **kwargs: stacks.append(stack) or from_stack(stack, *args, **kwargs)))
    template()
    assert stacks[0].tags.tag_values() == {**TAGS, "Name": STACK_NAME}

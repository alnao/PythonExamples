import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk26blockchain_lambda.cdk26blockchain_lambda_stack import Cdk26BlockchainLambdaStack
from cdk26blockchain_lambda.naming import check_template
from cdk26blockchain_lambda.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::ApiGateway::Account", "AWS::ApiGateway::Deployment", "AWS::ApiGateway::Method", "AWS::ApiGateway::Resource",
    "AWS::CloudFront::OriginAccessControl", "AWS::IAM::Policy", "AWS::Lambda::LayerVersion",
    "AWS::Lambda::Permission", "AWS::S3::BucketPolicy",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk26"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk26BlockchainLambdaStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    for key in ("Tags", "TableTags"):
        if key in props:
            tags = props[key]
            return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}
    for replica in props.get("Replicas", []):
        return {t["Key"]: t["Value"] for t in replica.get("Tags", [])}
    if "DistributionConfig" in props:
        return {t["Key"]: t["Value"] for t in props.get("Tags", [])}
    return {}


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_tables():
    t = template()
    t.has_resource_properties("AWS::DynamoDB::GlobalTable", {
        "TableName": "aws-py-cdk26-blocks",
        "KeySchema": [{"AttributeName": "chain", "KeyType": "HASH"}, {"AttributeName": "index", "KeyType": "RANGE"}],
        "BillingMode": "PAY_PER_REQUEST",
    })
    t.has_resource_properties("AWS::DynamoDB::GlobalTable", {
        "TableName": "aws-py-cdk26-transactions",
        "GlobalSecondaryIndexes": [assertions.Match.object_like({
            "IndexName": "StatusIndex",
            "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}, {"AttributeName": "timestamp", "KeyType": "RANGE"}],
        })],
    })


def test_functions_and_log_groups():
    t = template()
    functions = {f["Properties"]["FunctionName"]: f["Properties"] for f in t.find_resources("AWS::Lambda::Function").values()
                 if "FunctionName" in f["Properties"]}
    names = {"aws-py-cdk26-add-transaction", "aws-py-cdk26-mine-block", "aws-py-cdk26-get-transactions", "aws-py-cdk26-get-balances",
             "aws-py-cdk26-get-blocks", "aws-py-cdk26-validate-chain"}
    assert names <= set(functions)
    for name in names:
        assert functions[name]["Runtime"] == "python3.13" and functions[name]["Architectures"] == ["arm64"]
    assert functions["aws-py-cdk26-mine-block"]["Timeout"] == 28
    for name in names:
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/aws/lambda/{name}", "RetentionInDays": 7})


def test_least_privilege():
    """AddTransaction scrive solo transazioni, le funzioni di lettura non scrivono."""
    t = template()
    # senza la policy dei log (controllata da test_every_lambda_has_a_stack_log_group)
    policies = {k: p for k, p in t.find_resources("AWS::IAM::Policy").items()
                if not p["Properties"]["PolicyName"].endswith("-logs-policy")}

    def actions(prefix):
        result = set()
        for logical_id, p in policies.items():
            if logical_id.startswith(prefix):
                for s in p["Properties"]["PolicyDocument"]["Statement"]:
                    result.update([s["Action"]] if isinstance(s["Action"], str) else s["Action"])
        return result
    assert actions("AddTransaction") == {"dynamodb:PutItem"}
    for reader in ("GetTransactions", "GetBalances", "GetBlocks", "ValidateChain"):
        assert not {a for a in actions(reader) if a in ("dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem")}


def test_rest_api_routes_cors_and_throttling():
    t = template()
    paths = sorted(r["Properties"]["PathPart"] for r in t.find_resources("AWS::ApiGateway::Resource").values())
    assert paths == ["balances", "blocks", "mine", "transaction", "transactions", "validate"]
    methods = [m["Properties"]["HttpMethod"] for m in t.find_resources("AWS::ApiGateway::Method").values()]
    assert methods.count("OPTIONS") >= 6  # preflight CORS su ogni risorsa
    t.has_resource_properties("AWS::ApiGateway::Stage", {
        "StageName": "dev",
        "MethodSettings": [assertions.Match.object_like({"ThrottlingRateLimit": 10, "ThrottlingBurstLimit": 20})],
    })


def test_site_on_cloudfront():
    t = template()
    t.has_resource_properties("AWS::S3::Bucket", {"PublicAccessBlockConfiguration": {
        "BlockPublicAcls": True, "BlockPublicPolicy": True, "IgnorePublicAcls": True, "RestrictPublicBuckets": True}})
    t.has_resource_properties("AWS::CloudFront::Distribution", {"DistributionConfig": assertions.Match.object_like({
        "DefaultRootObject": "index.html"})})
    t.resource_count_is("Custom::CDKBucketDeployment", 1)


def test_every_lambda_has_a_stack_log_group():
    """Anche le Lambda di supporto di CDK (es. svuotamento del bucket) scrivono in un log group dello stack, con i
    tag e cancellato al destroy, e non possono crearne altri: Lambda non crea log group senza tag e senza scadenza."""
    resources = template().to_json()["Resources"]
    functions = {k: v for k, v in resources.items() if v["Type"] == "AWS::Lambda::Function"}
    for logical_id, function in functions.items():
        log_group = function["Properties"]["LoggingConfig"]["LogGroup"]
        group_id = log_group["Ref"] if "Ref" in log_group else None
        if group_id:  # log group dello stack (le Lambda dell'esempio possono avere un nome fisso)
            assert resources[group_id]["Type"] == "AWS::Logs::LogGroup", logical_id
            assert resources[group_id]["DeletionPolicy"] == "Delete", logical_id
            assert resources[group_id]["Properties"]["RetentionInDays"] == 7, logical_id
    for logical_id, role in resources.items():
        if role["Type"] == "AWS::IAM::Role":
            assert "AWSLambdaBasicExecutionRole" not in json.dumps(role["Properties"].get("ManagedPolicyArns", [])), logical_id


def test_all_resources_named():
    """Ogni risorsa si chiama aws-py-cdk26-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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

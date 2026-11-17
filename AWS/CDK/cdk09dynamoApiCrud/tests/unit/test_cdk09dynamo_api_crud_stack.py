import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk09dynamo_api_crud.cdk09dynamo_api_crud_stack import Cdk09DynamoApiCrudStack
from cdk09dynamo_api_crud.naming import check_template, kebab
from cdk09dynamo_api_crud.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare
UNTAGGABLE = {"AWS::IAM::Policy", "AWS::Lambda::Permission", "AWS::ApiGateway::Resource", "AWS::ApiGateway::Method",
              "AWS::ApiGateway::Deployment", "AWS::ApiGateway::Account"}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk09"


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk09DynamoApiCrudStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource["Properties"]
    if "Replicas" in props:  # TableV2: i tag stanno sulla replica
        props = props["Replicas"][0]
    return {t["Key"]: t["Value"] for t in props.get("Tags", [])}


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE:
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_table():
    t = template()
    t.has_resource_properties("AWS::DynamoDB::GlobalTable", {
        "TableName": "aws-py-cdk09-items", "BillingMode": "PAY_PER_REQUEST",
        "KeySchema": [{"AttributeName": "id", "KeyType": "HASH"}],
    })
    t.has_resource("AWS::DynamoDB::GlobalTable", {"DeletionPolicy": "Delete"})


def test_functions():
    t = template()
    for name, handler in (("CreateItem", "create"), ("ReadItem", "read"), ("UpdateItem", "update"), ("DeleteItem", "delete")):
        t.has_resource_properties("AWS::Lambda::Function", {
            "FunctionName": f"{STACK_NAME}-{kebab(name)}", "Handler": f"items.{handler}", "Runtime": "python3.13"})
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/aws/lambda/{STACK_NAME}-{kebab(name)}", "RetentionInDays": 7})


def test_least_privilege():
    """Ogni funzione ha solo le azioni DynamoDB della sua operazione."""
    t = template()
    actions = {}
    for policy in t.find_resources("AWS::IAM::Policy").values():
        if policy["Properties"]["PolicyName"].endswith("-logs-policy"):
            continue  # permessi sui log, controllati da test_every_lambda_has_a_stack_log_group
        role = policy["Properties"]["Roles"][0]["Ref"]
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            action = statement["Action"]
            actions[role.split("ServiceRole")[0]] = sorted(action if isinstance(action, list) else [action])
    assert actions == {
        "CreateItem": ["dynamodb:PutItem"],
        "ReadItem": ["dynamodb:GetItem", "dynamodb:Scan"],
        "UpdateItem": ["dynamodb:UpdateItem"],
        "DeleteItem": ["dynamodb:DeleteItem"],
    }


def test_api_routes():
    t = template()
    methods = {m["Properties"]["HttpMethod"] for m in t.find_resources("AWS::ApiGateway::Method").values()}
    assert methods == {"GET", "POST", "PUT", "DELETE"}
    t.resource_count_is("AWS::ApiGateway::Method", 5)
    t.has_resource_properties("AWS::ApiGateway::Stage", {"StageName": "dev"})


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
    """Ogni risorsa si chiama aws-py-cdk09-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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

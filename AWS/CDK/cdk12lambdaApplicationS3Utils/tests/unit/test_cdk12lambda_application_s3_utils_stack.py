import json
import tempfile
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk12lambda_application_s3_utils.cdk12lambda_application_s3_utils_stack import Cdk12LambdaApplicationS3UtilsStack
from cdk12lambda_application_s3_utils.naming import check_template, kebab
from cdk12lambda_application_s3_utils.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::IAM::Policy", "AWS::S3::BucketPolicy", "AWS::SNS::TopicPolicy", "AWS::SNS::Subscription",
    "AWS::Lambda::Permission", "AWS::Lambda::EventInvokeConfig", "AWS::Lambda::LayerVersion",
    "AWS::ApiGateway::Resource", "AWS::ApiGateway::Method", "AWS::ApiGateway::Deployment", "AWS::ApiGateway::Account",
    "AWS::CloudFront::OriginAccessControl", "AWS::SecretsManager::SecretTargetAttachment",
    "AWS::EC2::SecurityGroupEgress",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk12"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template(**context):
    app = core.App(context={**CDK_CONTEXT, **context})
    apply_tags(app)
    # nei test il layer e' una cartella vuota: quella vera la crea build_layer.sh
    stack = Cdk12LambdaApplicationS3UtilsStack(app, STACK_NAME, env=ENV, layer_dir=tempfile.mkdtemp())
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource["Properties"]
    if "Replicas" in props:  # TableV2: i tag stanno sulla replica
        props = props["Replicas"][0]
    tags = props.get("Tags", [])
    return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}


def test_all_resources_tagged():
    t = template(sftp_host="sftp.example.com", alarm_email="prova@example.com")
    for logical_id, resource in t.to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_private_bucket_with_eventbridge_and_cors():
    t = template()
    t.has_resource_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {"BlockPublicAcls": True, "BlockPublicPolicy": True,
                                           "IgnorePublicAcls": True, "RestrictPublicBuckets": True},
        "CorsConfiguration": {"CorsRules": [assertions.Match.object_like({"AllowedMethods": ["PUT", "GET"]})]},
    })
    t.has_resource_properties("Custom::S3BucketNotifications", {
        "NotificationConfiguration": {"EventBridgeConfiguration": {}}})


def test_aurora_serverless_with_data_api():
    """Database in pausa a 0 ACU e Data API: le Lambda non stanno nella VPC (niente endpoint a pagamento)."""
    t = template()
    t.has_resource_properties("AWS::RDS::DBCluster", {
        "Engine": "aurora-mysql", "EnableHttpEndpoint": True, "DatabaseName": "es12db", "StorageEncrypted": True,
        "ServerlessV2ScalingConfiguration": {"MinCapacity": 0, "MaxCapacity": 2, "SecondsUntilAutoPause": 300},
    })
    t.resource_count_is("AWS::EC2::VPCEndpoint", 0)
    for function in t.find_resources("AWS::Lambda::Function").values():
        assert "VpcConfig" not in function["Properties"]


def test_tables():
    t = template()
    t.has_resource_properties("AWS::DynamoDB::GlobalTable", {"TableName": "aws-py-cdk12-log", "BillingMode": "PAY_PER_REQUEST"})
    scan = next(v for v in t.find_resources("AWS::DynamoDB::GlobalTable").values()
                if v["Properties"]["TableName"] == "aws-py-cdk12-scan")["Properties"]
    assert sorted(i["IndexName"] for i in scan["GlobalSecondaryIndexes"]) == ["nomeFile-index", "nuovo-index"]


def test_functions_and_log_groups():
    t = template()
    names = {"Decompress", "ConvertToCsv", "ProcessCsv", "ReadRdsData", "UploadZip", "ListExcelFiles",
             "DownloadExcelFile", "ReadDynamoDbData", "ListNewFiles", "FindFile", "ScanS3"}
    functions = {f["Properties"]["FunctionName"]: f["Properties"] for f in t.find_resources("AWS::Lambda::Function").values()
                 if "FunctionName" in f["Properties"]}
    assert {f"{STACK_NAME}-{kebab(n)}" for n in names} <= set(functions)
    assert "aws-py-cdk12-send-sftp" not in functions  # SFTP solo con -c sftp_host=...
    for name in names:
        assert functions[f"{STACK_NAME}-{kebab(name)}"]["Runtime"] == "python3.13"
        t.has_resource_properties("AWS::Logs::LogGroup", {"LogGroupName": f"/aws/lambda/{STACK_NAME}-{kebab(name)}", "RetentionInDays": 7})
    assert len(functions["aws-py-cdk12-convert-to-csv"]["Layers"]) == 1
    t.has_resource_properties("AWS::Lambda::EventInvokeConfig", {"MaximumRetryAttempts": 0})


def test_rules():
    t = template()
    patterns = {r["Properties"]["Name"]: r["Properties"].get("EventPattern") for r in t.find_resources("AWS::Events::Rule").values()}
    assert patterns["aws-py-cdk12-decompress"]["detail"]["object"]["key"][0] == {"wildcard": "INPUT/*.zip"}
    assert patterns["aws-py-cdk12-convert-to-csv"]["detail"]["object"]["key"] == [{"wildcard": "DEZIPPED/*.xlsx"}]
    assert patterns["aws-py-cdk12-process-csv"]["detail"]["object"]["key"] == [{"wildcard": "CSV/*.csv"}]
    t.has_resource_properties("AWS::Events::Rule", {"Name": "aws-py-cdk12-scan-s3", "ScheduleExpression": "cron(0 1 * * ? *)"})


def test_sftp_optional():
    t = template(sftp_host="sftp.example.com", sftp_user="alberto", sftp_key_param="/cdk12/chiave")
    t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": "aws-py-cdk12-send-sftp", "Environment": {"Variables": {
        "SFTP_HOST": "sftp.example.com", "SFTP_PORT": "22", "SFTP_USER": "alberto", "SFTP_KEY_PARAM": "/cdk12/chiave"}}})
    t.has_resource_properties("AWS::Events::Rule", {"Name": "aws-py-cdk12-send-sftp"})


def test_api_routes_and_alarms():
    t = template()
    paths = sorted(r["Properties"]["PathPart"] for r in t.find_resources("AWS::ApiGateway::Resource").values())
    assert paths == sorted(["upload-zip", "list-excel-files", "download-excel-file", "read-rds-data",
                            "read-dynamodb-data", "list-new-files", "find-file"])
    t.resource_count_is("AWS::ApiGateway::Account", 0)
    alarms = {a["Properties"]["AlarmName"] for a in t.find_resources("AWS::CloudWatch::Alarm").values()}
    assert alarms == {"aws-py-cdk12-process-csv-errors", "aws-py-cdk12-read-rds-data-errors", "aws-py-cdk12-api5xx"}


def test_default_vpc_and_subnets():
    """Per default la VPC di default della region e due sue subnet (nei test la VPC finta di CDK)."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"]) == ("s-12345", "s-67890")


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
    """Ogni risorsa si chiama aws-py-cdk12-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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

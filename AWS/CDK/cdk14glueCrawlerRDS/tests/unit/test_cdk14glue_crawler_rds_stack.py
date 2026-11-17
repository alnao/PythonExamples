import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk14glue_crawler_rds.cdk14glue_crawler_rds_stack import Cdk14GlueCrawlerRdsStack
from cdk14glue_crawler_rds.naming import check_template
from cdk14glue_crawler_rds.tags import TAGS, apply_tags

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::IAM::Policy", "AWS::S3::BucketPolicy", "AWS::EC2::SecurityGroupIngress", "AWS::EC2::SecurityGroupEgress",
    "AWS::Glue::Database", "AWS::Glue::Classifier", "AWS::Glue::Connection",
    "AWS::SecretsManager::SecretTargetAttachment",
}

# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk14"
# account e region finti: il lookup della VPC di default nei test restituisce una VPC finta
ENV = core.Environment(account="111111111111", region="eu-central-1")


def template():
    app = core.App(context=CDK_CONTEXT)
    apply_tags(app)
    stack = Cdk14GlueCrawlerRdsStack(app, STACK_NAME, env=ENV)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource["Properties"]
    tags = props.get("Tags", props.get("TagSpecifications", []))
    return tags if isinstance(tags, dict) else {t["Key"]: t["Value"] for t in tags}  # Glue: tag come mappa


def test_all_resources_tagged():
    for logical_id, resource in template().to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_s3_endpoint_only_with_route_table():
    t = template()
    t.has_resource("AWS::EC2::VPCEndpoint", {"Condition": "CreateS3Endpoint"})
    t.has_condition("CreateS3Endpoint", {"Fn::Not": [{"Fn::Equals": [{"Ref": "routetableid"}, ""]}]})


def test_database_reachable_only_from_glue():
    t = template()
    t.has_resource_properties("AWS::RDS::DBInstance", {
        "Engine": "mysql", "DBInstanceClass": "db.t4g.micro", "PubliclyAccessible": False, "StorageEncrypted": True})
    glue_sg = next(k for k, v in t.find_resources("AWS::EC2::SecurityGroup").items()
                   if v["Properties"]["GroupDescription"].startswith("Glue"))
    db_sg = next(k for k in t.find_resources("AWS::EC2::SecurityGroup") if k.startswith("DatabaseSecurityGroup"))
    rules = [r["Properties"] for r in t.find_resources("AWS::EC2::SecurityGroupIngress").values()
             if r["Properties"]["GroupId"] == {"Fn::GetAtt": [db_sg, "GroupId"]}]
    assert len(rules) == 1 and rules[0]["SourceSecurityGroupId"] == {"Fn::GetAtt": [glue_sg, "GroupId"]}
    assert "SecurityGroupIngress" not in t.find_resources("AWS::EC2::SecurityGroup")[db_sg]["Properties"]


def test_crawler_job_and_workflow():
    t = template()
    t.has_resource_properties("AWS::Glue::Crawler", {"Name": "aws-py-cdk14-crawler", "DatabaseName": "aws_py_cdk14_csv"})
    job = next(iter(t.find_resources("AWS::Glue::Job").values()))["Properties"]
    assert job["GlueVersion"] == "5.0" and job["Connections"] == {"Connections": ["aws-py-cdk14-rds"]}
    assert job["DefaultArguments"]["--job-bookmark-option"] == "job-bookmark-enable"
    assert job["DefaultArguments"]["--continuous-log-logGroup"] == "/aws-glue/jobs/aws-py-cdk14-job"
    t.has_resource_properties("AWS::Glue::Trigger", {"Type": "CONDITIONAL", "StartOnCreation": True})
    t.has_resource_properties("AWS::Glue::Workflow", {"Name": "aws-py-cdk14-workflow", "MaxConcurrentRuns": 1})


def test_log_groups_deleted_with_the_stack():
    t = template()
    for name in ("/aws-glue/jobs/aws-py-cdk14-job", "/aws/vendedlogs/states/aws-py-cdk14-runner"):
        t.has_resource("AWS::Logs::LogGroup", {"DeletionPolicy": "Delete", "Properties": assertions.Match.object_like(
            {"LogGroupName": name, "RetentionInDays": 7})})


def test_csv_upload_starts_state_machine():
    t = template()
    bucket_id = next(iter(t.find_resources("AWS::S3::Bucket")))
    t.has_resource_properties("AWS::Events::Rule", {"EventPattern": {
        "source": ["aws.s3"], "detail-type": ["Object Created"],
        "detail": {"bucket": {"name": [{"Ref": bucket_id}]}, "object": {"key": [{"wildcard": "INPUT/*.csv"}]}},
    }})
    definition = json.dumps(next(iter(t.find_resources("AWS::StepFunctions::StateMachine").values()))
                            ["Properties"]["DefinitionString"])
    assert "glue:startWorkflowRun" in definition and "glue:getWorkflowRun" in definition


def test_default_vpc_subnets_zone_and_route_table():
    """Per default la VPC di default della region, due sue subnet, la zona e la tabella di routing della prima."""
    params = template().to_json()["Parameters"]
    assert params["vpcid"]["Default"] == "vpc-12345"
    assert (params["subnetid1"]["Default"], params["subnetid2"]["Default"]) == ("s-12345", "s-67890")
    assert params["subnetaz1"]["Default"] == "dummy1a" and params["routetableid"]["Default"] == "rtb-12345s"


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
    """Ogni risorsa si chiama aws-py-cdk14-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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


def test_catalog_database_tagged_by_api():
    """AWS::Glue::Database non accetta Tags in CloudFormation: i tag (con Name = nome) li mette una custom resource
    che chiama glue:TagResource, con il permesso solo su quel database."""
    t = template()
    calls = [json.loads("".join(p if isinstance(p, str) else "" for p in r["Properties"]["Create"]["Fn::Join"][1]))
             if isinstance(r["Properties"]["Create"], dict) else json.loads(r["Properties"]["Create"])
             for r in t.find_resources("Custom::AWS").values()]
    assert len(calls) == 1 and calls[0]["action"] == "TagResource" and calls[0]["service"] == "Glue"
    assert calls[0]["parameters"]["TagsToAdd"] == {"Name": "aws_py_cdk14_csv", **TAGS}
    assert calls[0]["parameters"]["ResourceArn"].endswith(":database/aws_py_cdk14_csv")
    t.has_resource_properties("AWS::Lambda::Function", {"FunctionName": "aws-py-cdk14-glue-tags"})
    policy = next(p for p in t.find_resources("AWS::IAM::Policy").values()
                  if "glue:TagResource" in json.dumps(p["Properties"]["PolicyDocument"]))
    assert [s["Action"] for s in policy["Properties"]["PolicyDocument"]["Statement"]] == ["glue:TagResource"]


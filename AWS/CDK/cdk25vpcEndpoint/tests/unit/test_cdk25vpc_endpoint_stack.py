import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from cdk25vpc_endpoint.cdk25vpc_endpoint_stack import Cdk25VpcEndpointStack
from cdk25vpc_endpoint.naming import check_template
from cdk25vpc_endpoint.tags import TAGS, apply_tags

CERT = "arn:aws:acm:eu-central-1:123456789012:certificate/server"
CLIENT = "arn:aws:acm:eu-central-1:123456789012:certificate/client"
SAML = "arn:aws:iam::123456789012:saml-provider/SAMLProvider"

# Tipi che CloudFormation non permette di taggare (le Custom:: sono risorse di CDK, non di AWS)
UNTAGGABLE = {
    "AWS::EC2::ClientVpnAuthorizationRule", "AWS::EC2::ClientVpnTargetNetworkAssociation", "AWS::EC2::Route",
    "AWS::EC2::SubnetRouteTableAssociation", "AWS::EC2::VPCEndpoint", "AWS::EC2::VPCGatewayAttachment",
    "AWS::IAM::Policy",
}


# feature flag di cdk.json, come li passa la CLI a cdk synth/deploy
CDK_CONTEXT = json.loads((Path(__file__).parents[2] / "cdk.json").read_text())["context"]
STACK_NAME = "aws-py-cdk25"


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk25VpcEndpointStack(app, STACK_NAME)
    return assertions.Template.from_stack(stack)


def tags_of(resource):
    props = resource.get("Properties", {})
    if "Tags" in props:
        return {t["Key"]: t["Value"] for t in props["Tags"]}
    for spec in props.get("TagSpecifications", []):
        return {t["Key"]: t["Value"] for t in spec["Tags"]}
    return {}


@pytest.mark.parametrize("context", [{}, {"server_certificate_arn": CERT, "client_certificate_arn": CLIENT}])
def test_all_resources_tagged(context):
    for logical_id, resource in template(context).to_json()["Resources"].items():
        if resource["Type"] in UNTAGGABLE or resource["Type"].startswith("Custom::"):
            continue
        tags = tags_of(resource)
        assert tags == {**tags, **TAGS}, f"{logical_id} ({resource['Type']}) senza i tag standard"


def test_vpc_subnets_and_no_nat():
    t = template()
    t.has_resource_properties("AWS::EC2::VPC", {"CidrBlock": "10.184.0.0/16"})
    cidrs = sorted(s["Properties"]["CidrBlock"] for s in t.find_resources("AWS::EC2::Subnet").values())
    assert cidrs == ["10.184.0.0/24", "10.184.1.0/24", "10.184.2.0/24", "10.184.3.0/24"]
    t.resource_count_is("AWS::EC2::NatGateway", 0)


def test_gateway_endpoints():
    t = template()
    endpoints = t.find_resources("AWS::EC2::VPCEndpoint")
    assert len(endpoints) == 2
    for e in endpoints.values():
        assert e["Properties"]["VpcEndpointType"] == "Gateway"
        assert len(e["Properties"]["RouteTableIds"]) == 4  # tutte le subnet, pubbliche e private


def test_flow_log_rejected_traffic():
    t = template()
    t.has_resource_properties("AWS::EC2::FlowLog", {"TrafficType": "REJECT", "LogDestinationType": "cloud-watch-logs"})
    t.has_resource_properties("AWS::Logs::LogGroup", {"RetentionInDays": 7})


def test_no_client_vpn_by_default():
    template().resource_count_is("AWS::EC2::ClientVpnEndpoint", 0)


def test_client_vpn_with_certificates():
    t = template({"server_certificate_arn": CERT, "client_certificate_arn": CLIENT})
    t.has_resource_properties("AWS::EC2::ClientVpnEndpoint", {
        "ClientCidrBlock": "10.185.0.0/22", "ServerCertificateArn": CERT, "SplitTunnel": True,
        "TransportProtocol": "tcp", "DnsServers": ["10.184.0.2"],
        "AuthenticationOptions": [{"Type": "certificate-authentication",
                                   "MutualAuthentication": {"ClientRootCertificateChainArn": CLIENT}}],
        "ConnectionLogOptions": assertions.Match.object_like({"Enabled": True}),
    })
    t.resource_count_is("AWS::EC2::ClientVpnTargetNetworkAssociation", 2)
    t.has_resource_properties("AWS::EC2::ClientVpnAuthorizationRule", {
        "TargetNetworkCidr": {"Fn::GetAtt": [assertions.Match.string_like_regexp("Vpc"), "CidrBlock"]},
        "AuthorizeAllGroups": True})


def test_client_vpn_with_saml():
    t = template({"server_certificate_arn": CERT, "saml_provider_arn": SAML})
    t.has_resource_properties("AWS::EC2::ClientVpnEndpoint", {
        "AuthenticationOptions": [{"Type": "federated-authentication",
                                   "FederatedAuthentication": {"SAMLProviderArn": SAML}}],
    })


def test_client_vpn_needs_authentication():
    with pytest.raises(Exception):
        template({"server_certificate_arn": CERT})


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
    """Ogni risorsa si chiama aws-py-cdk25-<servizio> (bucket S3 con l'account alla fine, ruoli IAM con la
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

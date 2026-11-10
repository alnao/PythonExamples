import json
from pathlib import Path

import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from cdk25vpc_endpoint.cdk25vpc_endpoint_stack import Cdk25VpcEndpointStack
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


def template(context=None):
    app = core.App(context={**CDK_CONTEXT, **(context or {})})
    apply_tags(app)
    stack = Cdk25VpcEndpointStack(app, "cdk25")
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

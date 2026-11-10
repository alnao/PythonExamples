"""VPC completa con endpoint gateway e, se configurato, un Client VPN endpoint.

- VPC 10.184.0.0/16 su due zone: subnet pubbliche (10.184.0-1.0/24) e private isolate (10.184.2-3.0/24),
  senza NAT gateway (le subnet private non escono su Internet)
- endpoint gateway per S3 e DynamoDB (gratuiti): tutte le subnet raggiungono i due servizi senza Internet
- Client VPN endpoint per entrare nella VPC dal proprio PC, creato solo con il certificato server ACM
  (-c server_certificate_arn=...) e un'autenticazione: certificato client (-c client_certificate_arn=...)
  oppure SAML (-c saml_provider_arn=... e facoltativo -c self_service_saml_provider_arn=...)

Il Client VPN costa circa 0,10 $/ora per ogni subnet associata anche senza connessioni: per questo e' facoltativo.
"""

from aws_cdk import (
    CfnOutput,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct

from .tags import TAGS

VPC_CIDR = "10.184.0.0/16"
CLIENT_CIDR = "10.185.0.0/22"  # indirizzi dati ai client VPN: non devono sovrapporsi alla VPC


class Cdk25VpcEndpointStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(self, "Vpc", ip_addresses=ec2.IpAddresses.cidr(VPC_CIDR), max_azs=2, nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED, cidr_mask=24),
            ],
            gateway_endpoints={
                "S3": ec2.GatewayVpcEndpointOptions(service=ec2.GatewayVpcEndpointAwsService.S3),
                "DynamoDB": ec2.GatewayVpcEndpointOptions(service=ec2.GatewayVpcEndpointAwsService.DYNAMODB),
            })

        # Flow log della VPC: traffico rifiutato, utile per capire cosa bloccano i security group
        flow_logs = logs.LogGroup(self, "FlowLogs", log_group_name=f"/vpc/{self.stack_name}/flow-logs",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        self.vpc.add_flow_log("FlowLog", destination=ec2.FlowLogDestination.to_cloud_watch_logs(flow_logs),
                              traffic_type=ec2.FlowLogTrafficType.REJECT)

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        CfnOutput(self, "PublicSubnets", value=",".join(s.subnet_id for s in self.vpc.public_subnets))
        CfnOutput(self, "PrivateSubnets", value=",".join(s.subnet_id for s in self.vpc.isolated_subnets))

        server_cert = self.node.try_get_context("server_certificate_arn")
        if server_cert:
            self._client_vpn(server_cert)

    def _client_vpn(self, server_cert: str) -> None:
        client_cert = self.node.try_get_context("client_certificate_arn")
        saml = self.node.try_get_context("saml_provider_arn")
        if not client_cert and not saml:
            raise ValueError("Client VPN: serve -c client_certificate_arn=... oppure -c saml_provider_arn=...")

        user_auth = None
        if saml:
            self_service = self.node.try_get_context("self_service_saml_provider_arn")
            user_auth = ec2.ClientVpnUserBasedAuthentication.federated(
                iam.SamlProvider.from_saml_provider_arn(self, "SamlProvider", saml),
                iam.SamlProvider.from_saml_provider_arn(self, "SelfServiceSamlProvider", self_service) if self_service else None)

        log_group = logs.LogGroup(self, "ClientVpnLogs", log_group_name=f"/vpn/{self.stack_name}/connections",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        security_group = ec2.SecurityGroup(self, "ClientVpnSecurityGroup", vpc=self.vpc,
                                           description="Client VPN endpoint", allow_all_outbound=True)
        endpoint = self.vpc.add_client_vpn_endpoint("ClientVpn",
            cidr=CLIENT_CIDR,
            server_certificate_arn=server_cert,
            client_certificate_arn=client_cert,
            user_based_authentication=user_auth,
            self_service_portal=bool(saml and self.node.try_get_context("self_service_saml_provider_arn")),
            # split tunnel: nella VPN passa solo il traffico verso la VPC, il resto esce dalla rete del client
            split_tunnel=True,
            transport_protocol=ec2.TransportProtocol.TCP,
            dns_servers=["10.184.0.2"],  # resolver Amazon della VPC (indirizzo base + 2)
            log_group=log_group,
            security_groups=[security_group],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            authorize_all_users_to_vpc_cidr=True,
            description=f"Client VPN {self.stack_name}",
        )
        # CloudFormation non accetta Tags sul Client VPN endpoint: i tag vanno in TagSpecifications
        cfn = endpoint.node.default_child
        cfn.add_property_override("TagSpecifications", [{
            "ResourceType": "client-vpn-endpoint",
            "Tags": [{"Key": k, "Value": v} for k, v in TAGS.items()],
        }])

        CfnOutput(self, "ClientVpnEndpointId", value=endpoint.endpoint_id)
        CfnOutput(self, "ClientVpnConfigCommand",
                  value=f"aws ec2 export-client-vpn-client-configuration --client-vpn-endpoint-id {endpoint.endpoint_id}"
                        f" --region {self.region} --output text > cdk25-client.ovpn")

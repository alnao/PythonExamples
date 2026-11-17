"""Istanza EC2 con un indirizzo IP pubblico fisso (Elastic IP).

- interfaccia di rete (ENI) creata dallo stack, con i tag standard, nella subnet pubblica indicata
- istanza EC2 Amazon Linux 2023 con Apache e una pagina di prova, collegata a quella interfaccia
- Elastic IP associato all'interfaccia di rete: l'indirizzo resta lo stesso se l'istanza viene fermata,
  riavviata o sostituita (basta collegare la stessa interfaccia, o riassociare l'IP)
- nessuna porta SSH: si entra con Session Manager

L'istanza usa le risorse L1 (CfnInstance, CfnNetworkInterface): con l'interfaccia di rete creata a parte
l'Elastic IP non dipende dall'istanza e l'interfaccia ha i tag (quella creata da EC2 con l'istanza no).
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Fn,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

INSTANCE_TYPES = ["t3.nano", "t3.micro", "t3.small", "t3.medium"]

USER_DATA = r"""#!/bin/bash
set -Eeuxo pipefail
trap 'echo "ERRORE cdk17: comando fallito alla riga $LINENO: $BASH_COMMAND" | tee /dev/console >&2' ERR
# l'Elastic IP puo' essere associato qualche secondo dopo l'avvio: dnf riprova finche' la rete non esce su Internet
for i in $(seq 1 30); do dnf install -y httpd && break; sleep 10; done
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
cat > /var/www/html/index.html <<HTML
<html><body><h1>Esempio cdk17 Elastic IP</h1>
<p>Istanza $INSTANCE_ID in $AZ, avviata il $(date)</p>
<p>L'indirizzo IP resta lo stesso anche dopo stop e start dell'istanza.</p></body></html>
HTML
systemctl enable --now httpd
"""


class Cdk17ElasticIpStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC e subnet: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 1)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_id = subnet_parameter(self, "subnetid", default_subnets[0], "subnet pubblica (con rotta verso l'Internet gateway)")
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo dell'istanza").value_as_string

        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=[Fn.select(0, Fn.get_azs())])
        security_group = ec2.SecurityGroup(self, "WebSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                           description="Pagina web di prova: HTTP da Internet, niente SSH")
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP da Internet")

        # Interfaccia di rete dello stack: ha i tag e porta l'Elastic IP
        self.network_interface = ec2.CfnNetworkInterface(self, "NetworkInterface", subnet_id=subnet_id,
            group_set=[security_group.security_group_id], description="cdk17: interfaccia con Elastic IP")

        role = iam.Role(self, "InstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")])
        profile = iam.CfnInstanceProfile(self, "InstanceProfile", roles=[role.role_name])

        self.instance = ec2.CfnInstance(self, "Instance",
            image_id=ec2.MachineImage.latest_amazon_linux2023().get_image(self).image_id,
            instance_type=instance_type,
            iam_instance_profile=profile.ref,
            network_interfaces=[ec2.CfnInstance.NetworkInterfaceProperty(
                device_index="0", network_interface_id=self.network_interface.ref)],
            block_device_mappings=[ec2.CfnInstance.BlockDeviceMappingProperty(device_name="/dev/xvda",
                ebs=ec2.CfnInstance.EbsProperty(volume_size=8, volume_type="gp3", encrypted=True, delete_on_termination=True))],
            propagate_tags_to_volume_on_creation=True,  # i tag dell'istanza anche sul disco
            metadata_options=ec2.CfnInstance.MetadataOptionsProperty(http_tokens="required", http_endpoint="enabled"),
            user_data=Fn.base64(USER_DATA))

        # Elastic IP: allocato dallo stack e associato all'interfaccia di rete
        self.eip = ec2.CfnEIP(self, "ElasticIp", domain="vpc")
        ec2.CfnEIPAssociation(self, "ElasticIpAssociation", allocation_id=self.eip.attr_allocation_id,
                              network_interface_id=self.network_interface.ref)

        CfnOutput(self, "ElasticIpAddress", value=self.eip.attr_public_ip)
        CfnOutput(self, "AllocationId", value=self.eip.attr_allocation_id)
        CfnOutput(self, "WebsiteUrl", value=f"http://{self.eip.attr_public_ip}/")
        CfnOutput(self, "InstanceId", value=self.instance.ref)
        CfnOutput(self, "NetworkInterfaceId", value=self.network_interface.ref)

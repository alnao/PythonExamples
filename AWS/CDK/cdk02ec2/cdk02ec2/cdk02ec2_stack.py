"""Istanza EC2 Amazon Linux 2023 in una subnet pubblica, gestita con Session Manager.

- istanza t3.micro (parametrica) con IP pubblico, disco gp3 cifrato, IMDSv2 obbligatorio
- nessuna porta aperta in ingresso e nessuna key pair: si entra con Session Manager
- l'interfaccia di rete e il disco li crea EC2 all'avvio: i tag arrivano da un launch template collegato
  all'istanza (TagSpecifications per instance, volume e network-interface, aggiunte da tags.py)

L'istanza usa la risorsa L1 CfnInstance: il costrutto L2 ec2.Instance non accetta un launch template e,
con la VPC importata da parametri, vorrebbe conoscere la zona della subnet.
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
)
from constructs import Construct

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

INSTANCE_TYPES = ["t3.nano", "t3.micro", "t3.small", "t3.medium"]


class Cdk02Ec2Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC e subnet: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_id = subnet_parameter(self, "subnetid", lookup_subnets(default_vpc, 1)[0],
                                     "subnet pubblica (con rotta verso l'Internet gateway)")
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo dell'istanza").value_as_string

        # Security group senza regole in ingresso: Session Manager usa solo connessioni in uscita
        security_group = ec2.CfnSecurityGroup(self, "SecurityGroup", vpc_id=vpc_id,
            group_description="Istanza cdk02: nessuna porta in ingresso (Session Manager)",
            security_group_egress=[ec2.CfnSecurityGroup.EgressProperty(ip_protocol="-1", cidr_ip="0.0.0.0/0")])

        role = iam.Role(self, "InstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")])
        profile = iam.CfnInstanceProfile(self, "InstanceProfile", roles=[role.role_name])

        # Launch template usato solo per i tag di disco e interfaccia di rete creati all'avvio
        launch_template = ec2.LaunchTemplate(self, "InstanceTemplate")

        self.instance = ec2.CfnInstance(self, "Instance",
            image_id=ec2.MachineImage.latest_amazon_linux2023().get_image(self).image_id,
            instance_type=instance_type,
            iam_instance_profile=profile.ref,
            launch_template=ec2.CfnInstance.LaunchTemplateSpecificationProperty(
                launch_template_id=launch_template.launch_template_id,
                version=launch_template.latest_version_number),
            network_interfaces=[ec2.CfnInstance.NetworkInterfaceProperty(
                device_index="0", subnet_id=subnet_id, group_set=[security_group.attr_group_id],
                associate_public_ip_address=True, delete_on_termination=True)],
            block_device_mappings=[ec2.CfnInstance.BlockDeviceMappingProperty(device_name="/dev/xvda",
                ebs=ec2.CfnInstance.EbsProperty(volume_size=8, volume_type="gp3", encrypted=True, delete_on_termination=True))],
            metadata_options=ec2.CfnInstance.MetadataOptionsProperty(http_tokens="required", http_endpoint="enabled"))

        CfnOutput(self, "InstanceId", value=self.instance.ref)
        CfnOutput(self, "PublicIp", value=self.instance.attr_public_ip)
        CfnOutput(self, "SessionCommand", value=f"aws ssm start-session --target {self.instance.ref} --region {self.region}")

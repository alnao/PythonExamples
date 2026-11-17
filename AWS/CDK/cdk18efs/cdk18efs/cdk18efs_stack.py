"""File system Amazon EFS montato da un'istanza EC2 come cartella del sito Apache.

- EFS cifrato con il mount target nella subnet indicata, NFS (porta 2049) aperto solo al security group dell'istanza
- istanza Amazon Linux 2023 con IP pubblico, IMDSv2, disco gp3 cifrato, Session Manager (niente SSH e key pair)
- lo script di avvio monta EFS in /var/www/html (con TLS, ripetendo finche' il DNS del mount target e' pronto),
  aggiunge una riga alla pagina condivisa e avvia Apache
- disco e interfaccia di rete creati da EC2 ricevono i tag da un launch template collegato all'istanza (come nel cdk02)

La prima versione usava Amazon Linux 2 (fuori supporto dal 30/06/2026), la zona eu-west-1b scritta nel codice,
SSH aperto a tutti, IMDSv1 e un mount senza nuovi tentativi.
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Fn,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_iam as iam,
)
from constructs import Construct

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

INSTANCE_TYPES = ["t3.nano", "t3.micro", "t3.small", "t3.medium"]

USER_DATA = r"""#!/bin/bash
set -Eeuxo pipefail
trap 'echo "ERRORE cdk18: comando fallito alla riga $LINENO: $BASH_COMMAND" | tee /dev/console >&2' ERR

# ripete un comando fino a 30 volte, 10 secondi tra un tentativo e l'altro (rete e DNS appena creati)
retry() {
  for i in $(seq 1 30); do
    "$@" && return 0
    echo "tentativo $i fallito: $*" >&2
    sleep 10
  done
  return 1
}

retry dnf install -y httpd amazon-efs-utils

# EFS come cartella del sito: il nome DNS del mount target puo' richiedere fino a 90 secondi dopo la creazione
mkdir -p /var/www/html
retry mount -t efs -o tls ${EfsId}:/ /var/www/html
echo "${EfsId}:/ /var/www/html efs _netdev,tls 0 0" >> /etc/fstab

TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
# la pagina e' su EFS: ogni istanza (e ogni riavvio dopo una sostituzione) aggiunge la sua riga
[ -f /var/www/html/index.html ] || echo "<html><body><h1>Esempio cdk18 EFS</h1>" > /var/www/html/index.html
echo "<p>Istanza $INSTANCE_ID in $AZ ha montato EFS il $(date)</p>" >> /var/www/html/index.html
chown -R apache:apache /var/www/html
systemctl enable --now httpd
"""


class Cdk18EfsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC e subnet: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 1)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_id = subnet_parameter(self, "subnetid", default_subnets[0], "subnet pubblica (istanza e mount target EFS)")
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo dell'istanza").value_as_string

        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=[Fn.select(0, Fn.get_azs())])
        subnet = ec2.Subnet.from_subnet_id(self, "Subnet", subnet_id)

        web_sg = ec2.SecurityGroup(self, "WebSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                   description="cdk18: HTTP da Internet, niente SSH")
        web_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP da Internet")
        efs_sg = ec2.SecurityGroup(self, "EfsSecurityGroup", vpc=vpc, allow_all_outbound=False,
                                   description="cdk18: NFS solo dalla istanza web")

        self.file_system = efs.FileSystem(self, "FileSystem", vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnets=[subnet]), security_group=efs_sg,
            encrypted=True, removal_policy=RemovalPolicy.DESTROY)  # esempio: al destroy si cancellano i file
        self.file_system.connections.allow_default_port_from(web_sg, "NFS dalla istanza web")

        role = iam.Role(self, "InstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")])
        self.file_system.grant_read_write(role)
        profile = iam.CfnInstanceProfile(self, "InstanceProfile", roles=[role.role_name])

        # Launch template usato solo per i tag di disco e interfaccia di rete creati all'avvio
        launch_template = ec2.LaunchTemplate(self, "WebServerTemplate")

        self.instance = ec2.CfnInstance(self, "WebServer",
            image_id=ec2.MachineImage.latest_amazon_linux2023().get_image(self).image_id,
            instance_type=instance_type,
            iam_instance_profile=profile.ref,
            launch_template=ec2.CfnInstance.LaunchTemplateSpecificationProperty(
                launch_template_id=launch_template.launch_template_id,
                version=launch_template.latest_version_number),
            network_interfaces=[ec2.CfnInstance.NetworkInterfaceProperty(
                device_index="0", subnet_id=subnet_id, group_set=[web_sg.security_group_id],
                associate_public_ip_address=True, delete_on_termination=True)],
            block_device_mappings=[ec2.CfnInstance.BlockDeviceMappingProperty(device_name="/dev/xvda",
                ebs=ec2.CfnInstance.EbsProperty(volume_size=8, volume_type="gp3", encrypted=True, delete_on_termination=True))],
            metadata_options=ec2.CfnInstance.MetadataOptionsProperty(http_tokens="required", http_endpoint="enabled"),
            user_data=Fn.base64(Fn.sub(USER_DATA, {"EfsId": self.file_system.file_system_id})))
        # l'istanza parte quando file system e mount target esistono (lo script li usa subito)
        self.instance.node.add_dependency(self.file_system)

        CfnOutput(self, "WebsiteUrl", value=f"http://{self.instance.attr_public_ip}/")
        CfnOutput(self, "FileSystemId", value=self.file_system.file_system_id)
        CfnOutput(self, "InstanceId", value=self.instance.ref)

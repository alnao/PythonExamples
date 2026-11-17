"""WordPress su una sola istanza EC2 con il database su RDS MySQL.

- istanza EC2 Amazon Linux 2023 con Apache, PHP-FPM e WordPress in /var/www/html (installati al primo avvio)
- database RDS MySQL 8.4 db.t4g.micro, utente e password generati in Secrets Manager e letti dall'istanza
- interfaccia di rete dello stack (con i tag) ed Elastic IP: l'indirizzo del sito non cambia dopo stop e start
- CloudFormation aspetta il segnale dello script di installazione (cfn-signal), con la riga che fallisce nel log
- niente SSH: si entra con Session Manager

E' la versione "a una istanza" del cdk21autoScalingWordpress (che aggiunge load balancer, Auto Scaling ed EFS).
"""

from aws_cdk import (
    CfnCreationPolicy,
    CfnOutput,
    CfnParameter,
    CfnResourceSignal,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
)
from constructs import Construct

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

INSTANCE_TYPES = ["t3.micro", "t3.small", "t3.medium"]

USER_DATA = r"""#!/bin/bash
set -Eeuxo pipefail
trap 'echo "ERRORE cdk19: comando fallito alla riga $LINENO: $BASH_COMMAND" | tee /dev/console >&2' ERR

# ripete un comando fino a 30 volte, 10 secondi tra un tentativo e l'altro (rete appena creata)
retry() {
  for i in $(seq 1 30); do
    "$@" && return 0
    echo "tentativo $i fallito: $*" >&2
    sleep 10
  done
  return 1
}

retry dnf install -y httpd php php-fpm php-mysqlnd php-json php-gd php-xml php-mbstring aws-cfn-bootstrap
# da qui in poi il segnale a CloudFormation parte sempre, con l'esito dello script
trap '/opt/aws/bin/cfn-signal -e $? --stack ${AWS::StackName} --resource Instance --region ${AWS::Region} || true' EXIT

curl -sSL --retry 5 --retry-delay 10 https://wordpress.org/latest.tar.gz | tar xz -C /tmp
rm -rf /var/www/html && mv /tmp/wordpress /var/www/html

set +x  # la password non deve finire nel log
SECRET_JSON=$(retry aws secretsmanager get-secret-value --secret-id ${DbSecretArn} --region ${AWS::Region} --query SecretString --output text)
export SECRET_JSON
export DB_HOST=${DbHost} DB_NAME=${DbName}
python3 - <<'PY'
import json, os, secrets
secret = json.loads(os.environ["SECRET_JSON"])
path = "/var/www/html/"
text = open(path + "wp-config-sample.php").read()
text = (text.replace("database_name_here", os.environ["DB_NAME"])
            .replace("username_here", secret["username"])
            .replace("password_here", secret["password"])
            .replace("'localhost'", "'" + os.environ["DB_HOST"] + "'"))
# chiavi di sicurezza di WordPress, una diversa per ogni riga 'put your unique phrase here'
while "put your unique phrase here" in text:
    text = text.replace("put your unique phrase here", secrets.token_urlsafe(48), 1)
open(path + "wp-config.php", "w").write(text)
PY
unset SECRET_JSON
set -x

chown -R apache:apache /var/www/html
systemctl enable --now php-fpm httpd
"""


class Cdk19WordpressSingleStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC e subnet: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 2)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_1 = subnet_parameter(self, "subnetid1", default_subnets[0], "subnet pubblica dell'istanza (e del database)")
        subnet_2 = subnet_parameter(self, "subnetid2", default_subnets[1], "seconda subnet del database, in un'altra zona")
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo dell'istanza").value_as_string
        db_name = CfnParameter(self, "dbname", type="String", default="wordpress", allowed_pattern="[a-zA-Z][a-zA-Z0-9]*",
                               description="nome del database di WordPress").value_as_string

        azs = [Fn.select(0, Fn.get_azs()), Fn.select(1, Fn.get_azs())]
        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=azs,
                                          private_subnet_ids=[subnet_1, subnet_2])

        web_sg = ec2.SecurityGroup(self, "WebSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                   description="WordPress: HTTP da Internet, niente SSH")
        web_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP da Internet")

        self.database = rds.DatabaseInstance(self, "Database",
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_4_8),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            database_name=db_name,
            credentials=rds.Credentials.from_generated_secret("wpadmin", exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"),
            allocated_storage=20, storage_type=rds.StorageType.GP3, storage_encrypted=True,
            multi_az=False, publicly_accessible=False,
            backup_retention=Duration.days(1), delete_automated_backups=True,
            removal_policy=RemovalPolicy.DESTROY, deletion_protection=False)
        self.database.connections.allow_default_port_from(web_sg, "MySQL da WordPress")

        # Interfaccia di rete dello stack con l'Elastic IP (come nel cdk17)
        network_interface = ec2.CfnNetworkInterface(self, "NetworkInterface", subnet_id=subnet_1,
            group_set=[web_sg.security_group_id], description="interfaccia di WordPress cdk19")
        eip = ec2.CfnEIP(self, "ElasticIp", domain="vpc")
        association = ec2.CfnEIPAssociation(self, "ElasticIpAssociation", allocation_id=eip.attr_allocation_id,
                                            network_interface_id=network_interface.ref)

        role = iam.Role(self, "InstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")])
        self.database.secret.grant_read(role)
        profile = iam.CfnInstanceProfile(self, "InstanceProfile", roles=[role.role_name])

        instance = ec2.CfnInstance(self, "Instance",
            image_id=ec2.MachineImage.latest_amazon_linux2023().get_image(self).image_id,
            instance_type=instance_type, iam_instance_profile=profile.ref,
            network_interfaces=[ec2.CfnInstance.NetworkInterfaceProperty(device_index="0",
                                                                         network_interface_id=network_interface.ref)],
            block_device_mappings=[ec2.CfnInstance.BlockDeviceMappingProperty(device_name="/dev/xvda",
                ebs=ec2.CfnInstance.EbsProperty(volume_size=8, volume_type="gp3", encrypted=True, delete_on_termination=True))],
            propagate_tags_to_volume_on_creation=True,
            metadata_options=ec2.CfnInstance.MetadataOptionsProperty(http_tokens="required", http_endpoint="enabled"),
            user_data=Fn.base64(Fn.sub(USER_DATA, {
                "DbSecretArn": self.database.secret.secret_arn,
                "DbHost": self.database.db_instance_endpoint_address,
                "DbName": db_name,
            })))
        # CloudFormation aspetta il cfn-signal dello script (al massimo 15 minuti)
        instance.cfn_options.creation_policy = CfnCreationPolicy(
            resource_signal=CfnResourceSignal(count=1, timeout="PT15M"))
        # l'Elastic IP deve essere gia' associato quando parte lo script (scarica pacchetti e WordPress)
        instance.node.add_dependency(association)
        # il secret deve avere host e porta (agganciati al database) e il ruolo il permesso di leggerlo
        instance.node.add_dependency(self.database, role)

        CfnOutput(self, "WebsiteUrl", value=f"http://{eip.attr_public_ip}/",
                  description="sito WordPress (la prima volta apre l'installazione)")
        CfnOutput(self, "ElasticIpAddress", value=eip.attr_public_ip)
        CfnOutput(self, "InstanceId", value=instance.ref)
        CfnOutput(self, "DatabaseEndpoint", value=self.database.db_instance_endpoint_address)
        CfnOutput(self, "DatabaseSecretArn", value=self.database.secret.secret_arn)

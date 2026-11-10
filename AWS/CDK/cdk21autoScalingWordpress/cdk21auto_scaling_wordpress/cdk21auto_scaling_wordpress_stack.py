"""WordPress su un Auto Scaling group dietro un Application Load Balancer.

Le istanze sono in subnet private e condividono:
- il codice di WordPress (e i file caricati) su un file system EFS montato in /mnt/efs
- il database su RDS MySQL, con la password generata in Secrets Manager

Il primo server che parte installa WordPress su EFS, gli altri lo trovano gia' pronto.
Lo stack e' la base anche del cdk22cloudWatchAlarm, che lo estende con gli allarmi.
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_rds as rds,
)
from constructs import Construct

INSTANCE_TYPES = ["t3.nano", "t3.micro", "t3.small", "t3.medium", "t3.large"]

# script eseguito come root al primo avvio di ogni istanza (log in /var/log/cloud-init-output.log)
USER_DATA = r"""
set -Eeuxo pipefail
# in caso di errore la riga e il comando falliti finiscono nel log (e nella console dell'istanza)
trap 'echo "ERRORE cdk21: comando fallito alla riga $LINENO: $BASH_COMMAND" | tee /dev/console >&2' ERR

# ripete un comando fino a 30 volte, 10 secondi tra un tentativo e l'altro (rete e DNS appena create)
retry() {
  for i in $(seq 1 30); do
    "$@" && return 0
    echo "tentativo $i fallito: $*"
    sleep 10
  done
  return 1
}

retry dnf install -y httpd php php-fpm php-mysqlnd php-json php-gd php-xml php-mbstring amazon-efs-utils aws-cfn-bootstrap

# disco condiviso EFS: il nome DNS del mount target puo' richiedere fino a 90 secondi dopo la creazione
mkdir -p /mnt/efs
retry mount -t efs -o tls ${EfsId}:/ /mnt/efs
echo "${EfsId}:/ /mnt/efs efs _netdev,tls 0 0" >> /etc/fstab

TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)

# WordPress si installa una sola volta: due istanze possono partire insieme, il lock sul disco condiviso le mette in fila
(
  flock 9
  if [ ! -f /mnt/efs/wordpress/wp-config.php ]; then
    echo "$(date) WordPress non presente: lo installo da $INSTANCE_ID" >> /mnt/efs/install.log
    curl -sSL --retry 5 --retry-delay 10 https://wordpress.org/latest.tar.gz | tar xz -C /mnt/efs
    set +x  # la password non deve finire nel log
    export SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id ${DbSecretArn} --region ${Region} --query SecretString --output text)
    export DB_HOST=${DbHost} DB_NAME=${DbName}
    python3 - <<'PY'
import json, os, secrets
secret = json.loads(os.environ["SECRET_JSON"])
path = "/mnt/efs/wordpress/"
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
    echo "OK Health status" > /mnt/efs/wordpress/hostname.html
  else
    echo "$(date) WordPress gia' installato, $INSTANCE_ID lo usa" >> /mnt/efs/install.log
  fi
) 9>/mnt/efs/install.lock

# elenco dei server avviati, nella pagina usata dal controllo di salute del load balancer
echo "Site from $INSTANCE_ID $AZ" >> /mnt/efs/wordpress/hostname.html
chown -R apache:apache /mnt/efs/wordpress

# Apache serve direttamente la cartella su EFS
sed -i 's#/var/www/html#/mnt/efs/wordpress#g' /etc/httpd/conf/httpd.conf
systemctl enable --now php-fpm httpd
"""


class Cdk21AutoScalingWordpressStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC esistente: le subnet pubbliche ospitano il load balancer, le private (con NAT) i server e il database
        vpc_id = CfnParameter(self, "vpcid", type="AWS::EC2::VPC::Id", description="VPC esistente").value_as_string
        public_1 = CfnParameter(self, "publicsubnetids1", type="AWS::EC2::Subnet::Id", description="subnet pubblica 1").value_as_string
        public_2 = CfnParameter(self, "publicsubnetids2", type="AWS::EC2::Subnet::Id", description="subnet pubblica 2").value_as_string
        private_1 = CfnParameter(self, "privatesubnetid1", type="AWS::EC2::Subnet::Id", description="subnet privata 1 (con NAT)").value_as_string
        private_2 = CfnParameter(self, "privatesubnetid2", type="AWS::EC2::Subnet::Id", description="subnet privata 2 (con NAT)").value_as_string
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo delle istanze EC2").value_as_string
        db_name = CfnParameter(self, "dbname", type="String", default="wordpress", allowed_pattern="[a-zA-Z][a-zA-Z0-9]*",
                               description="nome del database di WordPress").value_as_string

        azs = [Fn.select(0, Fn.get_azs()), Fn.select(1, Fn.get_azs())]
        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=azs,
                                          public_subnet_ids=[public_1, public_2],
                                          private_subnet_ids=[private_1, private_2])
        private = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)

        # Security group dei server web: HTTP solo dal load balancer (regola aggiunta da add_targets),
        # niente SSH (accesso con Session Manager)
        web_sg = ec2.SecurityGroup(self, "WebServerSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                   description="Server WordPress: HTTP dal load balancer")

        # Database MySQL, password generata in Secrets Manager (senza caratteri che disturbano wp-config.php)
        self.database = rds.DatabaseInstance(self, "Database",
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_4_8),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=vpc, vpc_subnets=private,
            database_name=db_name,
            credentials=rds.Credentials.from_generated_secret("wpadmin", exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"),
            allocated_storage=20, storage_type=rds.StorageType.GP3,
            multi_az=False, publicly_accessible=False, storage_encrypted=True,
            backup_retention=Duration.days(1), delete_automated_backups=True,
            # esempio: al destroy il database si cancella senza snapshot finale (vedi README)
            removal_policy=RemovalPolicy.DESTROY, deletion_protection=False,
        )
        self.database.connections.allow_default_port_from(web_sg, "MySQL dai server WordPress")

        # File system condiviso con il codice di WordPress
        self.file_system = efs.FileSystem(self, "FileSystem", vpc=vpc, vpc_subnets=private, encrypted=True,
                                          removal_policy=RemovalPolicy.DESTROY)
        self.file_system.connections.allow_default_port_from(web_sg, "NFS dai server WordPress")

        # Ruolo delle istanze: Session Manager, lettura del segreto del database, mount di EFS
        role = iam.Role(self, "WebServerRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")])
        self.database.secret.grant_read(role)
        self.file_system.grant_read_write(role)

        user_data = ec2.UserData.for_linux()
        user_data.add_commands(Fn.sub(USER_DATA, {
            "EfsId": self.file_system.file_system_id,
            "DbSecretArn": self.database.secret.secret_arn,
            "DbHost": self.database.db_instance_endpoint_address,
            "DbName": db_name,
            "Region": self.region,
        }))

        launch_template = ec2.LaunchTemplate(self, "WebServerTemplate",
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            user_data=user_data, role=role, security_group=web_sg,
            require_imdsv2=True,
            block_devices=[ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(
                8, volume_type=ec2.EbsDeviceVolumeType.GP3, encrypted=True, delete_on_termination=True))],
        )

        # Auto Scaling group: CloudFormation aspetta il segnale di ogni istanza (cfn-signal alla fine dello script)
        self.asg = autoscaling.AutoScalingGroup(self, "WebServerGroup",
            vpc=vpc, vpc_subnets=private, launch_template=launch_template,
            min_capacity=1, max_capacity=3,
            health_checks=autoscaling.HealthChecks.with_additional_checks(
                additional_types=[autoscaling.AdditionalHealthCheckType.ELB], grace_period=Duration.minutes(5)),
            signals=autoscaling.Signals.wait_for_min_capacity(timeout=Duration.minutes(15)),
            update_policy=autoscaling.UpdatePolicy.rolling_update(
                min_instances_in_service=1, max_batch_size=1, pause_time=Duration.minutes(15)),
        )
        user_data.add_signal_on_exit_command(self.asg)
        # l'istanza parte solo dopo database e file system (lo script li usa subito)
        self.asg.node.add_dependency(self.database, self.file_system)

        # Application Load Balancer pubblico
        self.alb = elbv2.ApplicationLoadBalancer(self, "LoadBalancer", vpc=vpc, internet_facing=True,
                                                 vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC))
        self.listener = self.alb.add_listener("HttpListener", port=80, open=True)
        self.target_group = self.listener.add_targets("WebServers",
            port=80, protocol=elbv2.ApplicationProtocol.HTTP, targets=[self.asg],
            health_check=elbv2.HealthCheck(path="/hostname.html", interval=Duration.seconds(10),
                                           timeout=Duration.seconds(5), healthy_threshold_count=2,
                                           unhealthy_threshold_count=5),
            # WordPress tiene la sessione sul server: stesso utente, stessa istanza per 30 secondi
            stickiness_cookie_duration=Duration.seconds(30),
            deregistration_delay=Duration.seconds(30),
        )

        CfnOutput(self, "WebsiteURL", value=f"http://{self.alb.load_balancer_dns_name}/",
                  description="sito WordPress (la prima volta apre l'installazione)")
        CfnOutput(self, "HealthURL", value=f"http://{self.alb.load_balancer_dns_name}/hostname.html",
                  description="pagina del controllo di salute con l'elenco dei server avviati")
        CfnOutput(self, "AutoScalingGroupName", value=self.asg.auto_scaling_group_name)
        CfnOutput(self, "DatabaseEndpoint", value=self.database.db_instance_endpoint_address)
        CfnOutput(self, "DatabaseSecretArn", value=self.database.secret.secret_arn)
        CfnOutput(self, "FileSystemId", value=self.file_system.file_system_id)

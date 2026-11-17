"""Auto Scaling group di istanze Apache dietro un Application Load Balancer.

- Application Load Balancer pubblico su due subnet (zone diverse) della VPC indicata
- Auto Scaling group da 1 a 4 istanze (2 all'avvio) Amazon Linux 2023 con Apache e una pagina che mostra
  istanza e zona: aggiornando la pagina si vede il load balancer alternare i server
- istanze nelle stesse subnet pubbliche con IP pubblico (per scaricare i pacchetti senza NAT gateway),
  ma la porta 80 e' aperta solo al security group del load balancer; niente SSH, Session Manager
- scaling sulla CPU media (target 70%), controllo di salute del load balancer per sostituire le istanze malate
- launch template con IMDSv2 e disco gp3 cifrato; i tag arrivano anche a istanze, dischi e interfacce di rete

La prima versione richiedeva subnet private con NAT (senza NAT le istanze non installavano Apache e venivano
sostituite in continuazione), una key pair con SSH aperto a tutti, Amazon Linux 2 e le zone eu-west-1a/b fisse.
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    Fn,
    Stack,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
)
from constructs import Construct

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

INSTANCE_TYPES = ["t3.nano", "t3.micro", "t3.small", "t3.medium"]

USER_DATA = r"""set -Eeuxo pipefail
for i in $(seq 1 30); do dnf install -y httpd && break; sleep 10; done
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
cat > /var/www/html/index.html <<HTML
<html><body><h1>Auto Scaling Group cdk20</h1>
<p>Risponde l'istanza $INSTANCE_ID in $AZ, avviata il $(date)</p></body></html>
HTML
systemctl enable --now httpd
"""


class Cdk20AutoScalingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC e subnet: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 2)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_1 = subnet_parameter(self, "subnetid1", default_subnets[0], "subnet pubblica 1")
        subnet_2 = subnet_parameter(self, "subnetid2", default_subnets[1], "subnet pubblica 2, in un'altra zona")
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo delle istanze").value_as_string

        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id,
                                          availability_zones=[Fn.select(0, Fn.get_azs()), Fn.select(1, Fn.get_azs())],
                                          public_subnet_ids=[subnet_1, subnet_2])
        public = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)

        alb_sg = ec2.SecurityGroup(self, "AlbSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                   description="cdk20: load balancer, HTTP da Internet")
        alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP da Internet")
        web_sg = ec2.SecurityGroup(self, "WebSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                   description="cdk20: istanze, HTTP solo dal load balancer")
        web_sg.add_ingress_rule(alb_sg, ec2.Port.tcp(80), "HTTP dal load balancer")

        role = iam.Role(self, "WebServerRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")])
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(USER_DATA)

        launch_template = ec2.LaunchTemplate(self, "WebServerTemplate",
            instance_type=ec2.InstanceType(instance_type),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            user_data=user_data, role=role, security_group=web_sg,
            associate_public_ip_address=True,  # pacchetti da Internet senza NAT gateway
            require_imdsv2=True,
            block_devices=[ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(
                8, volume_type=ec2.EbsDeviceVolumeType.GP3, encrypted=True, delete_on_termination=True))])

        self.asg = autoscaling.AutoScalingGroup(self, "WebServerAsg", vpc=vpc, vpc_subnets=public,
            launch_template=launch_template, min_capacity=1, max_capacity=4, desired_capacity=2,
            health_checks=autoscaling.HealthChecks.with_additional_checks(
                additional_types=[autoscaling.AdditionalHealthCheckType.ELB], grace_period=Duration.minutes(3)))
        self.asg.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=70,
                                          estimated_instance_warmup=Duration.minutes(3))

        self.alb = elbv2.ApplicationLoadBalancer(self, "WebAlb", vpc=vpc, vpc_subnets=public, internet_facing=True,
                                                 security_group=alb_sg)
        listener = self.alb.add_listener("HttpListener", port=80, open=False)  # regola gia' nel security group
        listener.add_targets("WebServers", port=80, protocol=elbv2.ApplicationProtocol.HTTP, targets=[self.asg],
            health_check=elbv2.HealthCheck(path="/", healthy_threshold_count=2, unhealthy_threshold_count=3,
                                           interval=Duration.seconds(15), timeout=Duration.seconds(5)),
            deregistration_delay=Duration.seconds(30))

        CfnOutput(self, "WebsiteUrl", value=f"http://{self.alb.load_balancer_dns_name}/")
        CfnOutput(self, "AutoScalingGroupName", value=self.asg.auto_scaling_group_name)

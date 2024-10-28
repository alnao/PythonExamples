from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
    aws_iam as iam,
    Duration,
    CfnOutput,CfnParameter
)
from constructs import Construct

class Cdk20AutoScalingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_id = CfnParameter(self, "vpcid", 
            type="String",
            description="vpc_id").value_as_string # ,default="xxx")
        key_name = CfnParameter(self, "keyname", 
            type="String",
            description="key_name").value_as_string # ,default="xxx")
        public_subnet_id1 = CfnParameter(self, "publicsubnetids1", 
            type="String",
            description="public_subnet_id1").value_as_string # ,default="xxx")
        public_subnet_id2 = CfnParameter(self, "publicsubnetids2", 
            type="String",
            description="public_subnet_id2").value_as_string # ,default="xxx")
        private_subnet_id1 = CfnParameter(self, "privatesubnetid1", 
            type="String",
            description="private_subnet_id1").value_as_string # ,default="xxx")
        private_subnet_id2 = CfnParameter(self, "privatesubnetid2", 
            type="String",
            description="private_subnet_id2").value_as_string # ,default="xxx")

         # Importa la VPC esistente
        vpc = ec2.Vpc.from_vpc_attributes(self, "VPC",
            availability_zones=["eu-west-1a", "eu-west-1b"], #availability_zones=["eu-west-1b"],
            # This imports the default VPC but you can also
            # specify a 'vpcName' or 'tags'.
            vpc_id=vpc_id,
            # is_default=False, # TypeError: from_vpc_attributes() got an unexpected keyword argument 'is_default'
            public_subnet_ids =[public_subnet_id1,public_subnet_id2],
            private_subnet_ids=[private_subnet_id1,private_subnet_id2]
        )

        # Security Group per ALB
        alb_security_group = ec2.SecurityGroup(self, "AlbSecurityGroup",
            vpc=vpc,
            description="Security Group per ALB",
            allow_all_outbound=True
        )

        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Permetti HTTP"
        )

        # Security Group per le istanze EC2
        asg_security_group = ec2.SecurityGroup(self, "AsgSecurityGroup",
            vpc=vpc,
            description="Security Group per ASG",
            allow_all_outbound=True
        )

        # Permetti traffico dall'ALB alle istanze EC2
        asg_security_group.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(80),
            description="Permetti HTTP dall ALB"
        )

        asg_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Permetti SSH"
        )

        # Permetti traffico NFS per EFS
#        asg_security_group.add_ingress_rule(
#            peer=asg_security_group,
#            connection=ec2.Port.tcp(2049),
#            description="Permetti NFS per EFS"
#        )

        # Crea Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(self, "WebAlb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group
        )

        # Crea Target Group
        target_group = elbv2.ApplicationTargetGroup(self, "WebTargetGroup",
            vpc=vpc,
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.INSTANCE,
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_threshold_count=2,
                unhealthy_threshold_count=2,
                timeout=Duration.seconds(10),
                interval=Duration.seconds(15)
            )
        )

        # Aggiungi listener all'ALB
        alb.add_listener("HttpListener",
            port=80,
            default_target_groups=[target_group]
        )

        # Crea ruolo IAM per le istanze EC2
        role = iam.Role(self, "WebServerRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        
        # Aggiungi i permessi necessari per EFS
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonElasticFileSystemClientReadWriteAccess")
        )

        # User data per le istanze EC2
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "yum update -y",
            "yum install -y httpd amazon-efs-utils",
#            "mkdir -p /var/www/html",
#            "rm -rf /var/www/html/*",
#            f"mount -t efs -o tls {efs_id}:/ /var/www/html",
#            f"echo '{efs_id}:/ /var/www/html efs _netdev,tls,iam 0 0' >> /etc/fstab",
#            "chown -R apache:apache /var/www/html",
            "REGION=$(curl http://169.254.169.254/latest/meta-data/placement/region)",
            "AZ=$(curl http://169.254.169.254/latest/meta-data/placement/availability-zone)",
            "echo '<html><body><h1>Auto Scaling Group Test</h1><p>' > /var/www/html/index.html",
            "echo ""Site from $(hostname -f) $REGION $AZ"" >> /var/www/html/index.html",
            "echo '</p></body></html>' >> /var/www/html/index.html",
            "systemctl enable httpd",
            "systemctl start httpd"
        )

        # Crea Launch Template
        launch_template = ec2.LaunchTemplate(self, "WebServerTemplate",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            user_data=user_data,
            role=role,
            security_group=asg_security_group,

            associate_public_ip_address=False,
            key_name=key_name
        )

        # Crea Auto Scaling Group
        asg = autoscaling.AutoScalingGroup(self, "WebServerAsg",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            launch_template=launch_template,
            min_capacity=1,
            max_capacity=4,
            desired_capacity=2,
#            target_group_arns=[target_group.target_group_arn],
            health_check=autoscaling.HealthCheck.elb(
                grace=Duration.seconds(60)
            )
        )
        # Collega l'ASG al target group
        target_group.add_target(asg)

        # Aggiungi policy di scaling
        asg.scale_on_cpu_utilization("CpuScaling",
            target_utilization_percent=70,
            cooldown=Duration.seconds(300)
        )

        # Output
        CfnOutput(self, "LoadBalancerDNS",
            value=alb.load_balancer_dns_name,
            description="DNS name del Load Balancer"
        )
        CfnOutput(self, "AutoScalingGroupName",
            value=asg.auto_scaling_group_name,
            description="Nome dell'Auto Scaling Group"
        )
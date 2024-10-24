import aws_cdk as cdk
from aws_cdk import (
    # Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_efs as efs,
    aws_iam as iam,
    CfnOutput,RemovalPolicy,CfnParameter
)
from constructs import Construct

class Cdk18EfsStack(Stack):

#        vpc_id = CfnParameter(self, "vpcid", 
#            type="String",
#            description="vpc_id").value_as_string # ,default="xxx")
#        key_name = CfnParameter(self, "keyname", 
#            type="String",
#            description="key_name").value_as_string # ,default="xxx")
#        public_subnet_ids1 = CfnParameter(self, "publicsubnetids1", 
#            type="String",
#            description="public_subnet_ids1").value_as_string # ,default="xxx")
#        public_subnet_ids2 = CfnParameter(self, "publicsubnetids2", 
#            type="String",
#            description="public_subnet_ids2").value_as_string # ,default="xxx")
#        # The code that defines your stack goes here
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None: #, vpc_id: str
        super().__init__(scope, construct_id, **kwargs)

        vpc_id = CfnParameter(self, "vpcid", 
            type="String",
            description="vpc_id").value_as_string # ,default="xxx")
        key_name = CfnParameter(self, "keyname", 
            type="String",
            description="key_name").value_as_string # ,default="xxx")
        public_subnet_id = CfnParameter(self, "publicsubnetids", 
            type="String",
            description="public_subnet_ids").value_as_string # ,default="xxx")


        # Importa la VPC esistente
        vpc = ec2.Vpc.from_vpc_attributes(self, "VPC",
            availability_zones=["eu-west-1b"],
            # This imports the default VPC but you can also
            # specify a 'vpcName' or 'tags'.
            vpc_id=vpc_id,
            # is_default=False, # TypeError: from_vpc_attributes() got an unexpected keyword argument 'is_default'
            public_subnet_ids =[public_subnet_id]
        )

        # Crea un Security Group per EFS
        efs_security_group = ec2.SecurityGroup(self, "EfsSecurityGroup",
            vpc=vpc,
            description="Security Group per EFS",
            allow_all_outbound=True
        )

        # Crea un Security Group per EC2
        ec2_security_group = ec2.SecurityGroup(self, "Ec2SecurityGroup",
            vpc=vpc,
            description="Security Group per EC2",
            allow_all_outbound=True
        )

        # Permetti traffico NFS dal security group EC2 a EFS
        efs_security_group.add_ingress_rule(
            peer=ec2_security_group,
            connection=ec2.Port.tcp(2049),
            description="Permetti NFS da EC2"
        )

        # Permetti traffico HTTP/HTTPS verso EC2
        ec2_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Permetti HTTP"
        )
        ec2_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Permetti HTTPS"
        )
        ec2_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(22),
            description="Permetti HTTPS"
        )

        # Crea il File System EFS
        file_system = efs.FileSystem(self, "EfsFileSystem",
            vpc=vpc,
            security_group=efs_security_group,
            removal_policy=RemovalPolicy.DESTROY  # Solo per dev/test
        )
        # Add policy to allow EC2 to mount EFS
        file_system.connections.allow_default_port_from(ec2_security_group)

        # Attach IAM policy to allow mounting EFS
        file_system_policy = iam.PolicyStatement(
            actions=["elasticfilesystem:ClientMount"],
            resources=["*"], #[file_system.file_system_arn]
            effect=iam.Effect.ALLOW,
            principals=[iam.AnyPrincipal()] #no *
        )
        file_system.add_to_resource_policy(file_system_policy)

        for subnet in vpc.private_subnets:
            efs.CfnMountTarget(self, f"EfsMountTarget{subnet.node.id}",
                file_system_id=file_system.file_system_id,
                subnet_id=subnet.subnet_id,
                security_groups=[efs_security_group.security_group_id]
            )

        # Crea un ruolo IAM per l'istanza EC2
        role = iam.Role(self, "Ec2Role",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        # Aggiungi i permessi necessari per EFS
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonElasticFileSystemClientReadWriteAccess")
        )
        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonElasticFileSystemClientFullAccess")
        )


        # Script di user data per configurare l'istanza
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "sudo yum update -y",
            "sudo yum install -y httpd amazon-efs-utils",
            "sudo chmod 777 /var/www/html",
            f"mkdir -p /var/www/html",
            "rm -rf /var/www/html/*",
            "REGION=$(curl http://169.254.169.254/latest/meta-data/placement/region)",
            "sleep 30",
            "sleep 30",
            f"sudo mount -t efs -o tls {file_system.file_system_id}:/ /var/www/html",
#            "echo '${file_system.file_system_id}:/ /var/www/html efs defaults,_netdev 0 0' >> /etc/fstab",
            "sudo echo ""Site from $(hostname -f) $REGION"" > /var/www/html/index.html ",
            "sudo echo ""Site from $REGION"" >> /home/ec2-user/aaaa.html ",
            "sudo chown -R apache:apache /var/www/html",
            "sudo systemctl enable httpd",
            "sudo systemctl start httpd"
        )

        # Crea l'istanza EC2
        instance = ec2.Instance(self, "WebServer",
            vpc=vpc,
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, 
                ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            security_group=ec2_security_group,
            role=role,
            user_data=user_data,
            associate_public_ip_address=True,
            key_name=key_name
        )


        # Output
        CfnOutput(self, "InstancePublicIP",
            value=instance.instance_public_ip,
            description="Indirizzo IP pubblico dell'istanza EC2"
        )
        CfnOutput(self, "FileSystemId",
            value=file_system.file_system_id,
            description="ID del File System EFS"
        )
        
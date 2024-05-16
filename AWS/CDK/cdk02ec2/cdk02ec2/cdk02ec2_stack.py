from aws_cdk import (
    Stack,CfnParameter,
    aws_ec2 as ec2,
    CfnOutput,
    CfnTag,
)
from constructs import Construct

class Cdk02Ec2Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc_id = CfnParameter(self, "vpc_id", type="String", default="vpc_id").value_as_string
        self.key_pair_name = CfnParameter(self, "key_pair_name", type="String", default="").value_as_string
        self.public_subnet_id = CfnParameter(self, "public_subnet_id", type="String", default="public_subnet_id").value_as_string

        # The code that defines your stack goes here
        # Create Basic VPC
        #        vpc = ec2.Vpc(
        #            self,
        #            "MyVpc",
        #            max_azs=2,
        #            subnet_configuration=[
        #                ec2.SubnetConfiguration(
        #                    name="public-subnet-1",
        #                    subnet_type=ec2.SubnetType.PUBLIC,
        #                    cidr_mask=24,
        #                )
        #            ],
        #        )
#see https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/Vpc.html
#see from_vpc_attributes method
        vpc = ec2.Vpc.from_vpc_attributes(self, "VPC",
            availability_zones=["eu-west-1b"],
            # This imports the default VPC but you can also
            # specify a 'vpcName' or 'tags'.
            vpc_id=self.vpc_id,
            # is_default=False, # TypeError: from_vpc_attributes() got an unexpected keyword argument 'is_default'
            public_subnet_ids =[self.public_subnet_id]
        )

        # Create Security Group
        sec_group = ec2.SecurityGroup(
            self, "CdkSecurityGroup", vpc=vpc, allow_all_outbound=True
        )
        # Create Security Group Ingress Rule
        sec_group.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(22), "allow SSH access"
        )

        # Create Key Pair
        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/CfnKeyPair.html
        #cfn_key_pair = ec2.CfnKeyPair(
        #    self,
        #    "MyCfnKeyPair",
        #    key_name="cdk-ec2-key-pair",
        #    tags=[CfnTag(key="key", value="value")],
        #)
        #see https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/KeyPair.html
        #cfn_key_pair = ec2.KeyPair.from_key_pair_attributes(self, "KeyPair",
        #    key_pair_name=self.key_pair_name,
        #    type=ec2.KeyPairType.RSA
        #)

        # Create EC2 instance
        # https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_ec2/README.html
        # https://docs.aws.amazon.com/linux/al2023/ug/what-is-amazon-linux.html
        instance = ec2.Instance(
            self,
            "MyInstance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            vpc=vpc,
            security_group=sec_group,
            associate_public_ip_address=True,
            key_name=self.key_pair_name # cfn_key_pair.key_name,
        )

        # Output Instance ID
        CfnOutput(self, "InstanceId", value=instance.instance_id)
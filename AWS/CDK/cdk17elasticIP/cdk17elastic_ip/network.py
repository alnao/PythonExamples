"""VPC e subnet di default dell'account come valori di default dei parametri dello stack.

Al synth (cdk synth / cdk deploy) CDK legge la VPC di default della region con chiamate di sola lettura
(ec2:DescribeVpcs, DescribeSubnets, DescribeRouteTables) e salva il risultato in cdk.context.json (ignorato da git:
contiene id dell'account). I parametri restano modificabili al deploy (--parameters vpcid=... subnetid1=...);
con -c vpc_id=vpc-xxx i valori di default vengono presi da un'altra VPC (per esempio se l'account non ha la VPC
di default: si ricrea con "aws ec2 create-default-vpc").
Lo stack deve avere account e region (env in app.py); nei test CDK usa una VPC finta, senza chiamate AWS.
"""

from aws_cdk import CfnParameter, aws_ec2 as ec2
from constructs import Construct


def lookup_vpc(scope: Construct) -> ec2.IVpc:
    """VPC di default della region, oppure quella indicata con -c vpc_id=..."""
    vpc_id = scope.node.try_get_context("vpc_id")
    if vpc_id:
        return ec2.Vpc.from_lookup(scope, "LookupVpc", vpc_id=vpc_id)
    return ec2.Vpc.from_lookup(scope, "LookupVpc", is_default=True)


def lookup_subnets(vpc: ec2.IVpc, count: int) -> list:
    """Le prime `count` subnet in zone diverse (prima le pubbliche: nella VPC di default lo sono tutte)."""
    chosen, zones = [], set()
    for subnet in [*vpc.public_subnets, *vpc.private_subnets, *vpc.isolated_subnets]:
        if subnet.availability_zone not in zones:
            chosen.append(subnet)
            zones.add(subnet.availability_zone)
    if len(chosen) < count:
        raise ValueError(f"la VPC {vpc.vpc_id} ha subnet in {len(chosen)} zone, ne servono {count}")
    return chosen[:count]


def vpc_parameter(scope: Construct, vpc: ec2.IVpc, name: str = "vpcid") -> str:
    return CfnParameter(scope, name, type="AWS::EC2::VPC::Id", default=vpc.vpc_id,
                        description="VPC (default: la VPC di default della region)").value_as_string


def subnet_parameter(scope: Construct, name: str, subnet: ec2.ISubnet, description: str) -> str:
    return CfnParameter(scope, name, type="AWS::EC2::Subnet::Id", default=subnet.subnet_id,
                        description=f"{description} (default: subnet della VPC di default in {subnet.availability_zone})"
                        ).value_as_string

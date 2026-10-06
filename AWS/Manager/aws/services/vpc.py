"""VPC: reti, subnet, route table, internet gateway e NAT gateway (sola lettura)."""

from aws.services import name_tag, paginate


class AwsVpc:
    def __init__(self, session):
        self.client = session.client('ec2')

    def vpcs(self):
        vpcs = paginate(self.client, 'describe_vpcs', 'Vpcs')
        for v in vpcs:
            v['Nome'] = name_tag(v.get('Tags'))
        return vpcs

    def network(self, vpc_id):
        """Componenti di rete della VPC."""
        f = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        subnets = paginate(self.client, 'describe_subnets', 'Subnets', Filters=f)
        for s in subnets:
            s['Nome'] = name_tag(s.get('Tags'))
        return {
            'subnets': sorted(subnets, key=lambda s: (s.get('AvailabilityZone', ''), s.get('CidrBlock', ''))),
            'route_tables': paginate(self.client, 'describe_route_tables', 'RouteTables', Filters=f),
            'internet_gateways': paginate(self.client, 'describe_internet_gateways', 'InternetGateways',
                                          Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]),
            'nat_gateways': paginate(self.client, 'describe_nat_gateways', 'NatGateways', Filter=f),
        }

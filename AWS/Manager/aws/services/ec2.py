"""EC2: istanze (avvio e arresto), Security Group (regole in ingresso) ed Elastic IP."""

from aws.services import name_tag, paginate


class AwsEc2:
    def __init__(self, session):
        self.client = session.client('ec2')

    def instances(self, ids=None):
        """Istanze con il campo Nome (tag Name) aggiunto."""
        kwargs = {'InstanceIds': ids} if ids else {}
        reservations = paginate(self.client, 'describe_instances', 'Reservations', **kwargs)
        out = []
        for r in reservations:
            for i in r['Instances']:
                i['Nome'] = name_tag(i.get('Tags'))
                out.append(i)
        return out

    def start(self, instance_id):
        self.client.start_instances(InstanceIds=[instance_id])
        return self.instances([instance_id])[0]

    def stop(self, instance_id):
        self.client.stop_instances(InstanceIds=[instance_id])
        return self.instances([instance_id])[0]


class AwsSecurityGroups:
    def __init__(self, session):
        self.client = session.client('ec2')

    def groups(self):
        return paginate(self.client, 'describe_security_groups', 'SecurityGroups')

    def get(self, group_id):
        return self.client.describe_security_groups(GroupIds=[group_id])['SecurityGroups'][0]

    def add_ingress(self, group_id, from_port, to_port, protocol, cidr, description=''):
        """Aggiunge una regola in ingresso (porte, protocollo tcp/udp/icmp/-1, CIDR)."""
        ip_range = {'CidrIp': cidr}
        if description:
            ip_range['Description'] = description
        self.client.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[{'FromPort': int(from_port), 'ToPort': int(to_port),
                            'IpProtocol': protocol, 'IpRanges': [ip_range]}])
        return self.get(group_id)


class AwsElasticIp:
    def __init__(self, session):
        self.client = session.client('ec2')

    def addresses(self):
        return self.client.describe_addresses().get('Addresses', [])

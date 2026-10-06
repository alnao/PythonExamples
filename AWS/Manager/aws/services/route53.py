"""Route 53: zone ospitate e record (servizio globale, sola lettura)."""

from aws.services import paginate


class AwsRoute53:
    def __init__(self, session):
        self.client = session.client('route53')

    def zones(self):
        return paginate(self.client, 'list_hosted_zones', 'HostedZones')

    def records(self, zone_id, limit=500):
        return paginate(self.client, 'list_resource_record_sets', 'ResourceRecordSets', limit=limit,
                        HostedZoneId=zone_id)

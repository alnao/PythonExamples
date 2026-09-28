"""RDS: istanze database."""

from aws.services import paginate


class AwsRds:
    def __init__(self, session):
        self.client = session.client('rds')

    def instances(self):
        return paginate(self.client, 'describe_db_instances', 'DBInstances')

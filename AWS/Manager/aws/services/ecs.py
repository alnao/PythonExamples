"""ECS: cluster, servizi e task (sola lettura)."""

from aws.services import paginate


def _chunks(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


class AwsEcs:
    def __init__(self, session):
        self.client = session.client('ecs')

    def clusters(self):
        arns = paginate(self.client, 'list_clusters', 'clusterArns')
        out = []
        for chunk in _chunks(arns, 100):
            out += self.client.describe_clusters(clusters=chunk, include=['TAGS', 'STATISTICS']).get('clusters', [])
        return out

    def services(self, cluster):
        arns = paginate(self.client, 'list_services', 'serviceArns', cluster=cluster)
        out = []
        for chunk in _chunks(arns, 10):
            out += self.client.describe_services(cluster=cluster, services=chunk).get('services', [])
        return out

    def tasks(self, cluster, limit=100):
        arns = paginate(self.client, 'list_tasks', 'taskArns', limit=limit, cluster=cluster)
        out = []
        for chunk in _chunks(arns, 100):
            out += self.client.describe_tasks(cluster=cluster, tasks=chunk).get('tasks', [])
        return out

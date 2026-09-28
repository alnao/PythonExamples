"""CloudFront: distribuzioni, dettaglio, invalidazioni."""

import time


class AwsCloudFront:
    def __init__(self, session):
        self.client = session.client('cloudfront')

    def distributions(self):
        items = []
        for page in self.client.get_paginator('list_distributions').paginate():
            items.extend(page.get('DistributionList', {}).get('Items', []))
        return items

    def distribution(self, distribution_id):
        return self.client.get_distribution(Id=distribution_id)['Distribution']

    def invalidations(self, distribution_id):
        response = self.client.list_invalidations(DistributionId=distribution_id)
        return response.get('InvalidationList', {}).get('Items', [])

    def invalidate_all(self, distribution_id):
        """Invalida tutta la cache della distribuzione (percorso /*)."""
        return self.client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={'Paths': {'Quantity': 1, 'Items': ['/*']},
                               'CallerReference': str(time.time()).replace('.', '')})['Invalidation']

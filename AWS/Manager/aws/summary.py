"""
Conteggio delle risorse attive per la Home: poche letture per region (describe e list,
gratuite) scelte tra le risorse che costano o che vanno tenute d'occhio.
"""

from common import GLOBAL_REGION, aws_session, run_parallel


def _paginate(client, operation, key, **kwargs):
    items = []
    for page in client.get_paginator(operation).paginate(**kwargs):
        items.extend(page.get(key, []))
    return items


def _ec2(s):
    reservations = _paginate(s.client('ec2'), 'describe_instances', 'Reservations')
    instances = [i for r in reservations for i in r['Instances'] if i['State']['Name'] != 'terminated']
    return {'value': sum(1 for i in instances if i['State']['Name'] == 'running'), 'total': len(instances)}


def _rds(s):
    dbs = _paginate(s.client('rds'), 'describe_db_instances', 'DBInstances')
    return {'value': sum(1 for d in dbs if d['DBInstanceStatus'] == 'available'), 'total': len(dbs)}


def _lambda(s):
    return {'value': len(_paginate(s.client('lambda'), 'list_functions', 'Functions'))}


def _dynamodb(s):
    return {'value': len(_paginate(s.client('dynamodb'), 'list_tables', 'TableNames'))}


def _load_balancers(s):
    return {'value': len(_paginate(s.client('elbv2'), 'describe_load_balancers', 'LoadBalancers'))}


def _nat(s):
    nats = _paginate(s.client('ec2'), 'describe_nat_gateways', 'NatGateways',
                     Filters=[{'Name': 'state', 'Values': ['available', 'pending']}])
    return {'value': len(nats)}


def _eip(s):
    addresses = s.client('ec2').describe_addresses().get('Addresses', [])
    # un Elastic IP non associato si paga senza usarlo
    return {'value': sum(1 for a in addresses if not a.get('AssociationId')), 'total': len(addresses)}


def _alarms(s):
    alarms = _paginate(s.client('cloudwatch'), 'describe_alarms', 'MetricAlarms')
    return {'value': sum(1 for a in alarms if a['StateValue'] == 'ALARM'), 'total': len(alarms)}


# (chiave, lettura) per region e globali
REGIONAL = [('ec2', _ec2), ('rds', _rds), ('lambda', _lambda), ('dynamodb', _dynamodb),
            ('load_balancers', _load_balancers), ('nat', _nat), ('eip', _eip), ('alarms', _alarms)]


def _s3(s):
    return {'value': len(s.client('s3').list_buckets().get('Buckets', []))}


def _cloudfront(s):
    dists = []
    for page in s.client('cloudfront').get_paginator('list_distributions').paginate():
        dists.extend(page.get('DistributionList', {}).get('Items', []))
    return {'value': sum(1 for d in dists if d['Enabled']), 'total': len(dists)}


GLOBAL = [('s3', _s3), ('cloudfront', _cloudfront)]


def resource_counts(profile, regions):
    """
    Contatori per region e globali, letti in parallelo. Un contatore che fallisce
    (permessi, servizio non attivo) riporta l'errore senza fermare gli altri.

    Ritorna {'regions': [{'region', 'counts': {chiave: {'value', 'total'?} | {'error'}}}],
             'global': {chiave: ...}, 'totals': {chiave: {'value', 'total'}}}
    """
    tasks = [(r, key, fn) for r in regions for key, fn in REGIONAL]
    tasks += [(GLOBAL_REGION, key, fn) for key, fn in GLOBAL]

    def run(task):
        region, _, fn = task
        return fn(aws_session(profile, region))

    per_region = {r: {} for r in regions}
    global_counts = {}
    for (region, key, _), res, err in run_parallel(tasks, run, max_workers=16):
        target = global_counts if key in dict(GLOBAL) else per_region[region]
        target[key] = {'error': err} if err else res

    totals = {}
    for counts in list(per_region.values()) + [global_counts]:
        for key, c in counts.items():
            if 'error' in c:
                continue
            t = totals.setdefault(key, {'value': 0})
            t['value'] += c['value']
            if 'total' in c:
                t['total'] = t.get('total', 0) + c['total']
    return {
        'regions': [{'region': r, 'counts': per_region[r]} for r in regions],
        'global': global_counts,
        'totals': totals,
    }

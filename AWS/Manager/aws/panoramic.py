"""
Panoramica delle risorse di un account AWS (ex AWS/Managers/PanoramicResources).

Ogni voce di SERVICES legge un servizio e restituisce righe gia' pronte per la tabella
({colonna: valore}). I servizi regionali vengono letti per ogni region richiesta, quelli
globali (S3, CloudFront, IAM, Route 53) una volta sola; tutte le letture vanno in parallelo.
"""

import logging
import time

from common import GLOBAL_REGION, aws_session, run_parallel

logger = logging.getLogger(__name__)


def _name(tags):
    """Valore del tag Name in una lista [{'Key', 'Value'}] di AWS."""
    return next((t['Value'] for t in tags or [] if t.get('Key') == 'Name'), '')


def _paginate(client, operation, key, **kwargs):
    items = []
    for page in client.get_paginator(operation).paginate(**kwargs):
        items.extend(page.get(key, []))
    return items


# ----------------------------------------------------------------------
# Letture: session -> righe
# ----------------------------------------------------------------------

def _default_vpc(ec2):
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])['Vpcs']
    return vpcs[0] if vpcs else None


def fetch_vpc(s):
    ec2 = s.client('ec2')
    vpc = _default_vpc(ec2)
    if not vpc:
        return []
    vpc_id = vpc['VpcId']
    igws = ec2.describe_internet_gateways(Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}])['InternetGateways']
    nats = ec2.describe_nat_gateways(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]},
                                              {'Name': 'state', 'Values': ['available']}])['NatGateways']
    nat_text = ', '.join(
        n['NatGatewayId'] + (f" ({n['NatGatewayAddresses'][0].get('PublicIp', '')})" if n.get('NatGatewayAddresses') else '')
        for n in nats)
    return [{'_tags': vpc.get('Tags'), 'VPC di default': vpc_id, 'CIDR': vpc['CidrBlock'],
             'Internet Gateway': igws[0]['InternetGatewayId'] if igws else '',
             'NAT Gateway': nat_text}]


def fetch_subnets(s):
    ec2 = s.client('ec2')
    vpc = _default_vpc(ec2)
    if not vpc:
        return []
    subnets = _paginate(ec2, 'describe_subnets', 'Subnets',
                        Filters=[{'Name': 'vpc-id', 'Values': [vpc['VpcId']]}])
    return [{'_tags': x.get('Tags'), 'ID Subnet': x['SubnetId'], 'Nome': _name(x.get('Tags')), 'CIDR': x['CidrBlock'],
             'Zona': x['AvailabilityZone'],
             'Tipo': 'pubblica' if x.get('MapPublicIpOnLaunch') else 'privata'} for x in subnets]


def fetch_security_groups(s):
    groups = _paginate(s.client('ec2'), 'describe_security_groups', 'SecurityGroups')
    return [{'_tags': g.get('Tags'), 'ID': g['GroupId'], 'Nome': g['GroupName'], 'Descrizione': g.get('Description', ''),
             'VPC': g.get('VpcId', '')} for g in groups]


def fetch_ec2(s):
    reservations = _paginate(s.client('ec2'), 'describe_instances', 'Reservations')
    return [{'_tags': i.get('Tags'), 'ID': i['InstanceId'], 'Nome': _name(i.get('Tags')), 'Tipo': i['InstanceType'],
             'Stato': i['State']['Name'], 'IP pubblico': i.get('PublicIpAddress', ''),
             'IP privato': i.get('PrivateIpAddress', '')}
            for r in reservations for i in r['Instances']]


def fetch_rds(s):
    dbs = _paginate(s.client('rds'), 'describe_db_instances', 'DBInstances')
    return [{'_tags': d.get('TagList'), 'Identificatore': d['DBInstanceIdentifier'],
             'Motore': f"{d['Engine']} {d.get('EngineVersion', '')}", 'Classe': d['DBInstanceClass'],
             'Stato': d['DBInstanceStatus'],
             'Endpoint': f"{d['Endpoint']['Address']}:{d['Endpoint']['Port']}" if d.get('Endpoint') else ''}
            for d in dbs]


def fetch_s3(s):
    buckets = s.client('s3').list_buckets().get('Buckets', [])
    return [{'_arn': f"arn:aws:s3:::{b['Name']}", 'Bucket': b['Name'], 'Creato': b['CreationDate']} for b in buckets]


def fetch_cloudfront(s):
    dists = []
    for page in s.client('cloudfront').get_paginator('list_distributions').paginate():
        dists.extend(page.get('DistributionList', {}).get('Items', []))
    return [{'_arn': d.get('ARN'), 'ID': d['Id'], 'Dominio': d['DomainName'],
             'Alias': ', '.join(d.get('Aliases', {}).get('Items', [])),
             'Stato': d['Status'], 'Abilitato': 'Sì' if d['Enabled'] else 'No'} for d in dists]


def fetch_lambda(s):
    functions = _paginate(s.client('lambda'), 'list_functions', 'Functions')
    return [{'_arn': f.get('FunctionArn'), 'Funzione': f['FunctionName'], 'Runtime': f.get('Runtime', f.get('PackageType', '')),
             'Memoria (MB)': f.get('MemorySize'), 'Ultima modifica': f.get('LastModified', '')}
            for f in functions]


def fetch_dynamodb(s):
    tables = _paginate(s.client('dynamodb'), 'list_tables', 'TableNames')
    return [{'_arn': f'arn:aws:dynamodb:{s.region_name}:{{account}}:table/{t}', 'Tabella': t} for t in tables]


def fetch_apigateway(s):
    apis = _paginate(s.client('apigateway'), 'get_rest_apis', 'items')
    rows = [{'_tags': a.get('tags'), 'ID': a['id'], 'Nome': a['name'], 'Tipo': 'REST', 'Descrizione': a.get('description', '')}
            for a in apis]
    http = _paginate(s.client('apigatewayv2'), 'get_apis', 'Items')
    rows += [{'_tags': a.get('Tags'), 'ID': a['ApiId'], 'Nome': a['Name'], 'Tipo': a.get('ProtocolType', ''),
              'Descrizione': a.get('Description', '')} for a in http]
    return rows


def fetch_sqs(s):
    urls = _paginate(s.client('sqs'), 'list_queues', 'QueueUrls')
    return [{'_arn': f"arn:aws:sqs:{s.region_name}:{u.rstrip('/').split('/')[-2]}:{u.rsplit('/', 1)[-1]}", 'Coda': u.rsplit('/', 1)[-1], 'URL': u} for u in urls]


def fetch_sns(s):
    topics = _paginate(s.client('sns'), 'list_topics', 'Topics')
    return [{'_arn': t['TopicArn'], 'Topic': t['TopicArn'].rsplit(':', 1)[-1], 'ARN': t['TopicArn']} for t in topics]


def fetch_ecr(s):
    repos = _paginate(s.client('ecr'), 'describe_repositories', 'repositories')
    return [{'_arn': r.get('repositoryArn'), 'Repository': r['repositoryName'], 'URI': r['repositoryUri'], 'Creato': r.get('createdAt')}
            for r in repos]


def fetch_eks(s):
    eks = s.client('eks')
    rows = []
    for name in _paginate(eks, 'list_clusters', 'clusters'):
        c = eks.describe_cluster(name=name)['cluster']
        rows.append({'_tags': c.get('tags'), 'Cluster': c['name'], 'Versione': c.get('version', ''), 'Stato': c.get('status', ''),
                     'ARN': c.get('arn', '')})
    return rows


def fetch_eks_nodes(s):
    """Istanze EC2 dei node group EKS (dagli Auto Scaling Group dei node group)."""
    eks, asg = s.client('eks'), s.client('autoscaling')
    rows = []
    for cluster in _paginate(eks, 'list_clusters', 'clusters'):
        for ng in _paginate(eks, 'list_nodegroups', 'nodegroups', clusterName=cluster):
            info = eks.describe_nodegroup(clusterName=cluster, nodegroupName=ng)['nodegroup']
            for group in info.get('resources', {}).get('autoScalingGroups', []):
                details = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[group['name']])
                for g in details['AutoScalingGroups']:
                    for i in g['Instances']:
                        rows.append({'Istanza': i['InstanceId'],
                                     'Stato': f"{i['LifecycleState']} ({i['HealthStatus']})",
                                     'Node group': ng, 'Cluster': cluster})
    return rows


def fetch_cloudformation(s):
    statuses = ['CREATE_COMPLETE', 'UPDATE_COMPLETE', 'ROLLBACK_COMPLETE', 'CREATE_IN_PROGRESS',
                'UPDATE_IN_PROGRESS', 'DELETE_IN_PROGRESS', 'ROLLBACK_IN_PROGRESS',
                'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE']
    stacks = _paginate(s.client('cloudformation'), 'list_stacks', 'StackSummaries', StackStatusFilter=statuses)
    return [{'_arn': x.get('StackId'), 'Stack': x['StackName'], 'Stato': x['StackStatus'], 'Creato': x.get('CreationTime'),
             'Aggiornato': x.get('LastUpdatedTime', '')} for x in stacks]


def fetch_cloudwatch_alarms(s):
    alarms = _paginate(s.client('cloudwatch'), 'describe_alarms', 'MetricAlarms')
    return [{'_arn': a.get('AlarmArn'), 'Allarme': a['AlarmName'], 'Stato': a['StateValue'], 'Metrica': a.get('MetricName', ''),
             'Namespace': a.get('Namespace', '')} for a in alarms]


def fetch_iam_users(s):
    users = _paginate(s.client('iam'), 'list_users', 'Users')
    return [{'Utente': u['UserName'], 'Creato': u['CreateDate'], 'Ultimo accesso': u.get('PasswordLastUsed', '')}
            for u in users if not u['UserName'].startswith('aws-')]


def fetch_iam_roles(s):
    roles = _paginate(s.client('iam'), 'list_roles', 'Roles')
    # solo i ruoli non di sistema
    return [{'Ruolo': r['RoleName'], 'Path': r['Path'], 'Creato': r['CreateDate']}
            for r in roles if not r['RoleName'].startswith('aws-')
            and not r['Path'].startswith('/aws-service-role/')]


def fetch_route53(s):
    zones = _paginate(s.client('route53'), 'list_hosted_zones', 'HostedZones')
    return [{'_arn': 'arn:aws:route53:::hostedzone/' + z['Id'].rsplit('/', 1)[-1], 'Zona': z['Name'], 'Record': z.get('ResourceRecordSetCount', ''),
             'Privata': 'Sì' if z.get('Config', {}).get('PrivateZone') else 'No'} for z in zones]


def fetch_elasticache(s):
    clusters = _paginate(s.client('elasticache'), 'describe_cache_clusters', 'CacheClusters')
    return [{'_arn': c.get('ARN'), 'Cluster': c['CacheClusterId'], 'Motore': f"{c.get('Engine', '')} {c.get('EngineVersion', '')}",
             'Tipo nodo': c.get('CacheNodeType', ''), 'Stato': c.get('CacheClusterStatus', '')} for c in clusters]


def fetch_load_balancers(s):
    lbs = _paginate(s.client('elbv2'), 'describe_load_balancers', 'LoadBalancers')
    return [{'_arn': lb.get('LoadBalancerArn'), 'Nome': lb['LoadBalancerName'], 'Tipo': lb.get('Type', ''), 'Schema': lb.get('Scheme', ''),
             'Stato': lb.get('State', {}).get('Code', ''), 'DNS': lb.get('DNSName', '')} for lb in lbs]


def fetch_secrets(s):
    secrets = _paginate(s.client('secretsmanager'), 'list_secrets', 'SecretList')
    return [{'_tags': x.get('Tags'), 'Segreto': x['Name'], 'Ultima modifica': x.get('LastChangedDate', '')} for x in secrets]


def fetch_ssm_parameters(s):
    params = _paginate(s.client('ssm'), 'describe_parameters', 'Parameters')
    return [{'_arn': f'arn:aws:ssm:{s.region_name}:{{account}}:parameter' + ('' if p['Name'].startswith('/') else '/') + p['Name'], 'Parametro': p['Name'], 'Tipo': p.get('Type', ''), 'Ultima modifica': p.get('LastModifiedDate', '')}
            for p in params]


def fetch_kinesis(s):
    streams = _paginate(s.client('kinesis'), 'list_streams', 'StreamNames')
    return [{'_arn': f'arn:aws:kinesis:{s.region_name}:{{account}}:stream/{x}', 'Stream': x} for x in streams]


def fetch_step_functions(s):
    machines = _paginate(s.client('stepfunctions'), 'list_state_machines', 'stateMachines')
    return [{'_arn': m.get('stateMachineArn'), 'Nome': m['name'], 'Tipo': m.get('type', ''), 'Creato': m.get('creationDate')} for m in machines]


def fetch_efs(s):
    filesystems = _paginate(s.client('efs'), 'describe_file_systems', 'FileSystems')
    return [{'_tags': f.get('Tags'), 'ID': f['FileSystemId'], 'Nome': f.get('Name', ''), 'Stato': f.get('LifeCycleState', ''),
             'Dimensione (byte)': f.get('SizeInBytes', {}).get('Value', '')} for f in filesystems]


# (chiave, titolo, globale, colonne, lettura)
SERVICES = [
    ('vpc', 'VPC di default', False, ['VPC di default', 'CIDR', 'Internet Gateway', 'NAT Gateway'], fetch_vpc),
    ('subnets', 'Subnet della VPC di default', False, ['ID Subnet', 'Nome', 'CIDR', 'Zona', 'Tipo'], fetch_subnets),
    ('security_groups', 'Security Group', False, ['ID', 'Nome', 'Descrizione', 'VPC'], fetch_security_groups),
    ('ec2', 'Istanze EC2', False, ['ID', 'Nome', 'Tipo', 'Stato', 'IP pubblico', 'IP privato'], fetch_ec2),
    ('rds', 'Istanze RDS', False, ['Identificatore', 'Motore', 'Classe', 'Stato', 'Endpoint'], fetch_rds),
    ('s3', 'Bucket S3', True, ['Bucket', 'Creato'], fetch_s3),
    ('cloudfront', 'Distribuzioni CloudFront', True, ['ID', 'Dominio', 'Alias', 'Stato', 'Abilitato'], fetch_cloudfront),
    ('lambda', 'Funzioni Lambda', False, ['Funzione', 'Runtime', 'Memoria (MB)', 'Ultima modifica'], fetch_lambda),
    ('dynamodb', 'Tabelle DynamoDB', False, ['Tabella'], fetch_dynamodb),
    ('apigateway', 'API Gateway', False, ['ID', 'Nome', 'Tipo', 'Descrizione'], fetch_apigateway),
    ('sqs', 'Code SQS', False, ['Coda', 'URL'], fetch_sqs),
    ('sns', 'Topic SNS', False, ['Topic', 'ARN'], fetch_sns),
    ('ecr', 'Repository ECR', False, ['Repository', 'URI', 'Creato'], fetch_ecr),
    ('eks', 'Cluster EKS', False, ['Cluster', 'Versione', 'Stato', 'ARN'], fetch_eks),
    ('eks_nodes', 'Nodi EKS (istanze EC2)', False, ['Istanza', 'Stato', 'Node group', 'Cluster'], fetch_eks_nodes),
    ('cloudformation', 'Stack CloudFormation', False, ['Stack', 'Stato', 'Creato', 'Aggiornato'], fetch_cloudformation),
    ('cloudwatch_alarms', 'Allarmi CloudWatch', False, ['Allarme', 'Stato', 'Metrica', 'Namespace'], fetch_cloudwatch_alarms),
    ('iam_users', 'Utenti IAM', True, ['Utente', 'Creato', 'Ultimo accesso'], fetch_iam_users),
    ('iam_roles', 'Ruoli IAM (non di sistema)', True, ['Ruolo', 'Path', 'Creato'], fetch_iam_roles),
    ('route53', 'Zone Route 53', True, ['Zona', 'Record', 'Privata'], fetch_route53),
    ('elasticache', 'Cluster ElastiCache', False, ['Cluster', 'Motore', 'Tipo nodo', 'Stato'], fetch_elasticache),
    ('load_balancers', 'Load Balancer', False, ['Nome', 'Tipo', 'Schema', 'Stato', 'DNS'], fetch_load_balancers),
    ('secrets', 'Secrets Manager', False, ['Segreto', 'Ultima modifica'], fetch_secrets),
    ('ssm_parameters', 'Parametri SSM', False, ['Parametro', 'Tipo', 'Ultima modifica'], fetch_ssm_parameters),
    ('kinesis', 'Stream Kinesis', False, ['Stream'], fetch_kinesis),
    ('step_functions', 'Step Functions', False, ['Nome', 'Tipo', 'Creato'], fetch_step_functions),
    ('efs', 'File system EFS', False, ['ID', 'Nome', 'Stato', 'Dimensione (byte)'], fetch_efs),
]


def collect(profile, regions, keys, multi_region):
    """
    Legge i servizi indicati (keys) nelle region indicate, tutto in parallelo.

    Ritorna le sezioni nell'ordine di SERVICES:
        [{'key', 'title', 'global', 'columns', 'rows', 'errors'}]
    Con multi_region le righe dei servizi regionali hanno la colonna 'Region'.
    """
    started = time.time()
    specs = [s for s in SERVICES if s[0] in keys]
    tasks = []
    for key, _, is_global, _, _ in specs:
        for r in ([GLOBAL_REGION] if is_global else regions):
            tasks.append((key, r))
    fetchers = {s[0]: s[4] for s in specs}
    results = run_parallel(tasks, lambda t: fetchers[t[0]](aws_session(profile, t[1])),
                           max_workers=16)

    sections = []
    for key, title, is_global, columns, _ in specs:
        rows, errors = [], []
        for (k, r), res, err in results:
            if k != key:
                continue
            if err:
                errors.append(err if is_global else f"{r}: {err}")
                continue
            for row in res:
                rows.append({'Region': r, **row} if multi_region and not is_global else row)
        cols = ['Region'] + columns if multi_region and not is_global else columns
        sections.append({'key': key, 'title': title, 'global': is_global, 'columns': cols,
                         'rows': rows, 'errors': errors})
    return {'sections': sections, 'elapsed': round(time.time() - started, 1)}

"""
Manager - gestione dei singoli servizi AWS (ex AWS/Managers/ManagerFlask, piu' i Security
Group del ManagerTk).

Ogni servizio e' una voce di SERVICES: la classe di aws/services, la funzione che elenca
le risorse, le letture di dettaglio (GET) e le azioni che modificano AWS (POST, che la
pagina esegue solo dopo una conferma). L'elenco di un servizio regionale con la region
"Tutte" legge tutte le region della lista in parallelo e marca ogni risorsa con _region;
dettagli e azioni lavorano sempre sulla region della risorsa.

API:
    GET  /api/manager/projects                 valori del tag Project per servizio (cache della Tagging API)
    GET  /api/manager/<servizio>/list          elenco (region o '__all__'; refresh=1 rilegge i tag)
    GET  /api/manager/<servizio>/<lettura>     dettaglio (region della risorsa + parametri)
    POST /api/manager/<servizio>/<azione>      azione (JSON con region e parametri)
    GET  /api/manager/s3/download              redirect all'URL firmato dell'oggetto
    POST /api/manager/s3/upload                upload multipart (bucket, prefix, file)
"""

import logging
import re

from flask import Blueprint, abort, jsonify, redirect, render_template, request

from aws.cloudwatch_manager import CloudWatchAlarmManager, CloudWatchLogsManager
from aws.services.apigateway import AwsApiGateway
from aws.services.cloudformation import AwsCloudFormation
from aws.services.cloudfront import AwsCloudFront
from aws.services.dynamodb import AwsDynamoDB
from aws.services.ecs import AwsEcs
from aws.services.ec2 import AwsEc2, AwsElasticIp, AwsSecurityGroups
from aws.services.eventbridge import AwsEventBridge
from aws.services.glue import AwsGlue
from aws.services.infrastructure import AwsAutoScaling, AwsEcr, AwsEfs, AwsLoadBalancers
from aws.services.lambda_function import AwsLambda
from aws.services.rds import AwsRds
from aws.services.route53 import AwsRoute53
from aws.services.s3 import AwsS3
from aws.services.secrets import AwsSecrets
from aws.services.sns import AwsSns
from aws.services.sqs import AwsSqs
from aws.services.ssm import AwsSsmParameters
from aws.services.stepfunctions import AwsStepFunctions
from aws.services.vpc import AwsVpc
from common import (ALL, GLOBAL_REGION, api_errors, aws_session, current_profile, current_region,
                    load_config, region_list, run_parallel)
from sections.tagmanager import TagLookup, region_resources

bp = Blueprint('manager', __name__)
logger = logging.getLogger(__name__)


def need(args, name):
    """Parametro obbligatorio di una lettura o di un'azione."""
    value = args.get(name)
    if value in (None, ''):
        raise ValueError(f"Parametro obbligatorio mancante: {name}")
    return value


def limit(name='list_limit'):
    return int(load_config()['manager'][name])


# Ogni voce: titolo, icona, descrizione, globale, classe, elenco, letture (get), azioni (post).
# Le funzioni ricevono l'istanza della classe e i parametri della richiesta.
SERVICES = {
    's3': dict(
        tags=lambda i: ('arn', f"arn:aws:s3:::{i['Name']}"),
        title='S3', icon='fa-bucket', desc='Bucket, proprieta\', cartelle, download e upload di file',
        global_=True, cls=AwsS3, list=lambda o: o.bucket_list(),
        get={'objects': lambda o, a: o.object_list(need(a, 'bucket'), a.get('prefix', ''), limit()),
             'info': lambda o, a: o.bucket_info(need(a, 'bucket'))}),
    'ec2': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='EC2', icon='fa-server', desc='Istanze: dettaglio, avvio e arresto',
        cls=AwsEc2, list=lambda o: o.instances(),
        post={'start': lambda o, d: o.start(need(d, 'id')),
              'stop': lambda o, d: o.stop(need(d, 'id'))}),
    'sg': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='Security Group', icon='fa-shield-halved', desc='Gruppi, regole in ingresso e in uscita, nuova regola',
        cls=AwsSecurityGroups, list=lambda o: o.groups(),
        post={'ingress': lambda o, d: o.add_ingress(need(d, 'id'), need(d, 'from_port'), need(d, 'to_port'),
                                                    need(d, 'protocol'), need(d, 'cidr'), d.get('description', ''))}),
    'cloudfront': dict(
        tags=lambda i: ('arn', i['ARN']),
        title='CloudFront', icon='fa-globe', desc='Distribuzioni, origini e invalidazioni',
        global_=True, cls=AwsCloudFront, list=lambda o: o.distributions(),
        get={'detail': lambda o, a: {'distribution': o.distribution(need(a, 'id')),
                                     'invalidations': o.invalidations(need(a, 'id'))}},
        post={'invalidate': lambda o, d: o.invalidate_all(need(d, 'id'))}),
    'ssm': dict(
        tags=lambda i: ('arn', 'arn:aws:ssm:{region}:{account}:parameter' + ('' if i['Name'].startswith('/') else '/') + i['Name']),
        title='SSM', icon='fa-sliders', desc='Parameter Store: valori e modifica',
        cls=AwsSsmParameters, list=lambda o: o.parameters(),
        post={'update': lambda o, d: o.put_value(need(d, 'name'), d.get('value', ''))}),
    'lambda': dict(
        tags=lambda i: ('arn', i['FunctionArn']),
        title='Lambda', icon='fa-bolt', desc='Funzioni: configurazione, invocazioni, ultimi log',
        cls=AwsLambda, list=lambda o: o.functions(),
        get={'detail': lambda o, a: {'configuration': o.configuration(need(a, 'name')),
                                     'invocations': o.invocations(need(a, 'name')),
                                     'logs': o.last_logs(need(a, 'name'), limit('logs_limit'))}}),
    'eventbridge': dict(
        tags=lambda i: ('arn', i['Arn']),
        title='EventBridge', icon='fa-calendar-check', desc='Regole del bus di default e target',
        cls=AwsEventBridge, list=lambda o: o.rules(),
        get={'detail': lambda o, a: o.rule(need(a, 'name'))},
        post={'enable': lambda o, d: o.set_enabled(need(d, 'name'), bool(d.get('enabled')))}),
    'stepfunctions': dict(
        tags=lambda i: ('arn', i['stateMachineArn']),
        title='StepFunction', icon='fa-diagram-project', desc='Macchine a stati, definizione, esecuzioni',
        cls=AwsStepFunctions, list=lambda o: o.state_machines(),
        get={'detail': lambda o, a: {'detail': o.detail(need(a, 'arn')),
                                     'executions': o.executions(need(a, 'arn'), limit())}}),
    'apigateway': dict(
        tags=lambda i: ('inline', i.get('tags') or i.get('Tags')),
        title='ApiGateway', icon='fa-network-wired', desc='API REST (risorse) e HTTP/WebSocket (route), con gli stage',
        cls=AwsApiGateway, list=lambda o: o.apis(),
        get={'detail': lambda o, a: o.detail(need(a, 'id'), a.get('type', 'REST'))}),
    'dynamodb': dict(
        tags=lambda i: ('arn', 'arn:aws:dynamodb:{region}:{account}:table/' + i['TableName']),
        title='DynamoDB', icon='fa-table', desc='Tabelle e righe a pagine, con Query sulle chiavi e filtri',
        cls=AwsDynamoDB, list=lambda o: o.tables(),
        get={'describe': lambda o, a: o.describe(need(a, 'table')),
             'items': lambda o, a: dynamodb_read(o, a)}),
    'rds': dict(
        tags=lambda i: ('inline', i.get('TagList')),
        title='RDS', icon='fa-database', desc='Istanze database',
        cls=AwsRds, list=lambda o: o.instances()),
    'glue': dict(
        tags=lambda i: ('arn', 'arn:aws:glue:{region}:{account}:job/' + i['Name']),
        title='GlueJob', icon='fa-gears', desc='Job Glue ed esecuzioni',
        cls=AwsGlue, list=lambda o: o.jobs(),
        get={'runs': lambda o, a: o.runs(need(a, 'name'), limit())}),
    'sqs': dict(
        tags=lambda i: ('arn', 'arn:aws:sqs:{region}:' + i['QueueUrl'].rstrip('/').split('/')[-2] + ':' + i['Name']),
        title='SQS', icon='fa-inbox', desc='Code: attributi, invio e ricezione dei messaggi',
        cls=AwsSqs, list=lambda o: o.queues(),
        get={'detail': lambda o, a: o.attributes(need(a, 'url'))},
        post={'send': lambda o, d: {'MessageId': o.send(need(d, 'url'), need(d, 'content'))},
              'consume': lambda o, d: o.consume(need(d, 'url'))}),
    'sns': dict(
        tags=lambda i: ('arn', i['TopicArn']),
        title='SNS', icon='fa-bullhorn', desc='Topic: attributi, sottoscrizioni, pubblicazione',
        cls=AwsSns, list=lambda o: o.topics(),
        get={'detail': lambda o, a: {'attributes': o.attributes(need(a, 'arn')),
                                     'subscriptions': o.subscriptions(need(a, 'arn'))}},
        post={'publish': lambda o, d: {'MessageId': o.publish(need(d, 'arn'), need(d, 'content'))}}),
    'eip': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='ElasticIP', icon='fa-location-dot', desc='Indirizzi IP elastici',
        cls=AwsElasticIp, list=lambda o: o.addresses()),
    'efs': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='EFS', icon='fa-hard-drive', desc='File system e mount target',
        cls=AwsEfs, list=lambda o: o.file_systems(),
        get={'mounts': lambda o, a: o.mount_targets(need(a, 'id'))}),
    'asg': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='ASG', icon='fa-up-right-and-down-left-from-center', desc='Auto Scaling Group e istanze',
        cls=AwsAutoScaling, list=lambda o: o.groups()),
    'alb': dict(
        tags=lambda i: ('arn', i['LoadBalancerArn']),
        title='ALB', icon='fa-scale-balanced', desc='Load balancer, listener, target group e salute dei target',
        cls=AwsLoadBalancers, list=lambda o: o.load_balancers(),
        get={'detail': lambda o, a: {'target_groups': o.target_groups(need(a, 'arn')),
                                     'listeners': o.listeners(need(a, 'arn'))}}),
    'cw_alarms': dict(
        tags=lambda i: ('arn', i['AlarmArn']),
        title='CWAlarms', icon='fa-bell', desc='Allarmi CloudWatch e storico (vista semplice)',
        cls=CloudWatchAlarmManager, list=lambda o: o.list_alarms(),
        get={'history': lambda o, a: o.get_alarm_history(need(a, 'name'))}),
    'cw_logs': dict(
        tags=lambda i: ('arn', i.get('logGroupArn') or i['arn'].removesuffix(':*')),
        title='CWLogs', icon='fa-file-lines', desc='Log group, stream ed eventi (vista semplice)',
        cls=CloudWatchLogsManager, list=lambda o: o.list_log_groups(),
        get={'streams': lambda o, a: o.list_log_streams(need(a, 'group'), limit('logs_limit')),
             'events': lambda o, a: o.get_log_events(need(a, 'group'), need(a, 'stream'), limit('logs_limit'))}),
    'ecr': dict(
        tags=lambda i: ('arn', i['repositoryArn']),
        title='ECR', icon='fa-box', desc='Repository e immagini',
        cls=AwsEcr, list=lambda o: o.repositories(),
        get={'images': lambda o, a: o.images(need(a, 'name'))}),
    'cloudformation': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='CloudFormation', icon='fa-layer-group', desc='Stack: parametri, output, risorse, eventi e template',
        cls=AwsCloudFormation, list=lambda o: o.stacks(),
        get={'detail': lambda o, a: {'resources': o.resources(need(a, 'stack')),
                                     'events': o.events(need(a, 'stack'), limit('logs_limit'))},
             'template': lambda o, a: o.template(need(a, 'stack'))}),
    'route53': dict(
        tags=lambda i: ('arn', 'arn:aws:route53:::hostedzone/' + i['Id'].rsplit('/', 1)[-1]),
        title='Route53', icon='fa-signs-post', desc='Zone ospitate e record DNS',
        global_=True, cls=AwsRoute53, list=lambda o: o.zones(),
        get={'records': lambda o, a: o.records(need(a, 'id'), limit())}),
    'secrets': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='Secrets', icon='fa-key', desc='Secrets Manager: metadati, rotazione, versioni; valore a richiesta',
        cls=AwsSecrets, list=lambda o: o.secrets(),
        get={'detail': lambda o, a: o.describe(need(a, 'id')),
             'value': lambda o, a: o.value(need(a, 'id'))}),
    'ecs': dict(
        tags=lambda i: ('inline', i.get('tags')),
        title='ECS', icon='fa-cubes', desc='Cluster, servizi e task',
        cls=AwsEcs, list=lambda o: o.clusters(),
        get={'detail': lambda o, a: {'services': o.services(need(a, 'cluster')),
                                     'tasks': o.tasks(need(a, 'cluster'), limit())}}),
    'vpc': dict(
        tags=lambda i: ('inline', i.get('Tags')),
        title='VPC', icon='fa-sitemap', desc='Reti, subnet, route table, internet e NAT gateway',
        cls=AwsVpc, list=lambda o: o.vpcs(),
        get={'network': lambda o, a: o.network(need(a, 'id'))}),
}


# Tipo di ARN (servizio, primo pezzo della risorsa) delle risorse elencate da ogni servizio, per la
# tendina Project; None = tutte le risorse del servizio (gli ARN di API Gateway, SQS e SNS non hanno tipo)
ARN_KINDS = {
    's3': ('s3', 'bucket'), 'ec2': ('ec2', 'instance'), 'sg': ('ec2', 'security-group'),
    'cloudfront': ('cloudfront', 'distribution'), 'ssm': ('ssm', 'parameter'), 'lambda': ('lambda', 'function'),
    'eventbridge': ('events', 'rule'), 'stepfunctions': ('states', 'stateMachine'), 'apigateway': ('apigateway', None),
    'dynamodb': ('dynamodb', 'table'), 'rds': ('rds', 'db'), 'glue': ('glue', 'job'), 'sqs': ('sqs', None),
    'sns': ('sns', None), 'eip': ('ec2', 'elastic-ip'), 'efs': ('elasticfilesystem', 'file-system'),
    'asg': ('autoscaling', 'autoScalingGroup'), 'alb': ('elasticloadbalancing', 'loadbalancer'),
    'cw_alarms': ('cloudwatch', 'alarm'), 'cw_logs': ('logs', 'log-group'), 'ecr': ('ecr', 'repository'),
    'cloudformation': ('cloudformation', 'stack'), 'route53': ('route53', 'hostedzone'),
    'secrets': ('secretsmanager', 'secret'), 'ecs': ('ecs', 'cluster'), 'vpc': ('ec2', 'vpc'),
}


def service_of_arn(arn):
    """(chiave del servizio del Manager, region dell'ARN), oppure (None, '') se nessun servizio elenca quella risorsa."""
    parts = arn.split(':', 5)
    if len(parts) < 6:
        return None, ''
    aws_service, region, resource = parts[2], parts[3], parts[5]
    if aws_service == 's3':  # bucket: arn:aws:s3:::nome, senza region e senza tipo
        kind = 'bucket' if not region and '/' not in resource else ''
    else:
        kind = re.split(r'[:/]', resource, maxsplit=1)[0]
    for key, (svc, svc_kind) in ARN_KINDS.items():
        if svc == aws_service and svc_kind in (None, kind):
            return key, region
    return None, ''


def projects_by_service(resources, region):
    """
    {servizio: [valori di Project]} dalle risorse della Tagging API (con 'arn' e 'tags'): per i
    servizi regionali solo le risorse della region scelta (tutte con '__all__'), per i globali tutte.
    """
    found = {key: set() for key in SERVICES}
    for risorsa in resources:
        project = (risorsa.get('tags') or {}).get('Project')
        if not project:
            continue
        key, arn_region = service_of_arn(risorsa['arn'])
        if key and (SERVICES[key].get('global_') or region == ALL or arn_region == region):
            found[key].add(project)
    return {key: sorted(values) for key, values in found.items()}


def dynamodb_read(o, a):
    """Una pagina di righe DynamoDB (Query o Scan, vedi AwsDynamoDB.read) dai parametri della pagina."""
    page_size = max(1, min(int(a.get('page_size') or 100), limit()))
    return o.read(need(a, 'table'), index=a.get('index', ''), pk=a.get('pk', ''),
                  sort_op=a.get('sort_op', ''), sort_value=a.get('sort_value', ''),
                  sort_value2=a.get('sort_value2', ''), filter_attr=a.get('filter_attr', '').strip(),
                  filter_op=a.get('filter_op', ''), filter_value=a.get('filter_value', ''),
                  filter_type=a.get('filter_type', 'S'), descending=a.get('descending') == '1',
                  page_size=page_size, max_read=limit('dynamodb_max_read'), start=a.get('start'))


def service(name):
    if name not in SERVICES:
        abort(404)
    return SERVICES[name]


def instance(spec, region=None):
    """Istanza della classe del servizio nella region della risorsa (globale per S3 e CloudFront)."""
    region = GLOBAL_REGION if spec.get('global_') else (region or current_region(allow_all=False))
    return spec['cls'](aws_session(current_profile(), region))


def nav_services():
    return [{'id': k, 'title': v['title'], 'icon': v['icon'], 'desc': v['desc'],
             'global': bool(v.get('global_'))} for k, v in SERVICES.items()]


# ----------------------------------------------------------------------
# Pagine
# ----------------------------------------------------------------------

def tag_settings():
    """Valori suggeriti e chiavi con le sottovoci, per la tendina Project (tag_match.js)."""
    config = load_config()
    return dict(suggested_tags=config['suggested_tags'],
                prefix_match_keys=config['tag_manager']['prefix_match_keys'])


@bp.route('/manager')
def index():
    return render_template('manager.html', services=nav_services(), service=None, current=None, **tag_settings())


@bp.route('/manager/<name>')
def service_page(name):
    service(name)
    services = nav_services()
    return render_template('manager.html', services=services, service=name,
                           current=next(s for s in services if s['id'] == name),
                           ddb_max_read=limit('dynamodb_max_read'), **tag_settings())


# ----------------------------------------------------------------------
# API
# ----------------------------------------------------------------------

@bp.route('/api/manager/projects')
@api_errors
def projects():
    """
    Valori del tag Project presenti in ogni servizio, per la tendina della seconda barra.
    Dalla cache della Tagging API del Tag Manager (la stessa delle icone dei tag, letture
    gratuite): tutte le region della lista piu' us-east-1, perche' i bucket S3 compaiono
    nella region del bucket e i servizi globali in us-east-1.
    """
    profile = current_profile()
    regions = list(dict.fromkeys(load_config()['regions'] + [GLOBAL_REGION]))
    resources, warnings = [], []
    for r, res, err in run_parallel(regions, lambda r: region_resources(profile, r, 'tagging', False)):
        if err:
            warnings.append(f"{r}: {err}")
            continue
        resources.extend(res[0]['resources'])
    return jsonify({'services': projects_by_service(resources, current_region()), 'warnings': warnings})


@bp.route('/api/manager/<name>/list')
@api_errors
def list_items(name):
    """Risorse del servizio nella region scelta o in tutte ('__all__')."""
    spec = service(name)
    profile = current_profile()
    refresh = request.args.get('refresh') == '1'
    if spec.get('global_'):
        items = spec['list'](instance(spec))
        add_tags(spec, items, profile, refresh)
        return jsonify({'items': items, 'warnings': [], 'global': True})
    items, warnings = [], []
    results = run_parallel(region_list(current_region()),
                           lambda r: spec['list'](spec['cls'](aws_session(profile, r))))
    for r, res, err in results:
        if err:
            warnings.append(f"{r}: {err}")
            continue
        for item in res:
            item['_region'] = r
            items.append(item)
    add_tags(spec, items, profile, refresh)
    return jsonify({'items': items, 'warnings': warnings, 'global': False})


def add_tags(spec, items, profile, refresh=False):
    """
    Aggiunge _tags ({chiave: valore}, None se non si possono sapere) per le icone e il
    dettaglio. Dall'elenco se li contiene gia', altrimenti dalla Tagging API per ARN (cache
    del Tag Manager, riletta con refresh; gli ARN che non vi compaiono si leggono a parte).
    """
    entries = []
    for item in items:
        try:
            entries.append((spec['tags'](item), item.get('_region', '')))
        except Exception as e:
            logger.warning(f"Tag non determinabili: {e}")
            entries.append((None, ''))
    try:
        tags = TagLookup(profile, refresh).resolve_all(entries)
    except Exception as e:
        logger.warning(f"Tag non determinabili: {e}")
        tags = [None] * len(items)
    for item, item_tags in zip(items, tags):
        item['_tags'] = item_tags


# Le route fisse di S3 vengono prima di quelle generiche (Flask preferisce le regole senza variabili)
@bp.route('/api/manager/s3/download')
@api_errors
def s3_download():
    """Redirect all'URL firmato (valido un'ora) per scaricare l'oggetto."""
    spec = SERVICES['s3']
    return redirect(instance(spec).presigned_url(need(request.args, 'bucket'), need(request.args, 'key')))


@bp.route('/api/manager/s3/upload', methods=['POST'])
@api_errors
def s3_upload():
    """Carica un file nella cartella (prefix) del bucket, senza passare dal disco."""
    uploaded = request.files.get('file')
    if not uploaded or not uploaded.filename:
        raise ValueError('Nessun file da caricare')
    bucket, prefix = need(request.form, 'bucket'), request.form.get('prefix', '')
    key = prefix + uploaded.filename.replace('\\', '/').rsplit('/', 1)[-1]
    instance(SERVICES['s3']).upload(bucket, key, uploaded.stream)
    return jsonify({'message': f"Caricato s3://{bucket}/{key}", 'key': key})


@bp.route('/api/manager/<name>/<op>')
@api_errors
def read(name, op):
    spec = service(name)
    fn = spec.get('get', {}).get(op)
    if not fn:
        abort(404)
    return jsonify({'data': fn(instance(spec), request.args)})


@bp.route('/api/manager/<name>/<op>', methods=['POST'])
@api_errors
def action(name, op):
    spec = service(name)
    fn = spec.get('post', {}).get(op)
    if not fn:
        abort(404)
    return jsonify({'data': fn(instance(spec), request.get_json(silent=True) or {})})

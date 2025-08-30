# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError

"""
Questo script Flask fornisce una dashboard semplice per visualizzare le risorse AWS. 
Creato con l'IA:
- fammi un nuovo script che mi crea variabili d'ambiente con le informazioni: vpc di default, subnets e igw, natg, tutti i security group, tutte le role iam non di default, tutti gli ECR, tutti eks cluster, tutti gli eks nodes, tutte le ec2, tutti gli RDS,
- facciamo così: fammi un nuovo script che mi crea variabili d'ambiente con le informazioni: vpc di default, subnets e igw, natg, tutti i security group, tutti gli ECR, tutti eks cluster, tutti gli eks nodes, tutte le ec2, tutti gli RDS,
- nello script aggiungi S3, cloudfront, cloudformation, cloudwatch e altri 5 servizi a tua scelta
- dammi il codice della funzione print_section_header
- ora dammi tutto lo script in python e che sia graficamente carino , magari con flask e libreria grafica bootstrap

"""

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Cambia con una chiave segreta sicura

# Configurazione di default
DEFAULT_REGION = "eu-central-1"
DEFAULT_PROFILE = "default"

def get_aws_clients(region=None, profile=None):
    """
    Crea i client AWS con la regione e il profilo specificati.
    """
    if not region:
        region = session.get('aws_region', DEFAULT_REGION)
    if not profile:
        profile = session.get('aws_profile', DEFAULT_PROFILE)
    
    try:
        # Crea una sessione boto3 con il profilo specificato
        boto3_session = boto3.Session(profile_name=profile)
        
        # Inizializza tutti i client con la sessione e regione
        clients = {
            'ec2': boto3_session.client('ec2', region_name=region),
            'ecr': boto3_session.client('ecr', region_name=region),
            'eks': boto3_session.client('eks', region_name=region),
            'rds': boto3_session.client('rds', region_name=region),
            's3': boto3_session.client('s3', region_name=region),
            'cloudfront': boto3_session.client('cloudfront', region_name=region),
            'cloudformation': boto3_session.client('cloudformation', region_name=region),
            'cloudwatch': boto3_session.client('cloudwatch', region_name=region),
            'lambda': boto3_session.client('lambda', region_name=region),
            'dynamodb': boto3_session.client('dynamodb', region_name=region),
            'sqs': boto3_session.client('sqs', region_name=region),
            'sns': boto3_session.client('sns', region_name=region),
            'apigateway': boto3_session.client('apigateway', region_name=region),
            'autoscaling': boto3_session.client('autoscaling', region_name=region),
            'iam': boto3_session.client('iam', region_name=region),
            'route53': boto3_session.client('route53', region_name=region),
            'elasticache': boto3_session.client('elasticache', region_name=region),
            'elbv2': boto3_session.client('elbv2', region_name=region),
            'secretsmanager': boto3_session.client('secretsmanager', region_name=region),
            'ssm': boto3_session.client('ssm', region_name=region),
            'kinesis': boto3_session.client('kinesis', region_name=region),
            'stepfunctions': boto3_session.client('stepfunctions', region_name=region),
            'efs': boto3_session.client('efs', region_name=region)
        }
        return clients, region, profile
    except Exception as e:
        print(f"Errore nella creazione dei client AWS: {e}")
        return None, region, profile

def get_available_regions():
    """
    Restituisce una lista delle regioni AWS disponibili.
    """
    try:
        ec2 = boto3.client('ec2')
        regions = ec2.describe_regions()['Regions']
        return [region['RegionName'] for region in regions]
    except:
        # Fallback a una lista predefinita se non riesce a recuperare le regioni
        return [
            'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
            'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
            'ap-south-1', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
        ]

def get_available_profiles():
    """
    Restituisce una lista dei profili AWS disponibili.
    """
    try:
        session_boto = boto3.Session()
        profiles = session_boto.available_profiles
        return profiles if profiles else ['default']
    except:
        return ['default']

def get_aws_resources():
    """
    Recupera le informazioni su varie risorse AWS.
    """
    # Ottieni i client AWS con la configurazione corrente
    clients, current_region, current_profile = get_aws_clients()
    
    if not clients:
        return {'error': 'Impossibile creare i client AWS. Verificare le credenziali e la configurazione.'}
    
    resources = {
        'current_region': current_region,
        'current_profile': current_profile
    }

    # Estrai i client dal dizionario
    ec2_client = clients['ec2']
    ecr_client = clients['ecr']
    eks_client = clients['eks']
    rds_client = clients['rds']
    s3_client = clients['s3']
    cloudfront_client = clients['cloudfront']
    cloudformation_client = clients['cloudformation']
    cloudwatch_client = clients['cloudwatch']
    lambda_client = clients['lambda']
    dynamodb_client = clients['dynamodb']
    sqs_client = clients['sqs']
    sns_client = clients['sns']
    apigateway_client = clients['apigateway']
    autoscaling_client = clients['autoscaling']
    iam_client = clients['iam']
    route53_client = clients['route53']
    elasticache_client = clients['elasticache']
    elbv2_client = clients['elbv2']
    secretsmanager_client = clients['secretsmanager']
    ssm_client = clients['ssm']
    kinesis_client = clients['kinesis']
    stepfunctions_client = clients['stepfunctions']
    efs_client = clients['efs']

    # --- 1. Componenti di Rete della VPC di Default ---
    try:
        vpcs = ec2_client.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
        default_vpc = vpcs['Vpcs'][0] if vpcs['Vpcs'] else None
        resources['default_vpc'] = default_vpc

        if default_vpc:
            vpc_id = default_vpc['VpcId']
            resources['vpc_id'] = vpc_id
            resources['vpc_cidr_block'] = default_vpc['CidrBlock']

            # Subnet Pubbliche
            public_subnets = ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'map-public-ip-on-launch', 'Values': ['true']}
                ]
            )
            resources['public_subnets'] = public_subnets['Subnets']

            # Subnet Private
            private_subnets = ec2_client.describe_subnets(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'map-public-ip-on-launch', 'Values': ['false']}
                ]
            )
            resources['private_subnets'] = private_subnets['Subnets']

            # Internet Gateway
            igws = ec2_client.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
            )
            resources['internet_gateway'] = igws['InternetGateways'][0] if igws['InternetGateways'] else None

            # NAT Gateway
            nat_gateways = ec2_client.describe_nat_gateways(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]},
                    {'Name': 'state', 'Values': ['available']}
                ]
            )
            resources['nat_gateway'] = nat_gateways['NatGateways'][0] if nat_gateways['NatGateways'] else None
    except Exception as e:
        print(f"Errore nel recupero delle informazioni VPC: {e}")
        resources['default_vpc'] = None

    # --- 2. Security Groups ---
    try:
        security_groups = ec2_client.describe_security_groups(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}] if 'vpc_id' in resources else []
        )
        resources['security_groups'] = security_groups['SecurityGroups']
    except Exception as e:
        print(f"Errore nel recupero dei Security Groups: {e}")
        resources['security_groups'] = []

    # --- 3. Repository ECR ---
    try:
        ecr_repos = ecr_client.describe_repositories()
        resources['ecr_repositories'] = ecr_repos['repositories']
    except Exception as e:
        print(f"Errore nel recupero dei repository ECR: {e}")
        resources['ecr_repositories'] = []

    # --- 4. Cluster EKS e Nodi ---
    try:
        eks_clusters = eks_client.list_clusters()['clusters']
        resources['eks_clusters'] = []
        resources['eks_nodes'] = []

        for cluster_name in eks_clusters:
            cluster_info = eks_client.describe_cluster(name=cluster_name)['cluster']
            resources['eks_clusters'].append(cluster_info)

            node_groups = eks_client.list_node_groups(clusterName=cluster_name)['nodeGroups']
            for ng_name in node_groups:
                ng_info = eks_client.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name)['nodeGroup']
                resources['eks_nodes'].append(ng_info)
                # Recupera le istanze EC2 associate all'Auto Scaling Group del Node Group
                for asg in ng_info.get('resources', {}).get('autoScalingGroups', []):
                    asg_name = asg['name']
                    asg_details = autoscaling_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
                    for instance in asg_details['AutoScalingGroups'][0]['Instances']:
                        resources['eks_nodes'].append({
                            'InstanceId': instance['InstanceId'],
                            'LaunchConfigurationName': instance.get('LaunchConfigurationName'),
                            'LifecycleState': instance['LifecycleState'],
                            'HealthStatus': instance['HealthStatus'],
                            'NodegroupName': ng_name,
                            'ClusterName': cluster_name
                        })
    except Exception as e:
        print(f"Errore nel recupero dei cluster EKS o nodi: {e}")
        resources['eks_clusters'] = []
        resources['eks_nodes'] = []

    # --- 5. Istanze EC2 ---
    try:
        ec2_instances = ec2_client.describe_instances(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}] if 'vpc_id' in resources else []
        )
        instances = []
        for reservation in ec2_instances['Reservations']:
            instances.extend(reservation['Instances'])
        resources['ec2_instances'] = instances
    except Exception as e:
        print(f"Errore nel recupero delle istanze EC2: {e}")
        resources['ec2_instances'] = []

    # --- 6. Istanze RDS ---
    try:
        rds_instances = rds_client.describe_db_instances()
        resources['rds_instances'] = rds_instances['DBInstances']
    except Exception as e:
        print(f"Errore nel recupero delle istanze RDS: {e}")
        resources['rds_instances'] = []

    # --- 7. S3 Buckets ---
    try:
        s3_buckets = s3_client.list_buckets()
        resources['s3_buckets'] = s3_buckets['Buckets']
    except Exception as e:
        print(f"Errore nel recupero dei bucket S3: {e}")
        resources['s3_buckets'] = []

    # --- 8. CloudFront Distributions ---
    try:
        cf_distributions = cloudfront_client.list_distributions().get('DistributionList', {}).get('Items', [])
        resources['cloudfront_distributions'] = cf_distributions
    except Exception as e:
        print(f"Errore nel recupero delle distribuzioni CloudFront: {e}")
        resources['cloudfront_distributions'] = []

    # --- 9. CloudFormation Stacks ---
    try:
        cfn_stacks = cloudformation_client.list_stacks(
            StackStatusFilter=[
                'CREATE_COMPLETE', 'UPDATE_COMPLETE', 'ROLLBACK_COMPLETE',
                'CREATE_IN_PROGRESS', 'UPDATE_IN_PROGRESS', 'DELETE_IN_PROGRESS',
                'ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_IN_PROGRESS'
            ]
        ).get('StackSummaries', [])
        resources['cloudformation_stacks'] = cfn_stacks
    except Exception as e:
        print(f"Errore nel recupero degli stack CloudFormation: {e}")
        resources['cloudformation_stacks'] = []

    # --- 10. CloudWatch Alarms ---
    try:
        cw_alarms = cloudwatch_client.describe_alarms().get('MetricAlarms', [])
        resources['cloudwatch_alarms'] = cw_alarms
    except Exception as e:
        print(f"Errore nel recupero degli allarmi CloudWatch: {e}")
        resources['cloudwatch_alarms'] = []

    # --- 11. Lambda Functions ---
    try:
        lambda_functions = lambda_client.list_functions().get('Functions', [])
        resources['lambda_functions'] = lambda_functions
    except Exception as e:
        print(f"Errore nel recupero delle funzioni Lambda: {e}")
        resources['lambda_functions'] = []

    # --- 12. DynamoDB Tables ---
    try:
        ddb_tables = dynamodb_client.list_tables().get('TableNames', [])
        resources['dynamodb_tables'] = ddb_tables
    except Exception as e:
        print(f"Errore nel recupero delle tabelle DynamoDB: {e}")
        resources['dynamodb_tables'] = []

    # --- 13. SQS Queues ---
    try:
        sqs_queues = sqs_client.list_queues().get('QueueUrls', [])
        resources['sqs_queues'] = sqs_queues
    except Exception as e:
        print(f"Errore nel recupero delle code SQS: {e}")
        resources['sqs_queues'] = []

    # --- 14. SNS Topics ---
    try:
        sns_topics = sns_client.list_topics().get('Topics', [])
        resources['sns_topics'] = sns_topics
    except Exception as e:
        print(f"Errore nel recupero degli argomenti SNS: {e}")
        resources['sns_topics'] = []

    # --- 15. API Gateway REST APIs ---
    try:
        api_gateway_rest_apis = apigateway_client.get_rest_apis().get('items', [])
        resources['api_gateway_rest_apis'] = api_gateway_rest_apis
    except Exception as e:
        print(f"Errore nel recupero delle API Gateway REST APIs: {e}")
        resources['api_gateway_rest_apis'] = []

    # --- 16. IAM Users (Solo utenti non di sistema) ---
    try:
        iam_users = iam_client.list_users().get('Users', [])
        # Filtra utenti non di sistema (esclude quelli che iniziano con 'aws-' o sono di servizio)
        filtered_users = [user for user in iam_users if not user['UserName'].startswith('aws-')]
        resources['iam_users'] = filtered_users
    except Exception as e:
        print(f"Errore nel recupero degli utenti IAM: {e}")
        resources['iam_users'] = []

    # --- 17. IAM Roles (Solo ruoli non di default) ---
    try:
        iam_roles = iam_client.list_roles().get('Roles', [])
        # Filtra ruoli non di sistema AWS
        filtered_roles = [role for role in iam_roles if not role['RoleName'].startswith('aws-') 
                         and not role['Path'].startswith('/aws-service-role/')]
        resources['iam_roles'] = filtered_roles
    except Exception as e:
        print(f"Errore nel recupero dei ruoli IAM: {e}")
        resources['iam_roles'] = []

    # --- 18. Route53 Hosted Zones ---
    try:
        route53_zones = route53_client.list_hosted_zones().get('HostedZones', [])
        resources['route53_zones'] = route53_zones
    except Exception as e:
        print(f"Errore nel recupero delle zone Route53: {e}")
        resources['route53_zones'] = []

    # --- 19. ElastiCache Clusters ---
    try:
        elasticache_clusters = elasticache_client.describe_cache_clusters().get('CacheClusters', [])
        resources['elasticache_clusters'] = elasticache_clusters
    except Exception as e:
        print(f"Errore nel recupero dei cluster ElastiCache: {e}")
        resources['elasticache_clusters'] = []

    # --- 20. Application Load Balancers ---
    try:
        load_balancers = elbv2_client.describe_load_balancers().get('LoadBalancers', [])
        resources['load_balancers'] = load_balancers
    except Exception as e:
        print(f"Errore nel recupero dei Load Balancer: {e}")
        resources['load_balancers'] = []

    # --- 21. Secrets Manager Secrets ---
    try:
        secrets = secretsmanager_client.list_secrets().get('SecretList', [])
        resources['secrets'] = secrets
    except Exception as e:
        print(f"Errore nel recupero dei segreti: {e}")
        resources['secrets'] = []

    # --- 22. SSM Parameters ---
    try:
        ssm_parameters = ssm_client.describe_parameters().get('Parameters', [])
        resources['ssm_parameters'] = ssm_parameters
    except Exception as e:
        print(f"Errore nel recupero dei parametri SSM: {e}")
        resources['ssm_parameters'] = []

    # --- 23. Kinesis Streams ---
    try:
        kinesis_streams = kinesis_client.list_streams().get('StreamNames', [])
        resources['kinesis_streams'] = kinesis_streams
    except Exception as e:
        print(f"Errore nel recupero degli stream Kinesis: {e}")
        resources['kinesis_streams'] = []

    # --- 24. Step Functions ---
    try:
        step_functions = stepfunctions_client.list_state_machines().get('stateMachines', [])
        resources['step_functions'] = step_functions
    except Exception as e:
        print(f"Errore nel recupero delle Step Functions: {e}")
        resources['step_functions'] = []

    # --- 25. EFS File Systems ---
    try:
        efs_filesystems = efs_client.describe_file_systems().get('FileSystems', [])
        resources['efs_filesystems'] = efs_filesystems
    except Exception as e:
        print(f"Errore nel recupero dei file system EFS: {e}")
        resources['efs_filesystems'] = []

    return resources

@app.route('/')
def index():
    """
    Renderizza la pagina principale del dashboard con le informazioni sulle risorse AWS.
    """
    # Inizializza la sessione se non esiste
    if 'aws_region' not in session:
        session['aws_region'] = DEFAULT_REGION
        print(f"Inizializzata regione di default: {DEFAULT_REGION}")
    if 'aws_profile' not in session:
        session['aws_profile'] = DEFAULT_PROFILE
        print(f"Inizializzato profilo di default: {DEFAULT_PROFILE}")
    
    print(f"Caricamento dashboard con regione: {session.get('aws_region')}, profilo: {session.get('aws_profile')}")
    
    aws_data = get_aws_resources()
    available_regions = get_available_regions()
    available_profiles = get_available_profiles()
    
    return render_template('index.html', 
                         aws_data=aws_data,
                         available_regions=available_regions,
                         available_profiles=available_profiles)

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """
    Aggiorna la regione e il profilo AWS.
    """
    try:
        new_region = request.form.get('region')
        new_profile = request.form.get('profile')
        
        print(f"Ricevuta richiesta di aggiornamento: region={new_region}, profile={new_profile}")
        
        if new_region and new_region != session.get('aws_region'):
            session['aws_region'] = new_region
            print(f"Regione aggiornata a: {new_region}")
        
        if new_profile and new_profile != session.get('aws_profile'):
            session['aws_profile'] = new_profile
            print(f"Profilo aggiornato a: {new_profile}")
        
        # Forza il salvataggio della sessione
        session.permanent = True
        
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Errore nell'aggiornamento delle impostazioni: {e}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Per eseguire l'app in modalità sviluppo
    # Assicurati che le tue credenziali AWS siano configurate (es. ~/.aws/credentials o variabili d'ambiente)
    app.run(debug=True, host='0.0.0.0', port=5042)


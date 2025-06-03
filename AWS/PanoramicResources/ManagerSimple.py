# app.py
from flask import Flask, render_template
import boto3
import os

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

# Configurazione della regione AWS (puoi impostarla anche come variabile d'ambiente)
AWS_REGION = os.environ.get("AWS_REGION", "eu-central-1")

# Inizializza i client Boto3
ec2_client = boto3.client('ec2', region_name=AWS_REGION)
ecr_client = boto3.client('ecr', region_name=AWS_REGION)
eks_client = boto3.client('eks', region_name=AWS_REGION)
rds_client = boto3.client('rds', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
cloudfront_client = boto3.client('cloudfront', region_name=AWS_REGION)
cloudformation_client = boto3.client('cloudformation', region_name=AWS_REGION)
cloudwatch_client = boto3.client('cloudwatch', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
sqs_client = boto3.client('sqs', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)
apigateway_client = boto3.client('apigateway', region_name=AWS_REGION)
autoscaling_client = boto3.client('autoscaling', region_name=AWS_REGION) # Per i nodi EKS

def get_aws_resources():
    """
    Recupera le informazioni su varie risorse AWS.
    """
    resources = {}

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

    return resources

@app.route('/')
def index():
    """
    Renderizza la pagina principale del dashboard con le informazioni sulle risorse AWS.
    """
    aws_data = get_aws_resources()
    return render_template('index.html', aws_data=aws_data)

if __name__ == '__main__':
    # Per eseguire l'app in modalità sviluppo
    # Assicurati che le tue credenziali AWS siano configurate (es. ~/.aws/credentials o variabili d'ambiente)
    app.run(debug=True, host='0.0.0.0', port=5042)


"""Caricamento di file CSV da S3 a RDS MySQL con AWS Glue (crawler, job e workflow).

Flusso: un file .csv caricato in s3://<bucket>/INPUT/ genera un evento EventBridge che avvia una Step
Function; la Step Function avvia il workflow Glue (crawler -> job) e ne controlla lo stato ogni 30 secondi.
- crawler: legge i CSV (separatore ";", con intestazione) e aggiorna la tabella "input" del Data Catalog
- job (Glue 5.0, Spark): legge la tabella del catalogo e scrive le righe nella tabella "persone" di RDS;
  con il job bookmark legge solo i file nuovi
- RDS MySQL 8.4 nelle subnet indicate, raggiungibile solo dal security group di Glue
- la connessione JDBC di Glue lavora nella VPC: per leggere S3 serve un endpoint gateway S3 sulla tabella di
  routing della subnet (creato dallo stack se si passa routetableid)

Rispetto al CloudFormation la Step Function chiama direttamente Glue (startWorkflowRun, getWorkflowRun)
invece di passare da due Lambda.
"""

import os

from aws_cdk import (
    CfnCondition,
    CfnOutput,
    CfnParameter,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_events as events,
    aws_events_targets as targets,
    aws_glue as glue,
    aws_iam as iam,
    aws_logs as logs,
    aws_rds as rds,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    custom_resources as cr,
)
from constructs import Construct

from .naming import nome_risorsa
from .tags import TAGS

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INPUT_PREFIX = "INPUT/"
CATALOG_TABLE = "input"  # il crawler chiama la tabella come la cartella dei CSV
RDS_DATABASE = "mydb"
RDS_TABLE = "persone"


class Cdk14GlueCrawlerRdsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # database del Data Catalog: solo minuscole, numeri e _ (Athena non accetta i trattini)
        catalog_database = nome_risorsa(self, "csv").replace("-", "_")
        classifier_name = nome_risorsa(self, "csv-classifier")
        job_log_group = f"/aws-glue/jobs/{nome_risorsa(self, 'job')}"

        # VPC, subnet, zona e tabella di routing: per default quelle della VPC di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 2)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_1 = subnet_parameter(self, "subnetid1", default_subnets[0], "subnet della connessione Glue e del database")
        subnet_1_az = CfnParameter(self, "subnetaz1", type="AWS::EC2::AvailabilityZone::Name",
                                   default=default_subnets[0].availability_zone,
                                   description="zona della subnet 1 (richiesta dalla connessione Glue)").value_as_string
        subnet_2 = subnet_parameter(self, "subnetid2", default_subnets[1], "seconda subnet del database, in un'altra zona")
        route_table = CfnParameter(self, "routetableid", type="String",
            default=default_subnets[0].route_table.route_table_id,
            description="tabella di routing della subnet 1 per l'endpoint gateway S3 (vuoto se l'endpoint c'e' gia')")

        azs = [Fn.select(0, Fn.get_azs()), Fn.select(1, Fn.get_azs())]
        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=azs,
                                          private_subnet_ids=[subnet_1, subnet_2])

        # Endpoint gateway S3 (gratuito), solo se indicata la tabella di routing
        has_route_table = CfnCondition(self, "CreateS3Endpoint",
                                       expression=Fn.condition_not(Fn.condition_equals(route_table.value_as_string, "")))
        endpoint = ec2.CfnVPCEndpoint(self, "S3Endpoint", vpc_id=vpc_id, vpc_endpoint_type="Gateway",
                                      service_name=f"com.amazonaws.{self.region}.s3",
                                      route_table_ids=[route_table.value_as_string])
        endpoint.cfn_options.condition = has_route_table

        bucket = s3.Bucket(self, "DataBucket", event_bridge_enabled=True, enforce_ssl=True,
                           block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                           removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True,
                           lifecycle_rules=[s3.LifecycleRule(prefix="temp/", expiration=Duration.days(7))])

        # Security group di Glue: Glue chiede tutte le porte TCP aperte verso se stesso (comunicazione tra i worker)
        glue_sg = ec2.SecurityGroup(self, "GlueSecurityGroup", vpc=vpc, allow_all_outbound=True,
                                    description="Glue: worker del job e connessione JDBC")
        glue_sg.add_ingress_rule(glue_sg, ec2.Port.all_tcp(), "traffico tra i worker Glue")

        database = rds.DatabaseInstance(self, "Database",
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_4_8),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=vpc, vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            database_name=RDS_DATABASE,
            credentials=rds.Credentials.from_generated_secret("admin", exclude_characters=" %+~`#$&*()|[]{}:;<>?!'/@\"\\"),
            allocated_storage=20, storage_type=rds.StorageType.GP3, storage_encrypted=True,
            multi_az=False, publicly_accessible=False, backup_retention=Duration.days(0),
            removal_policy=RemovalPolicy.DESTROY, deletion_protection=False)
        database.connections.allow_default_port_from(glue_sg, "MySQL dal job Glue")

        # Ruolo di Glue: servizio Glue, dati del bucket, script del job
        role = iam.Role(self, "GlueRole", assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")])
        bucket.grant_read_write(role)
        script = s3_assets.Asset(self, "JobScript", path=os.path.join(ROOT, "glue", "csv_to_rds.py"))
        script.grant_read(role)

        catalog = glue.CfnDatabase(self, "CatalogDatabase", catalog_id=self.account,
            database_input=glue.CfnDatabase.DatabaseInputProperty(name=catalog_database,
                                                                  description="CSV caricati dal cdk14"))
        classifier = glue.CfnClassifier(self, "CsvClassifier", csv_classifier=glue.CfnClassifier.CsvClassifierProperty(
            name=classifier_name, delimiter=";", contains_header="PRESENT", quote_symbol='"'))
        crawler = glue.CfnCrawler(self, "Crawler", name=nome_risorsa(self, "crawler"), role=role.role_arn,
            database_name=catalog_database, classifiers=[classifier_name],
            targets=glue.CfnCrawler.TargetsProperty(s3_targets=[glue.CfnCrawler.S3TargetProperty(
                path=f"s3://{bucket.bucket_name}/{INPUT_PREFIX}")]),
            schema_change_policy=glue.CfnCrawler.SchemaChangePolicyProperty(
                update_behavior="UPDATE_IN_DATABASE", delete_behavior="LOG"))
        crawler.node.add_dependency(catalog)
        crawler.node.add_dependency(classifier)

        connection = glue.CfnConnection(self, "RdsConnection", catalog_id=self.account,
            connection_input=glue.CfnConnection.ConnectionInputProperty(
                name=nome_risorsa(self, "rds"), connection_type="JDBC",
                connection_properties={
                    "JDBC_CONNECTION_URL": f"jdbc:mysql://{database.db_instance_endpoint_address}:3306/{RDS_DATABASE}",
                    "USERNAME": database.secret.secret_value_from_json("username").unsafe_unwrap(),
                    "PASSWORD": database.secret.secret_value_from_json("password").unsafe_unwrap(),
                },
                physical_connection_requirements=glue.CfnConnection.PhysicalConnectionRequirementsProperty(
                    subnet_id=subnet_1, availability_zone=subnet_1_az,
                    security_group_id_list=[glue_sg.security_group_id])))

        # Database del Data Catalog: CloudFormation non accetta Tags su AWS::Glue::Database, l'API di Glue si'.
        # Una custom resource chiama glue:TagResource alla creazione e a ogni aggiornamento: tag standard e Name = nome
        catalog_arn = f"arn:{self.partition}:glue:{self.region}:{self.account}:database/{catalog_database}"
        tag_call = cr.AwsSdkCall(service="Glue", action="TagResource",
                                 parameters={"ResourceArn": catalog_arn, "TagsToAdd": {"Name": catalog_database, **TAGS}},
                                 physical_resource_id=cr.PhysicalResourceId.of(catalog_arn))
        catalog_tags = cr.AwsCustomResource(self, "CatalogDatabaseTags", on_create=tag_call, on_update=tag_call,
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(actions=["glue:TagResource"], resources=[catalog_arn])]),
            install_latest_aws_sdk=False, function_name=nome_risorsa(self, "glue-tags"))
        catalog_tags.node.add_dependency(catalog)

        # Log group del job (con tag e scadenza): sotto /aws-glue/ basta il permesso della policy AWSGlueServiceRole
        job_logs = logs.LogGroup(self, "JobLogs", log_group_name=job_log_group,
                                 retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        job = glue.CfnJob(self, "Job", name=nome_risorsa(self, "job"), role=role.role_arn,
            command=glue.CfnJob.JobCommandProperty(name="glueetl", python_version="3", script_location=script.s3_object_url),
            glue_version="5.0", worker_type="G.1X", number_of_workers=2, timeout=15, max_retries=0,
            execution_property=glue.CfnJob.ExecutionPropertyProperty(max_concurrent_runs=1),
            connections=glue.CfnJob.ConnectionsListProperty(connections=[nome_risorsa(self, "rds")]),
            default_arguments={
                "--job-bookmark-option": "job-bookmark-enable",  # solo i file nuovi a ogni esecuzione
                "--TempDir": f"s3://{bucket.bucket_name}/temp/",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--continuous-log-logGroup": job_log_group,
                "--database_name": catalog_database,
                "--table_name": CATALOG_TABLE,
                "--rds_connection_name": nome_risorsa(self, "rds"),
                "--rds_database": RDS_DATABASE,
                "--rds_table_name": RDS_TABLE,
            })
        job.node.add_dependency(connection, job_logs)

        # Workflow: il trigger manuale avvia il crawler, quando finisce bene parte il job
        workflow = glue.CfnWorkflow(self, "Workflow", name=nome_risorsa(self, "workflow"), max_concurrent_runs=1,
                                    description="crawler dei CSV e caricamento in RDS")
        start_trigger = glue.CfnTrigger(self, "StartTrigger", name=nome_risorsa(self, "start"), type="ON_DEMAND",
            workflow_name=workflow.ref, actions=[glue.CfnTrigger.ActionProperty(crawler_name=crawler.ref)])
        job_trigger = glue.CfnTrigger(self, "JobTrigger", name=nome_risorsa(self, "job-after-crawler"), type="CONDITIONAL",
            start_on_creation=True, workflow_name=workflow.ref,
            actions=[glue.CfnTrigger.ActionProperty(job_name=job.ref)],
            predicate=glue.CfnTrigger.PredicateProperty(conditions=[glue.CfnTrigger.ConditionProperty(
                crawler_name=crawler.ref, crawl_state="SUCCEEDED", logical_operator="EQUALS")]))
        for trigger in (start_trigger, job_trigger):
            trigger.node.add_dependency(workflow)

        # Step Function: avvia il workflow e ne controlla lo stato ogni 30 secondi
        workflow_arn = f"arn:{self.partition}:glue:{self.region}:{self.account}:workflow/{nome_risorsa(self, 'workflow')}"
        start_run = tasks.CallAwsService(self, "StartWorkflowRun", service="glue", action="startWorkflowRun",
            parameters={"Name": workflow.ref}, iam_resources=[workflow_arn], result_path="$.run")
        # un solo workflow alla volta: se ne gira gia' uno, riprova dopo un minuto
        start_run.add_retry(errors=["Glue.ConcurrentRunsExceededException"], interval=Duration.seconds(60),
                            max_attempts=20, backoff_rate=1)
        wait = sfn.Wait(self, "Wait30Seconds", time=sfn.WaitTime.duration(Duration.seconds(30)))
        get_run = tasks.CallAwsService(self, "GetWorkflowRun", service="glue", action="getWorkflowRun",
            parameters={"Name": workflow.ref, "RunId": sfn.JsonPath.string_at("$.run.RunId")},
            iam_resources=[workflow_arn], result_path="$.status",
            result_selector={"Status.$": "$.Run.Status", "Statistics.$": "$.Run.Statistics"})
        failed = sfn.Fail(self, "WorkflowFailed", error="GlueWorkflowFailed", cause="Il workflow Glue non e' terminato bene")
        done = sfn.Succeed(self, "WorkflowCompleted")
        check = (sfn.Choice(self, "WorkflowFinished")
                 .when(sfn.Condition.or_(sfn.Condition.string_equals("$.status.Status", "RUNNING"),
                                         sfn.Condition.string_equals("$.status.Status", "STOPPING")), wait)
                 .when(sfn.Condition.and_(sfn.Condition.string_equals("$.status.Status", "COMPLETED"),
                                          sfn.Condition.number_greater_than("$.status.Statistics.FailedActions", 0)), failed)
                 .when(sfn.Condition.string_equals("$.status.Status", "COMPLETED"), done)
                 .otherwise(failed))
        sm_logs = logs.LogGroup(self, "StateMachineLogs", log_group_name=f"/aws/vendedlogs/states/{nome_risorsa(self, 'runner')}",
                                retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        state_machine = sfn.StateMachine(self, "StateMachine", state_machine_name=nome_risorsa(self, "runner"),
            definition_body=sfn.DefinitionBody.from_chainable(start_run.next(wait).next(get_run).next(check)),
            timeout=Duration.hours(1),
            logs=sfn.LogOptions(destination=sm_logs, level=sfn.LogLevel.ALL, include_execution_data=True))

        # Regola EventBridge: un .csv nuovo in INPUT/ avvia la Step Function
        events.Rule(self, "CsvUploadedRule", rule_name=nome_risorsa(self, "csv-uploaded"),
            event_pattern=events.EventPattern(source=["aws.s3"], detail_type=["Object Created"], detail={
                "bucket": {"name": [bucket.bucket_name]},
                "object": {"key": [{"wildcard": f"{INPUT_PREFIX}*.csv"}]},
            }),
            targets=[targets.SfnStateMachine(state_machine)])

        CfnOutput(self, "BucketName", value=bucket.bucket_name)
        CfnOutput(self, "UploadCommand", value=f"aws s3 cp data/persone.csv s3://{bucket.bucket_name}/{INPUT_PREFIX}persone.csv")
        CfnOutput(self, "StateMachineArn", value=state_machine.state_machine_arn)
        CfnOutput(self, "WorkflowName", value=workflow.ref)
        CfnOutput(self, "JobName", value=job.ref)
        CfnOutput(self, "CrawlerName", value=crawler.ref)
        CfnOutput(self, "DatabaseEndpoint", value=database.db_instance_endpoint_address)
        CfnOutput(self, "DatabaseSecretArn", value=database.secret.secret_arn)

"""Job AWS Glue (Spark) che legge un CSV da S3 e lo riscrive con le righe in ordine decrescente (tutte le colonne).

- bucket dello stack: il CSV di prova (data/persone.csv) viene caricato da CDK in INPUT/, il job scrive in OUTPUT/
- script del job (glue/invert_csv_data.py) caricato da CDK come asset nel bucket del bootstrap
- job Glue 5.0, 2 worker G.1X, timeout 10 minuti, nessun nuovo tentativo
- log del job in un log group dello stack (--continuous-log-logGroup) con 7 giorni, cancellato al destroy

La prima versione richiedeva un bucket esistente e il caricamento a mano dello script, e usava Glue 3.0.
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_glue as glue,
    aws_iam as iam,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

from .naming import nome_risorsa

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
INPUT_PREFIX = "INPUT/"
OUTPUT_PREFIX = "OUTPUT/"


class Cdk13GlueJobStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        job_name = nome_risorsa(self, "InvertCsv")

        self.bucket = s3.Bucket(self, "DataBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
            lifecycle_rules=[s3.LifecycleRule(prefix="temp/", expiration=Duration.days(7))],
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)

        # CSV di prova in INPUT/ (prune=False: il deploy non cancella gli altri file della cartella)
        s3deploy.BucketDeployment(self, "SampleData",
            sources=[s3deploy.Source.asset(os.path.join(ROOT, "data"))],
            destination_bucket=self.bucket, destination_key_prefix=INPUT_PREFIX, prune=False,
            log_group=logs.LogGroup(self, "SampleDataLogs", retention=logs.RetentionDays.ONE_WEEK,
                                    removal_policy=RemovalPolicy.DESTROY))

        script = s3_assets.Asset(self, "JobScript", path=os.path.join(ROOT, "glue", "invert_csv_data.py"))

        # Ruolo del job: servizio Glue (comprende i log /aws-glue/*), dati del bucket, script
        role = iam.Role(self, "GlueJobRole", assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole")])
        self.bucket.grant_read_write(role)
        script.grant_read(role)

        # Log group del job: con il nome sotto /aws-glue/ basta il permesso della policy AWSGlueServiceRole
        log_group = logs.LogGroup(self, "JobLogs", log_group_name=f"/aws-glue/jobs/{job_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)

        self.job = glue.CfnJob(self, "InvertCsvJob",
            name=job_name,
            role=role.role_arn,
            command=glue.CfnJob.JobCommandProperty(name="glueetl", python_version="3", script_location=script.s3_object_url),
            glue_version="5.0",
            worker_type="G.1X", number_of_workers=2,
            timeout=10, max_retries=0,
            execution_property=glue.CfnJob.ExecutionPropertyProperty(max_concurrent_runs=1),
            default_arguments={
                "--source_path": f"s3://{self.bucket.bucket_name}/{INPUT_PREFIX}persone.csv",
                "--destination_path": f"s3://{self.bucket.bucket_name}/{OUTPUT_PREFIX}",
                "--TempDir": f"s3://{self.bucket.bucket_name}/temp/",
                "--enable-metrics": "true",
                "--enable-continuous-cloudwatch-log": "true",
                "--continuous-log-logGroup": f"/aws-glue/jobs/{job_name}",
                "--enable-spark-ui": "true",
                "--spark-event-logs-path": f"s3://{self.bucket.bucket_name}/sparkui-logs/",
            })
        self.job.node.add_dependency(log_group)

        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "JobName", value=self.job.ref)
        CfnOutput(self, "StartCommand", value=f"aws glue start-job-run --job-name {job_name}")

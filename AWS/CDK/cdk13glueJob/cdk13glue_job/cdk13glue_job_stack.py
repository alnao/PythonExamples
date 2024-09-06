from aws_cdk import (
    Stack,
    aws_glue as glue,
    aws_iam as iam,
    aws_s3 as s3,
    CfnParameter,
)
from constructs import Construct

class Cdk13GlueJobStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        # Parametro per il nome del bucket
        bucket_name = CfnParameter(self, "BucketName", 
            type="String",
            description="Nome del bucket S3 esistente"
        )

        # Riferimento al bucket S3 esistente
        bucket = s3.Bucket.from_bucket_name(self, "DataBucket", bucket_name.value_as_string)

        # Crea un ruolo IAM per il job Glue
        glue_role = iam.Role(self, "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com")
        )

        # Aggiungi le policy necessarie al ruolo
        glue_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"))
        bucket.grant_read_write(glue_role)

        # Crea il job Glue
        glue_job = glue.CfnJob(self, "InvertDataGlueJob",
            name="InvertCSVDataJob",
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                python_version="3",
                script_location=f"s3://{bucket.bucket_name}/CODE/glue/invert_csv_data.py"
            ),
            default_arguments={
                "--enable-continuous-cloudwatch-log": "true",
                "--enable-spark-ui": "true",
                "--spark-event-logs-path": f"s3://{bucket.bucket_name}/sparkui-logs",
                "--enable-job-insights": "true",
                "--enable-glue-datacatalog": "true",
                "--source_path": f"s3://{bucket.bucket_name}/INPUT/prova.csv",
                "--destination_path": f"s3://{bucket.bucket_name}/OUTPUT/",
            },
            glue_version="3.0",
            max_retries=0,
            timeout=2880,
            number_of_workers=2,
            worker_type="G.1X"
        )
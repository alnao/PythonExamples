"""Applicazione AWS Elastic Beanstalk che esegue un'immagine Docker (piattaforma Docker su Amazon Linux 2023).

- source bundle: la cartella app/ con Dockerrun.aws.json (immagine e porta del container), caricata da CDK
  nel bucket del bootstrap come asset e registrata come versione dell'applicazione
- ambiente LoadBalanced con Application Load Balancer, da 1 a 2 istanze t3.micro nella VPC di default
- nginx sulle istanze inoltra la porta 80 alla porta del container; controllo di salute su HEALTH_PATH
- health reporting enhanced, log delle istanze in CloudWatch (7 giorni, cancellati con l'ambiente)

La piattaforma va indicata con il parametro solutionstack (nome esatto, cambia a ogni versione:
vedi il comando nel README).
"""

import json
import os

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Stack,
    aws_elasticbeanstalk as eb,
    aws_iam as iam,
    aws_s3_assets as s3_assets,
)
from constructs import Construct

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
HEALTH_PATH = "/api/echo/status"  # pagina di stato dell'immagine pathsgames/pathsgames
INSTANCE_TYPES = ["t3.micro", "t3.small", "t3.medium"]


def container_port() -> int:
    """Porta del container, letta da app/Dockerrun.aws.json (una sola fonte per immagine e porta)."""
    with open(os.path.join(APP_DIR, "Dockerrun.aws.json")) as f:
        return int(json.load(f)["Ports"][0]["ContainerPort"])


class Cdk31ElasticBeanstalkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name

        solution_stack = CfnParameter(self, "solutionstack", type="String",
            description="piattaforma, es. '64bit Amazon Linux 2023 v4.x.y running Docker' (vedi README)").value_as_string
        instance_type = CfnParameter(self, "instancetype", type="String", default="t3.micro",
                                     allowed_values=INSTANCE_TYPES, description="tipo delle istanze").value_as_string

        # Ruolo delle istanze (web tier, Docker, Session Manager) e ruolo di servizio di Elastic Beanstalk
        instance_role = iam.Role(self, "InstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(name) for name in (
                "AWSElasticBeanstalkWebTier", "AWSElasticBeanstalkMulticontainerDocker", "AmazonSSMManagedInstanceCore")])
        instance_profile = iam.InstanceProfile(self, "InstanceProfile", role=instance_role)
        service_role = iam.Role(self, "ServiceRole", assumed_by=iam.ServicePrincipal("elasticbeanstalk.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(name) for name in (
                "service-role/AWSElasticBeanstalkEnhancedHealth",
                "AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy")])

        application = eb.CfnApplication(self, "Application", application_name=f"{prefix}-app",
            description="Esempio cdk31: un container Docker su Elastic Beanstalk",
            # al massimo 10 versioni registrate; i bundle restano nel bucket del bootstrap (condiviso)
            resource_lifecycle_config=eb.CfnApplication.ApplicationResourceLifecycleConfigProperty(
                service_role=service_role.role_arn,
                version_lifecycle_config=eb.CfnApplication.ApplicationVersionLifecycleConfigProperty(
                    max_count_rule=eb.CfnApplication.MaxCountRuleProperty(enabled=True, max_count=10,
                                                                          delete_source_from_s3=False))))

        bundle = s3_assets.Asset(self, "SourceBundle", path=APP_DIR)  # zip della cartella app/
        version = eb.CfnApplicationVersion(self, "ApplicationVersion", application_name=application.ref,
            description="Dockerrun.aws.json della cartella app/",
            source_bundle=eb.CfnApplicationVersion.SourceBundleProperty(
                s3_bucket=bundle.s3_bucket_name, s3_key=bundle.s3_object_key))

        def option(namespace: str, name: str, value: str):
            return eb.CfnEnvironment.OptionSettingProperty(namespace=namespace, option_name=name, value=value)

        environment = eb.CfnEnvironment(self, "Environment", application_name=application.ref,
            environment_name=f"{prefix}-env", solution_stack_name=solution_stack, version_label=version.ref,
            option_settings=[
                option("aws:elasticbeanstalk:environment", "EnvironmentType", "LoadBalanced"),
                option("aws:elasticbeanstalk:environment", "LoadBalancerType", "application"),
                option("aws:elasticbeanstalk:environment", "ServiceRole", service_role.role_arn),
                option("aws:autoscaling:launchconfiguration", "IamInstanceProfile", instance_profile.instance_profile_name),
                option("aws:autoscaling:launchconfiguration", "DisableIMDSv1", "true"),
                option("aws:autoscaling:launchconfiguration", "RootVolumeType", "gp3"),
                option("aws:ec2:instances", "InstanceTypes", instance_type),
                option("aws:autoscaling:asg", "MinSize", "1"),
                option("aws:autoscaling:asg", "MaxSize", "2"),
                # il load balancer parla con nginx sulla porta 80, nginx con il container (porta in Dockerrun.aws.json)
                option("aws:elasticbeanstalk:environment:process:default", "Port", "80"),
                option("aws:elasticbeanstalk:environment:process:default", "HealthCheckPath", HEALTH_PATH),
                option("aws:elasticbeanstalk:environment:process:default", "MatcherHTTPCode", "200"),
                option("aws:elasticbeanstalk:environment:proxy", "ProxyServer", "nginx"),
                option("aws:elasticbeanstalk:healthreporting:system", "SystemType", "enhanced"),
                option("aws:elasticbeanstalk:managedactions", "ManagedActionsEnabled", "false"),
                option("aws:elasticbeanstalk:cloudwatch:logs", "StreamLogs", "true"),
                option("aws:elasticbeanstalk:cloudwatch:logs", "RetentionInDays", "7"),
                option("aws:elasticbeanstalk:cloudwatch:logs", "DeleteOnTerminate", "true"),
            ])

        CfnOutput(self, "ApplicationName", value=application.ref)
        CfnOutput(self, "EnvironmentName", value=environment.ref)
        CfnOutput(self, "EnvironmentURL", value=f"http://{environment.attr_endpoint_url}{HEALTH_PATH}")
        CfnOutput(self, "ContainerPort", value=str(container_port()))

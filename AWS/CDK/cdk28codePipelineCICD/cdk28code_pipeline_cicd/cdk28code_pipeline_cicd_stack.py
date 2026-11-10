"""Pipeline CI/CD con CodePipeline: dal repository GitHub fino a ECS Fargate e a un sito su CloudFront.

A ogni commit sul branch la pipeline:
1. Source: scarica il repository GitHub (alnao/PythonExamples per default)
2. Build: CodeBuild costruisce l'immagine Docker del backend (Docker/03ApiPersoneNoDb) e la carica su ECR;
   un secondo progetto CodeBuild prende i file del frontend (cartella frontend di questo esempio)
3. Deploy: aggiorna il servizio ECS Fargate con la nuova immagine e copia il frontend nel bucket del sito

Infrastruttura:
- VPC con sole subnet pubbliche (nessun NAT): i task Fargate hanno un IP pubblico per scaricare l'immagine
- servizio Fargate dietro un Application Load Balancer; al primo deploy l'immagine e' costruita da CDK,
  poi la sostituisce la pipeline
- CloudFront davanti a tutto: / dal bucket S3 privato, /persone e /test dal load balancer (stesso dominio, niente CORS)

Sorgente GitHub: token personale in Secrets Manager (secret github/codepipeline/token, come nell'esempio
CloudFormation) oppure, con -c connection_arn=..., una connessione AWS CodeConnections.
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    SecretValue,
    Stack,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
    aws_s3 as s3,
)
from constructs import Construct

# progetto Docker/03ApiPersoneNoDb del repository PythonExamples (prima immagine, prima della pipeline)
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Docker", "03ApiPersoneNoDb")
CONTAINER_NAME = "backend"
CONTAINER_PORT = 5001

DEFAULTS = {
    "github_owner": "alnao",
    "github_repo": "PythonExamples",
    "github_branch": "master",
    "github_token_secret": "github/codepipeline/token",
    "backend_dir": "Docker/03ApiPersoneNoDb",
    "frontend_dir": "AWS/CDK/cdk28codePipelineCICD/frontend",
}

BACKEND_BUILDSPEC = {
    "version": "0.2",
    "phases": {
        "pre_build": {"commands": [
            "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin ${REPOSITORY_URI%%/*}",
            "IMAGE_TAG=${CODEBUILD_RESOLVED_SOURCE_VERSION:0:8}",
            # immagine base dalla galleria pubblica di ECR: Docker Hub limita i download anonimi da CodeBuild
            "docker pull public.ecr.aws/docker/library/python:3.8 && docker tag public.ecr.aws/docker/library/python:3.8 python:3.8",
        ]},
        "build": {"commands": [
            "cd $BACKEND_DIR",
            "docker build -t $REPOSITORY_URI:$IMAGE_TAG -t $REPOSITORY_URI:latest .",
        ]},
        "post_build": {"commands": [
            "docker push $REPOSITORY_URI:$IMAGE_TAG",
            "docker push $REPOSITORY_URI:latest",
            # file letto dall'azione di deploy ECS: nome del container e nuova immagine
            'printf \'[{"name":"%s","imageUri":"%s"}]\' $CONTAINER_NAME $REPOSITORY_URI:$IMAGE_TAG > $CODEBUILD_SRC_DIR/imagedefinitions.json',
        ]},
    },
    "artifacts": {"files": ["imagedefinitions.json"]},
}

FRONTEND_BUILDSPEC = {
    "version": "0.2",
    "phases": {"build": {"commands": ["ls -la $FRONTEND_DIR"]}},  # file statici: niente da compilare
    "artifacts": {"base-directory": "$FRONTEND_DIR", "files": ["**/*"]},
}


class Cdk28CodePipelineCicdStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prefix = self.stack_name
        cfg = {k: self.node.try_get_context(k) or v for k, v in DEFAULTS.items()}

        # ---- infrastruttura del backend ----
        vpc = ec2.Vpc(self, "Vpc", ip_addresses=ec2.IpAddresses.cidr("10.186.0.0/16"), max_azs=2, nat_gateways=0,
                      subnet_configuration=[ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC,
                                                                    cidr_mask=24)])
        repository = ecr.Repository(self, "BackendRepository", image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY, empty_on_delete=True,
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10, description="al massimo 10 immagini")])

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, cluster_name=prefix)
        log_group = logs.LogGroup(self, "BackendLogs", log_group_name=f"/ecs/{prefix}-backend",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        task_definition = ecs.FargateTaskDefinition(self, "BackendTask", family=f"{prefix}-backend",
                                                    cpu=256, memory_limit_mib=512,
                                                    runtime_platform=ecs.RuntimePlatform(
                                                        cpu_architecture=ecs.CpuArchitecture.X86_64,
                                                        operating_system_family=ecs.OperatingSystemFamily.LINUX))
        task_definition.add_container(CONTAINER_NAME,
            image=ecs.ContainerImage.from_asset(APP_DIR, platform=ecr_assets.Platform.LINUX_AMD64),
            port_mappings=[ecs.PortMapping(container_port=CONTAINER_PORT)],
            logging=ecs.LogDriver.aws_logs(stream_prefix="backend", log_group=log_group))
        repository.grant_pull(task_definition.obtain_execution_role())  # le immagini della pipeline

        service = ecs.FargateService(self, "BackendService", cluster=cluster, task_definition=task_definition,
            service_name="backend", desired_count=1, assign_public_ip=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100, max_healthy_percent=200, propagate_tags=ecs.PropagatedTagSource.SERVICE)

        alb = elbv2.ApplicationLoadBalancer(self, "LoadBalancer", vpc=vpc, internet_facing=True)
        listener = alb.add_listener("HttpListener", port=80, open=True)
        listener.add_targets("Backend", port=CONTAINER_PORT, protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service], deregistration_delay=Duration.seconds(30),
            health_check=elbv2.HealthCheck(path="/test", interval=Duration.seconds(30), healthy_threshold_count=2,
                                           unhealthy_threshold_count=2))

        # ---- sito: bucket privato + CloudFront, le API passano dallo stesso dominio ----
        site = s3.Bucket(self, "FrontendBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                         removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        api_origin = origins.HttpOrigin(alb.load_balancer_dns_name, protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY)
        api_behavior = cloudfront.BehaviorOptions(origin=api_origin,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER)
        distribution = cloudfront.Distribution(self, "Distribution", comment=f"{prefix} frontend e backend",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS),
            additional_behaviors={"/persone*": api_behavior, "/test": api_behavior})

        # ---- pipeline ----
        source_output = codepipeline.Artifact("SourceCode")
        connection_arn = self.node.try_get_context("connection_arn")
        if connection_arn:
            source = actions.CodeStarConnectionsSourceAction(action_name="GitHub", connection_arn=connection_arn,
                owner=cfg["github_owner"], repo=cfg["github_repo"], branch=cfg["github_branch"], output=source_output)
        else:
            source = actions.GitHubSourceAction(action_name="GitHub", output=source_output,
                owner=cfg["github_owner"], repo=cfg["github_repo"], branch=cfg["github_branch"],
                oauth_token=SecretValue.secrets_manager(cfg["github_token_secret"]),
                trigger=actions.GitHubTrigger.POLL)

        def build_project(name: str, spec: dict, env: dict, privileged: bool = False) -> codebuild.PipelineProject:
            logs_group = logs.LogGroup(self, f"{name}BuildLogs", log_group_name=f"/aws/codebuild/{prefix}-{name}",
                                       retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
            return codebuild.PipelineProject(self, f"{name}Build", project_name=f"{prefix}-{name}",
                build_spec=codebuild.BuildSpec.from_object(spec),
                environment=codebuild.BuildEnvironment(build_image=codebuild.LinuxBuildImage.STANDARD_7_0,
                                                       compute_type=codebuild.ComputeType.SMALL, privileged=privileged),
                environment_variables={k: codebuild.BuildEnvironmentVariable(value=v) for k, v in env.items()},
                logging=codebuild.LoggingOptions(cloud_watch=codebuild.CloudWatchLoggingOptions(log_group=logs_group)),
                timeout=Duration.minutes(20))

        backend_build = build_project("backend", BACKEND_BUILDSPEC, {
            "REPOSITORY_URI": repository.repository_uri, "BACKEND_DIR": cfg["backend_dir"],
            "CONTAINER_NAME": CONTAINER_NAME}, privileged=True)  # privileged: docker dentro CodeBuild
        repository.grant_pull_push(backend_build)
        frontend_build = build_project("frontend", FRONTEND_BUILDSPEC, {"FRONTEND_DIR": cfg["frontend_dir"]})

        backend_output = codepipeline.Artifact("BackendBuildOutput")
        frontend_output = codepipeline.Artifact("FrontendBuildOutput")
        artifacts = s3.Bucket(self, "ArtifactBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                              enforce_ssl=True, removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True,
                              lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(30))])
        pipeline = codepipeline.Pipeline(self, "Pipeline", pipeline_name=f"{prefix}-pipeline",
            pipeline_type=codepipeline.PipelineType.V2, artifact_bucket=artifacts, restart_execution_on_update=True,
            stages=[
                codepipeline.StageProps(stage_name="Source", actions=[source]),
                codepipeline.StageProps(stage_name="Build", actions=[
                    actions.CodeBuildAction(action_name="Backend", project=backend_build, input=source_output,
                                            outputs=[backend_output]),
                    actions.CodeBuildAction(action_name="Frontend", project=frontend_build, input=source_output,
                                            outputs=[frontend_output]),
                ]),
                codepipeline.StageProps(stage_name="Deploy", actions=[
                    actions.EcsDeployAction(action_name="Backend", service=service,
                                            image_file=backend_output.at_path("imagedefinitions.json"),
                                            deployment_timeout=Duration.minutes(20)),
                    actions.S3DeployAction(action_name="Frontend", bucket=site, input=frontend_output, extract=True,
                                           cache_control=[actions.CacheControl.no_cache()]),
                ]),
            ])

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "BackendUrl", value=f"http://{alb.load_balancer_dns_name}/persone")
        CfnOutput(self, "RepositoryUri", value=repository.repository_uri)
        CfnOutput(self, "PipelineUrl", value=f"https://{self.region}.console.aws.amazon.com/codesuite/codepipeline/"
                                             f"pipelines/{pipeline.pipeline_name}/view?region={self.region}")

"""Cluster ECS su istanze EC2 con un servizio dietro un Application Load Balancer.

- VPC nuova con due subnet pubbliche (load balancer, NAT) e due private (istanze del cluster)
- istanze ECS-optimized Amazon Linux 2023 in un Auto Scaling group, collegato al cluster
  come capacity provider (ECS aggiunge e toglie istanze secondo i task da eseguire)
- servizio con 2 task dell'API Flask di Docker/03ApiPersoneNoDb (porta 5001, rete bridge con porte dinamiche)
- il load balancer manda /persone e /test al servizio, il resto riceve un 404 fisso

L'immagine e' costruita da CDK al deploy (repository ECR del bootstrap); con -c ecr_repository=<nome>
il servizio usa invece l'immagine :latest di un repository esistente, per esempio quello del cdk23ecr.
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct

# progetto Docker/03ApiPersoneNoDb del repository PythonExamples
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "Docker", "03ApiPersoneNoDb")
CONTAINER_NAME = "api-persone"
CONTAINER_PORT = 5001
DESIRED_TASKS = 2


class Cdk24EcsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC: subnet pubbliche per load balancer e NAT, private per le istanze (un solo NAT per risparmiare)
        vpc = ec2.Vpc(self, "Vpc", ip_addresses=ec2.IpAddresses.cidr("10.184.0.0/16"), max_azs=2, nat_gateways=1,
                      subnet_configuration=[
                          ec2.SubnetConfiguration(name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
                          ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=24),
                      ])

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, cluster_name=self.stack_name)

        # Istanze del cluster: l'agente ECS gira sull'AMI ECS-optimized, Session Manager al posto di SSH
        role = iam.Role(self, "EcsInstanceRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
                        managed_policies=[
                            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"),
                            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                        ])
        launch_template = ec2.LaunchTemplate(self, "EcsLaunchTemplate",
            instance_type=ec2.InstanceType("t3.micro"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2023(),
            user_data=ec2.UserData.for_linux(),  # CDK aggiunge ECS_CLUSTER=<cluster> in /etc/ecs/ecs.config
            role=role,
            security_group=ec2.SecurityGroup(self, "EcsHostSecurityGroup", vpc=vpc, description="Istanze del cluster ECS"),
            require_imdsv2=True,
            http_put_response_hop_limit=2,  # i container in rete bridge raggiungono i metadati dell'istanza
        )
        asg = autoscaling.AutoScalingGroup(self, "EcsHosts", vpc=vpc, launch_template=launch_template,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            min_capacity=1, max_capacity=2)
        capacity_provider = ecs.AsgCapacityProvider(self, "CapacityProvider", auto_scaling_group=asg,
            enable_managed_scaling=True, target_capacity_percent=100, enable_managed_draining=True,
            # senza protezione dallo scale-in il destroy non resta bloccato sulle istanze protette
            enable_managed_termination_protection=False)
        cluster.add_asg_capacity_provider(capacity_provider)

        # Immagine: costruita da CDK (default) oppure presa da un repository ECR esistente
        repo_name = self.node.try_get_context("ecr_repository")
        if repo_name:
            image = ecs.ContainerImage.from_ecr_repository(
                ecr.Repository.from_repository_name(self, "ImageRepository", repo_name), tag="latest")
        else:
            image = ecs.ContainerImage.from_asset(APP_DIR, platform=ecr_assets.Platform.LINUX_AMD64)

        log_group = logs.LogGroup(self, "LogGroup", log_group_name=f"/ecs/{self.stack_name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        task_definition = ecs.Ec2TaskDefinition(self, "TaskDefinition", family=f"{self.stack_name}-api-persone",
                                                network_mode=ecs.NetworkMode.BRIDGE)
        task_definition.add_container(CONTAINER_NAME, image=image, cpu=256, memory_reservation_mib=256,
            port_mappings=[ecs.PortMapping(container_port=CONTAINER_PORT, host_port=0)],  # porta dell'host scelta da ECS
            logging=ecs.LogDriver.aws_logs(stream_prefix="api", log_group=log_group))

        service = ecs.Ec2Service(self, "Service", cluster=cluster, task_definition=task_definition,
            service_name="api-persone", desired_count=DESIRED_TASKS,
            capacity_provider_strategies=[ecs.CapacityProviderStrategy(
                capacity_provider=capacity_provider.capacity_provider_name, weight=1)],
            placement_strategies=[ecs.PlacementStrategy.spread_across(ecs.BuiltInAttributes.AVAILABILITY_ZONE),
                                  ecs.PlacementStrategy.packed_by_memory()],
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=50, propagate_tags=ecs.PropagatedTagSource.SERVICE)

        # Load balancer pubblico: /persone e /test al servizio, il resto 404
        alb = elbv2.ApplicationLoadBalancer(self, "LoadBalancer", vpc=vpc, internet_facing=True)
        listener = alb.add_listener("HttpListener", port=80, open=True,
            default_action=elbv2.ListenerAction.fixed_response(404, content_type="text/plain",
                message_body="Esempio cdk24ecs: usare /persone"))
        listener.add_targets("ApiPersone", port=80, priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/persone", "/persone/*", "/test"])],
            targets=[service.load_balancer_target(container_name=CONTAINER_NAME, container_port=CONTAINER_PORT)],
            health_check=elbv2.HealthCheck(path="/test", interval=Duration.seconds(15), healthy_threshold_count=2),
            deregistration_delay=Duration.seconds(30))

        CfnOutput(self, "ServiceUrl", value=f"http://{alb.load_balancer_dns_name}/persone")
        CfnOutput(self, "ClusterName", value=cluster.cluster_name)
        CfnOutput(self, "ServiceName", value=service.service_name)
        CfnOutput(self, "LogGroupName", value=log_group.log_group_name)

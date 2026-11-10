"""Cluster Amazon EKS con un node group gestito e un database RDS MySQL, nella VPC di default.

Come il template CloudFormation l'esempio usa le risorse L1 (CfnCluster, CfnNodegroup): il costrutto L2
eks.Cluster di CDK creerebbe anche una Lambda con kubectl e diversi custom resource, qui non servono
perche' l'applicazione si installa con kubectl dal proprio PC (k8s/springboot-k8s.yaml).

- cluster con API pubblica e privata, log del control plane (api, audit) in un log group con 7 giorni
- accesso con le access entry di EKS: amministratore il principal IAM passato come parametro
- node group gestito Amazon Linux 2023, launch template con disco gp3 e IMDSv2 (e i tag su istanze e volumi)
- add-on metrics-server per l'HorizontalPodAutoscaler del manifest
- RDS MySQL raggiungibile solo dai nodi del cluster, password gestita da RDS in Secrets Manager
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Fn,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_iam as iam,
    aws_logs as logs,
    aws_rds as rds,
)
from constructs import Construct


INSTANCE_TYPES = ["t3.small", "t3.medium", "t3.large", "m5.large", "m5.xlarge"]


class Cdk27EksStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_id = CfnParameter(self, "vpcid", type="AWS::EC2::VPC::Id", description="VPC (quella di default va bene)").value_as_string
        subnet_ids = CfnParameter(self, "subnetids", type="List<AWS::EC2::Subnet::Id>",
                                  description="almeno due subnet della VPC in zone diverse").value_as_list
        admin_arn = CfnParameter(self, "adminprincipalarn", type="String", allowed_pattern="arn:aws:iam::[0-9]{12}:(user|role)/.+",
                                 description="utente o ruolo IAM amministratore del cluster (per kubectl)").value_as_string
        cluster_name = CfnParameter(self, "clustername", type="String", default="cdk27eks-cluster",
                                    description="nome del cluster EKS").value_as_string
        k8s_version = CfnParameter(self, "kubernetesversion", type="String", default="1.35",
                                   description="versione di Kubernetes (verificare quelle in supporto standard)").value_as_string
        node_type = CfnParameter(self, "nodeinstancetype", type="String", default="t3.small",
                                 allowed_values=INSTANCE_TYPES, description="tipo delle istanze dei nodi").value_as_string

        # Log group del control plane: il nome e' fisso (lo decide EKS), creato prima del cluster per avere tag e scadenza
        log_group = logs.LogGroup(self, "ClusterLogGroup", log_group_name=Fn.sub("/aws/eks/${Name}/cluster", {"Name": cluster_name}),
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)

        cluster_role = iam.Role(self, "ClusterRole", assumed_by=iam.ServicePrincipal("eks.amazonaws.com"),
                                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKSClusterPolicy")])
        cluster = eks.CfnCluster(self, "Cluster",
            name=cluster_name, version=k8s_version, role_arn=cluster_role.role_arn,
            resources_vpc_config=eks.CfnCluster.ResourcesVpcConfigProperty(
                subnet_ids=subnet_ids, endpoint_public_access=True, endpoint_private_access=True),
            logging=eks.CfnCluster.LoggingProperty(cluster_logging=eks.CfnCluster.ClusterLoggingProperty(
                enabled_types=[eks.CfnCluster.LoggingTypeConfigProperty(type="api"),
                               eks.CfnCluster.LoggingTypeConfigProperty(type="audit")])),
            # accesso con le access entry (API di EKS) oltre alla vecchia ConfigMap aws-auth
            access_config=eks.CfnCluster.AccessConfigProperty(authentication_mode="API_AND_CONFIG_MAP",
                                                              bootstrap_cluster_creator_admin_permissions=True),
            # supporto standard: una versione in supporto esteso costerebbe 6 volte tanto (0,60 $/ora)
            upgrade_policy=eks.CfnCluster.UpgradePolicyProperty(support_type="STANDARD"),
        )
        cluster.node.add_dependency(log_group)

        # chi crea il cluster e' il ruolo di CloudFormation del bootstrap: l'amministratore per kubectl va aggiunto
        eks.CfnAccessEntry(self, "AdminAccess", cluster_name=cluster.ref, principal_arn=admin_arn,
            access_policies=[eks.CfnAccessEntry.AccessPolicyProperty(
                policy_arn="arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy",
                access_scope=eks.CfnAccessEntry.AccessScopeProperty(type="cluster"))])

        node_role = iam.Role(self, "NodeRole", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(name) for name in (
                "AmazonEKSWorkerNodePolicy", "AmazonEKS_CNI_Policy", "AmazonEC2ContainerRegistryReadOnly",
                "AmazonSSMManagedInstanceCore")])

        # Launch template dei nodi: EKS non propaga i tag del node group a istanze e volumi
        launch_template = ec2.LaunchTemplate(self, "NodeLaunchTemplate",
            block_devices=[ec2.BlockDevice(device_name="/dev/xvda", volume=ec2.BlockDeviceVolume.ebs(
                20, volume_type=ec2.EbsDeviceVolumeType.GP3, encrypted=True, delete_on_termination=True))],
            http_tokens=ec2.LaunchTemplateHttpTokens.REQUIRED,
            http_put_response_hop_limit=2)  # i pod raggiungono i metadati dell'istanza
        nodegroup = eks.CfnNodegroup(self, "Nodegroup",
            cluster_name=cluster.ref, nodegroup_name=Fn.sub("${Name}-nodes", {"Name": cluster_name}),
            node_role=node_role.role_arn, subnets=subnet_ids,
            scaling_config=eks.CfnNodegroup.ScalingConfigProperty(min_size=1, desired_size=1, max_size=2),
            instance_types=[node_type], ami_type="AL2023_x86_64_STANDARD", capacity_type="ON_DEMAND",
            launch_template=eks.CfnNodegroup.LaunchTemplateSpecificationProperty(
                id=launch_template.launch_template_id, version=launch_template.latest_version_number),
            labels={"Application": "springboot"})

        # metrics-server: serve all'HorizontalPodAutoscaler; l'add-on diventa attivo solo quando ci sono i nodi
        addon = eks.CfnAddon(self, "MetricsServer", addon_name="metrics-server", cluster_name=cluster.ref,
                             resolve_conflicts="OVERWRITE")
        addon.node.add_dependency(nodegroup)

        # Database MySQL nelle stesse subnet, raggiungibile dal security group del cluster (lo usano anche i nodi)
        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=[Fn.select(0, Fn.get_azs())])
        db_sg = ec2.SecurityGroup(self, "DatabaseSecurityGroup", vpc=vpc, allow_all_outbound=False,
                                  description="RDS MySQL: accesso dai nodi EKS")
        db_sg.add_ingress_rule(ec2.Peer.security_group_id(cluster.attr_cluster_security_group_id), ec2.Port.tcp(3306),
                               "MySQL dai nodi EKS")
        subnet_group = rds.CfnDBSubnetGroup(self, "DatabaseSubnetGroup", subnet_ids=subnet_ids,
                                            db_subnet_group_description="Subnet del database cdk27")
        database = rds.CfnDBInstance(self, "Database",
            db_instance_identifier=Fn.sub("${Name}-mysql", {"Name": cluster_name}),
            db_instance_class="db.t4g.micro", engine="mysql", engine_version="8.4.8",
            master_username="root", manage_master_user_password=True,  # password generata e ruotata da RDS
            allocated_storage="20", storage_type="gp3", storage_encrypted=True,
            db_subnet_group_name=subnet_group.ref, vpc_security_groups=[db_sg.security_group_id],
            multi_az=False, publicly_accessible=False, deletion_protection=False,
            backup_retention_period=1, delete_automated_backups=True, copy_tags_to_snapshot=True)
        # esempio: al destroy il database si cancella senza snapshot finale (il default di RDS sarebbe Snapshot)
        database.apply_removal_policy(RemovalPolicy.DESTROY)

        CfnOutput(self, "ClusterName", value=cluster.ref)
        CfnOutput(self, "ClusterEndpoint", value=cluster.attr_endpoint)
        CfnOutput(self, "ClusterSecurityGroupId", value=cluster.attr_cluster_security_group_id)
        CfnOutput(self, "KubectlCommand", value=f"aws eks update-kubeconfig --region {self.region} --name {cluster.ref}")
        CfnOutput(self, "MySQLEndpoint", value=database.attr_endpoint_address)
        CfnOutput(self, "MySQLSecretArn", value=database.attr_master_user_secret_secret_arn)

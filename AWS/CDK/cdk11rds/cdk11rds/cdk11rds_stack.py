"""Database relazionale su Amazon RDS, con un cluster Aurora Serverless v2 facoltativo.

- istanza RDS (MySQL per default, oppure MariaDB o PostgreSQL con -c engine=...) db.t4g.micro, disco gp3 cifrato
- utente e password generati in Secrets Manager (nessuna password nei parametri)
- VPC e subnet per default quelle di default della region (vedi network.py), modificabili con i parametri
- security group con la porta del database aperta solo verso il CIDR indicato (per default quello della VPC)
- con -c aurora=true anche un cluster Aurora MySQL Serverless v2 che va in pausa dopo 5 minuti senza
  connessioni (0 ACU, si paga solo lo storage) e con la Data API, per fare query con la CLI senza rete
- al destroy i database si cancellano senza snapshot finale e senza backup automatici
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_rds as rds,
)
from constructs import Construct

from .network import lookup_subnets, lookup_vpc, subnet_parameter, vpc_parameter

ENGINES = {
    # nome -> (motore, porta)
    "mysql": (rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_4_8), 3306),
    "mariadb": (rds.DatabaseInstanceEngine.maria_db(version=rds.MariaDbEngineVersion.VER_11_8_3), 3306),
    "postgres": (rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_17_7), 5432),
}
# caratteri esclusi dalla password generata: danno fastidio negli URL di connessione e nella shell
EXCLUDE = " %+~`#$&*()|[]{}:;<>?!'/@\"\\"


class Cdk11RdsStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        engine_name = self.node.try_get_context("engine") or "mysql"
        if engine_name not in ENGINES:
            raise ValueError(f"engine deve essere uno di {sorted(ENGINES)}")
        engine, port = ENGINES[engine_name]
        with_aurora = str(self.node.try_get_context("aurora") or "false").lower() == "true"

        # VPC e subnet: per default quelle di default della region (vedi network.py)
        default_vpc = lookup_vpc(self)
        default_subnets = lookup_subnets(default_vpc, 2)
        vpc_id = vpc_parameter(self, default_vpc)
        subnet_1 = subnet_parameter(self, "subnetid1", default_subnets[0], "subnet 1 del database")
        subnet_2 = subnet_parameter(self, "subnetid2", default_subnets[1], "subnet 2 del database, in un'altra zona")
        allowed_cidr = CfnParameter(self, "allowedcidr", type="String", default=default_vpc.vpc_cidr_block,
                                    allowed_pattern=r"(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})/(\d{1,2})",
                                    description="rete da cui si puo' raggiungere il database (default: CIDR della VPC)").value_as_string
        db_name = CfnParameter(self, "dbname", type="String", default="cdk11rds", allowed_pattern="[a-zA-Z][a-zA-Z0-9]*",
                               description="nome del database").value_as_string

        azs = [Fn.select(0, Fn.get_azs()), Fn.select(1, Fn.get_azs())]
        vpc = ec2.Vpc.from_vpc_attributes(self, "Vpc", vpc_id=vpc_id, availability_zones=azs,
                                          private_subnet_ids=[subnet_1, subnet_2])
        subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)

        security_group = ec2.SecurityGroup(self, "DatabaseSecurityGroup", vpc=vpc, allow_all_outbound=False,
                                           description=f"Database cdk11: porta {port} dalla rete indicata")
        security_group.add_ingress_rule(ec2.Peer.ipv4(allowed_cidr), ec2.Port.tcp(port), "accesso al database")

        self.instance = rds.DatabaseInstance(self, "Database",
            engine=engine, instance_type=ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO),
            vpc=vpc, vpc_subnets=subnets, security_groups=[security_group],
            database_name=db_name,
            credentials=rds.Credentials.from_generated_secret("alnao", exclude_characters=EXCLUDE),
            allocated_storage=20, storage_type=rds.StorageType.GP3, storage_encrypted=True,
            multi_az=False, publicly_accessible=False,
            backup_retention=Duration.days(1), delete_automated_backups=True,
            removal_policy=RemovalPolicy.DESTROY, deletion_protection=False)

        CfnOutput(self, "Engine", value=engine_name)
        CfnOutput(self, "DatabaseEndpoint", value=self.instance.db_instance_endpoint_address)
        CfnOutput(self, "DatabasePort", value=self.instance.db_instance_endpoint_port)
        CfnOutput(self, "DatabaseSecretArn", value=self.instance.secret.secret_arn)

        if with_aurora:
            self.cluster = rds.DatabaseCluster(self, "AuroraCluster",
                engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_09_0),
                writer=rds.ClusterInstance.serverless_v2("writer"),
                # 0 ACU: dopo 5 minuti senza connessioni il cluster va in pausa e si paga solo lo storage
                serverless_v2_min_capacity=0, serverless_v2_max_capacity=2,
                serverless_v2_auto_pause_duration=Duration.minutes(5),
                vpc=vpc, vpc_subnets=subnets, security_groups=[security_group],
                default_database_name=db_name,
                credentials=rds.Credentials.from_generated_secret("alnao", exclude_characters=EXCLUDE),
                enable_data_api=True,  # query via HTTPS con la CLI (aws rds-data), senza aprire la rete
                storage_encrypted=True, backup=rds.BackupProps(retention=Duration.days(1)),
                removal_policy=RemovalPolicy.DESTROY, deletion_protection=False)
            CfnOutput(self, "AuroraClusterArn", value=self.cluster.cluster_arn)
            CfnOutput(self, "AuroraEndpoint", value=self.cluster.cluster_endpoint.hostname)
            CfnOutput(self, "AuroraReaderEndpoint", value=self.cluster.cluster_read_endpoint.hostname)
            CfnOutput(self, "AuroraSecretArn", value=self.cluster.secret.secret_arn)

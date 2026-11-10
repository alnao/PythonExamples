"""Repository Amazon ECR per le immagini Docker degli esempi.

- scansione delle vulnerabilita' a ogni push
- regole di ciclo di vita: le immagini senza tag spariscono dopo 1 giorno, si tengono le ultime 10
- al destroy il repository si svuota e si cancella (EmptyOnDelete)

L'immagine di prova e' quella del progetto Docker/03ApiPersoneNoDb del repository, usata anche dal cdk24ecs.
"""

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ecr as ecr,
)
from constructs import Construct


class Cdk23EcrStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repo_name = CfnParameter(self, "reponame", type="String", default="cdk23ecr-repository",
                                 allowed_pattern="[a-z0-9]+(?:[._-][a-z0-9]+)*",
                                 description="nome del repository ECR (minuscole, numeri, . _ -)").value_as_string

        self.repository = ecr.Repository(self, "Repository",
            repository_name=repo_name,
            image_scan_on_push=True,
            image_tag_mutability=ecr.TagMutability.MUTABLE,  # il tag latest viene sovrascritto a ogni push
            encryption=ecr.RepositoryEncryption.AES_256,  # default di ECR: CDK non lo scrive nel template
            # esempio: al destroy si cancellano anche le immagini
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            lifecycle_rules=[
                ecr.LifecycleRule(rule_priority=1, description="immagini senza tag dopo 1 giorno",
                                  tag_status=ecr.TagStatus.UNTAGGED, max_image_age=Duration.days(1)),
                ecr.LifecycleRule(rule_priority=2, description="al massimo 10 immagini",
                                  tag_status=ecr.TagStatus.ANY, max_image_count=10),
            ],
        )

        registry = f"{self.account}.dkr.ecr.{self.region}.amazonaws.com"
        uri = self.repository.repository_uri
        CfnOutput(self, "RepositoryName", value=self.repository.repository_name)
        CfnOutput(self, "RepositoryUri", value=uri)
        CfnOutput(self, "LoginCommand", description="login di docker al registry ECR",
                  value=f"aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {registry}")
        CfnOutput(self, "PushCommand", description="build e push dell'immagine di Docker/03ApiPersoneNoDb (dalla root del repository)",
                  value=f"docker build -t {uri}:latest Docker/03ApiPersoneNoDb && docker push {uri}:latest")

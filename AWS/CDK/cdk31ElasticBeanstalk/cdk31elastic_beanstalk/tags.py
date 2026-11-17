"""Tag standard del repository (convenzione in CLAUDE.md) su tutte le risorse dell'app.

Il tag Name e' diverso per ogni risorsa (uguale al suo nome aws-py-cdkXX-<servizio>): lo mette naming.py.
"""

import json

import aws_cdk as cdk
import jsii
from aws_cdk import aws_ec2 as ec2, aws_iam as iam, aws_lambda as lambda_, aws_logs as logs

from .naming import RULES, PhysicalNames, conforms, current_name, physical_name, servizio

TAGS = {
    "Environment": "dev",
    "Project": "Development.aws.py-CDK.cdk31ElasticBeanstalk",
    "Owner": "AlNao",
    "CostCenter": "dev",
    "ManagedBy": "CDK",
}


def tag_list(name) -> list:
    """Tag standard con il Name della risorsa, nel formato di CloudFormation."""
    return [{"Key": "Name", "Value": name}] + [{"Key": k, "Value": v} for k, v in TAGS.items()]


@jsii.implements(cdk.IAspect)
class TagRawResources:
    """Le risorse di supporto create da CDK come CfnResource (es. il provider che svuota i
    bucket al destroy) non ricevono i tag da Tags.of: li aggiunge direttamente, con il loro Name."""

    def visit(self, node):
        if (isinstance(node, cdk.CfnResource) and not cdk.TagManager.is_taggable(node)
                and node.cfn_resource_type in ("AWS::IAM::Role", "AWS::Lambda::Function")):
            node.add_property_override("Tags", tag_list(physical_name(node, RULES[node.cfn_resource_type])))


# risorse create al lancio da un launch template: CDK tagga istanze e volumi, non le interfacce di rete
LAUNCH_TAG_TYPES = ("instance", "volume", "network-interface")


@jsii.implements(cdk.IAspect)
class TagLaunchTemplateResources:
    """Ogni launch template applica i tag standard a istanze, volumi e interfacce di rete che crea; il loro Name e'
    quello del launch template senza "-launch-template"/"-template" (es. aws-py-cdk20-web-server)."""

    def visit(self, node):
        if isinstance(node, ec2.CfnLaunchTemplate):
            base = servizio(node)
            for suffix in ("-launch-template", "-template"):
                base = base.removesuffix(suffix)
            tags = tag_list(f"{cdk.Stack.of(node).stack_name}-{base}")
            node.add_property_override("LaunchTemplateData.TagSpecifications",
                                       [{"ResourceType": t, "Tags": tags} for t in LAUNCH_TAG_TYPES])


# politica gestita che permette a Lambda di creare da sola i log group (logs:CreateLogGroup su tutto)
BASIC_EXECUTION_POLICY = "AWSLambdaBasicExecutionRole"


@jsii.implements(cdk.IAspect)
class LambdaLogGroups:
    """Ogni Lambda scrive in un log group dello stack (tag standard, 7 giorni, cancellato al destroy) e non ne crea altri.

    - Lambda di supporto di CDK (svuotamento dei bucket, notifiche S3, security group di default della VPC, ...):
      non hanno un log group, Lambda lo creerebbe da sola al primo avvio senza tag e senza scadenza, e resterebbe
      dopo il destroy: l'aspect ne aggiunge uno (/aws/lambda/<nome della funzione>)
    - tutte le Lambda (anche quelle degli esempi, che il log group lo hanno gia'): il ruolo perde
      AWSLambdaBasicExecutionRole e puo' solo scrivere nel proprio log group, cosi' le ultime righe di log che
      arrivano durante il destroy, dopo la cancellazione del gruppo, non lo fanno ricreare senza tag
    """

    def visit(self, node):
        if not (isinstance(node, cdk.CfnResource) and node.cfn_resource_type == "AWS::Lambda::Function"):
            return
        scope = node.node.scope
        if scope.node.try_find_child("LogsPolicy"):
            return  # gia' visitata
        stack = cdk.Stack.of(node)
        if isinstance(node, lambda_.CfnFunction) and node.logging_config is not None:
            configured = stack.resolve(node.logging_config)
            group_ref = configured.get("logGroup", configured.get("LogGroup")) if isinstance(configured, dict) else None
            log_group = self._find(stack, group_ref.get("Ref")) if isinstance(group_ref, dict) else None
            if log_group is None:
                return  # log group indicato per nome: il ruolo resta com'e'
        else:
            log_group = logs.CfnLogGroup(scope, "Logs", retention_in_days=7,
                                         log_group_name=f"/aws/lambda/{self._function_name(stack, node)}")
            log_group.tags.set_tag("Name", log_group.log_group_name, 400)
            for key, value in TAGS.items():
                log_group.tags.set_tag(key, value, 300)
            log_group.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
            node.add_property_override("LoggingConfig.LogGroup", log_group.ref)

        role = self._role(stack, node)
        if role is None:
            return
        if isinstance(role, iam.CfnRole):
            managed = [arn for arn in (stack.resolve(role.managed_policy_arns) or [])
                       if BASIC_EXECUTION_POLICY not in json.dumps(arn)]
            if managed:
                role.add_property_override("ManagedPolicyArns", managed)
            else:
                role.add_property_deletion_override("ManagedPolicyArns")
        else:  # ruolo dei provider di CDK (CfnResource generica): ha solo AWSLambdaBasicExecutionRole
            role.add_property_deletion_override("ManagedPolicyArns")
        policy = iam.CfnPolicy(scope, "LogsPolicy", roles=[role.ref], policy_name="logs",
            policy_document={"Version": "2012-10-17", "Statement": [{
                "Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
                "Resource": log_group.get_att("Arn")}]})
        policy.policy_name = physical_name(policy, RULES["AWS::IAM::Policy"])
        node.add_resource_dependency(policy)  # la Lambda parte solo quando puo' scrivere i log

    @staticmethod
    def _function_name(stack, function) -> str:
        """Nome che la funzione avra' (quello del codice, oppure quello che le dara' PhysicalNames)."""
        rule = RULES["AWS::Lambda::Function"]
        name = current_name(function, rule[0])
        return name if name is not None and conforms(function, name, rule[3]) else physical_name(function, rule)

    @staticmethod
    def _find(stack, logical_id):
        for child in stack.node.find_all():
            if isinstance(child, cdk.CfnResource) and stack.resolve(child.logical_id) == logical_id:
                return child
        return None

    @classmethod
    def _role(cls, stack, function):
        """Ruolo della Lambda: per le CfnFunction dal GetAtt della proprieta' Role, per i provider il ruolo nello stesso costrutto."""
        if isinstance(function, lambda_.CfnFunction):
            target = stack.resolve(function.role)
            role = cls._find(stack, target["Fn::GetAtt"][0]) if isinstance(target, dict) and "Fn::GetAtt" in target else None
            return role if role is not None and role.cfn_resource_type == "AWS::IAM::Role" else None
        return next((c for c in function.node.scope.node.find_all()
                     if isinstance(c, cdk.CfnResource) and c.cfn_resource_type == "AWS::IAM::Role"), None)


def apply_tags(scope) -> None:
    """Tag e nomi su tutte le risorse sotto scope (l'app in app.py, la stessa chiamata nei test).
    Priorita' 300 per i tag standard, 400 per il Name di ogni risorsa (vince sui Name che CDK mette da solo)."""
    for key, value in TAGS.items():
        cdk.Tags.of(scope).add(key, value, priority=300)
    cdk.Aspects.of(scope).add(TagRawResources())
    cdk.Aspects.of(scope).add(TagLaunchTemplateResources())
    cdk.Aspects.of(scope).add(LambdaLogGroups())
    cdk.Aspects.of(scope).add(PhysicalNames())

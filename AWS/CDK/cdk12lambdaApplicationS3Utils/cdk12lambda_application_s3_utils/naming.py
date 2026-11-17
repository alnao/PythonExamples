"""Nomi delle risorse: aws-py-cdkXX-<servizio> (convenzione in CLAUDE.md), uguali al tag Name.

- il nome dello stack e' il prefisso (aws-py-cdkXX, in app.py); <servizio> e' in minuscolo con i trattini
- nome_risorsa(scope, "create-item") per i nomi scritti nel codice (servono quando una risorsa e' citata per nome)
- l'aspect PhysicalNames da' un nome a tutte le altre risorse (anche quelle create da CDK) a partire dall'id del
  costrutto, e mette il tag Name uguale al nome; le risorse senza proprieta' del nome (istanze EC2, EFS, VPC,
  CloudFront, ...) hanno solo il tag Name
- bucket S3: nome con l'account alla fine (i nomi dei bucket sono unici in tutto AWS); ruoli e instance profile
  IAM: nome con la region alla fine (i nomi IAM valgono per tutto l'account)
- check_template(...) controlla un template sintetizzato (usata dai test)
"""

import hashlib
import json
import re

import aws_cdk as cdk
import jsii

STACK_NAME = re.compile(r"^aws-py-cdk\d\d$")

# tipo -> (proprieta' del nome, lunghezza massima, suffisso, stile)
#   suffisso: "account" (S3), "region" (IAM) o None; stile: "kebab" (default), "snake" (solo lettere, numeri e _)
RULES = {
    "AWS::ApiGateway::Authorizer": ("Name", 128, None, "kebab"),
    "AWS::ApiGateway::RestApi": ("Name", 128, None, "kebab"),
    "AWS::ApiGatewayV2::Api": ("Name", 128, None, "kebab"),
    "AWS::AppSync::DataSource": ("Name", 128, None, "snake"),
    "AWS::AppSync::GraphQLApi": ("Name", 128, None, "kebab"),
    "AWS::AutoScaling::AutoScalingGroup": ("AutoScalingGroupName", 255, None, "kebab"),
    "AWS::Bedrock::ApplicationInferenceProfile": ("InferenceProfileName", 64, None, "kebab"),
    "AWS::Bedrock::DataSource": ("Name", 100, None, "kebab"),
    "AWS::Bedrock::KnowledgeBase": ("Name", 100, None, "kebab"),
    "AWS::CloudFront::OriginAccessControl": ("OriginAccessControlConfig.Name", 64, None, "kebab"),
    "AWS::CloudWatch::Alarm": ("AlarmName", 255, None, "kebab"),
    "AWS::CloudWatch::Dashboard": ("DashboardName", 255, None, "kebab"),
    "AWS::CodeBuild::Project": ("Name", 150, None, "kebab"),
    "AWS::CodePipeline::Pipeline": ("Name", 100, None, "kebab"),
    "AWS::DynamoDB::GlobalTable": ("TableName", 255, None, "kebab"),
    "AWS::DynamoDB::Table": ("TableName", 255, None, "kebab"),
    "AWS::EC2::LaunchTemplate": ("LaunchTemplateName", 128, None, "kebab"),
    "AWS::EC2::SecurityGroup": ("GroupName", 255, None, "kebab"),
    "AWS::ECR::Repository": ("RepositoryName", 256, None, "kebab"),
    "AWS::ECS::Cluster": ("ClusterName", 255, None, "kebab"),
    "AWS::ECS::Service": ("ServiceName", 255, None, "kebab"),
    "AWS::ECS::TaskDefinition": ("Family", 255, None, "kebab"),
    "AWS::EKS::Cluster": ("Name", 100, None, "kebab"),
    "AWS::EKS::Nodegroup": ("NodegroupName", 63, None, "kebab"),
    "AWS::ElasticBeanstalk::Application": ("ApplicationName", 100, None, "kebab"),
    "AWS::ElasticBeanstalk::Environment": ("EnvironmentName", 40, None, "kebab"),
    "AWS::ElasticLoadBalancingV2::LoadBalancer": ("Name", 32, None, "kebab"),
    "AWS::ElasticLoadBalancingV2::TargetGroup": ("Name", 32, None, "kebab"),
    "AWS::Events::Rule": ("Name", 64, None, "kebab"),
    "AWS::Glue::Classifier": ("CsvClassifier.Name", 255, None, "kebab"),
    "AWS::Glue::Connection": ("ConnectionInput.Name", 255, None, "kebab"),
    "AWS::Glue::Crawler": ("Name", 255, None, "kebab"),
    "AWS::Glue::Database": ("DatabaseInput.Name", 255, None, "snake"),
    "AWS::Glue::Job": ("Name", 255, None, "kebab"),
    "AWS::Glue::Trigger": ("Name", 255, None, "kebab"),
    "AWS::Glue::Workflow": ("Name", 255, None, "kebab"),
    "AWS::IAM::InstanceProfile": ("InstanceProfileName", 128, "region", "kebab"),
    "AWS::IAM::ManagedPolicy": ("ManagedPolicyName", 128, "region", "kebab"),
    "AWS::IAM::Policy": ("PolicyName", 128, None, "kebab"),
    "AWS::IAM::Role": ("RoleName", 64, "region", "kebab"),
    "AWS::Lambda::Function": ("FunctionName", 64, None, "kebab"),
    "AWS::Lambda::LayerVersion": ("LayerName", 140, None, "kebab"),
    "AWS::Logs::LogGroup": ("LogGroupName", 512, None, "path"),
    "AWS::RDS::DBCluster": ("DBClusterIdentifier", 63, None, "kebab"),
    "AWS::RDS::DBInstance": ("DBInstanceIdentifier", 63, None, "kebab"),
    "AWS::RDS::DBSubnetGroup": ("DBSubnetGroupName", 255, None, "kebab"),
    "AWS::S3::Bucket": ("BucketName", 63, "account", "kebab"),
    "AWS::S3Vectors::Index": ("IndexName", 63, None, "kebab"),
    "AWS::S3Vectors::VectorBucket": ("VectorBucketName", 63, None, "kebab"),
    "AWS::SNS::Topic": ("TopicName", 256, None, "kebab"),
    "AWS::SQS::Queue": ("QueueName", 80, None, "kebab"),
    "AWS::SecretsManager::Secret": ("Name", 512, None, "kebab"),
    "AWS::StepFunctions::StateMachine": ("StateMachineName", 80, None, "kebab"),
}
# tipi senza proprieta' del nome: solo il tag Name
TAG_ONLY = {
    "AWS::CloudFront::Distribution", "AWS::EC2::ClientVpnEndpoint", "AWS::EC2::EIP", "AWS::EC2::FlowLog",
    "AWS::EC2::Instance", "AWS::EC2::InternetGateway", "AWS::EC2::NatGateway", "AWS::EC2::NetworkInterface",
    "AWS::EC2::RouteTable", "AWS::EC2::Subnet", "AWS::EC2::VPC", "AWS::EC2::VPCEndpoint", "AWS::EFS::FileSystem",
}
# tipi in cui il nome non puo' iniziare con "aws": prefisso davanti al nome (come fa CDK con "cp-")
NO_AWS_PREFIX = {"AWS::ECS::CapacityProvider": ("Name", "cp-")}
# log group con il nome deciso dal servizio (es. AppSync scrive solo in /aws/appsync/apis/<id dell'API>)
SERVICE_LOG_GROUPS = ("/aws/appsync/apis/",)
# nomi sostituiti dall'aspect, per stack: se il vecchio nome resta citato come stringa (es. i resolver di AppSync
# citano la data source per nome) il deploy fallirebbe; check_template lo segnala
REPLACED_NAMES = {}
SUFFIX_LENGTH = {"account": 13, "region": 15}  # "-" + 12 cifre, "-" + region piu' lunga (es. ap-southeast-4)
GENERIC = {"Resource", "Default"}
# id interni di CDK senza significato -> nome leggibile (Lambda condivisa delle AwsCustomResource)
CDK_SINGLETONS = {"AWS679f53fac002430cb0da5b7982bd2287": "AwsCustomResource"}


def kebab(text: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", text)
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def nome_risorsa(scope, servizio: str) -> str:
    """Nome scritto nel codice: aws-py-cdkXX-<servizio> (servizio in qualunque forma, diventa minuscolo con -)."""
    stack_name = cdk.Stack.of(scope).stack_name
    return f"{stack_name}-{kebab(servizio)}"


def servizio(node) -> str:
    """<servizio> dall'id del costrutto e dei suoi genitori (senza Resource/Default e senza gli hash di CDK)."""
    stack = cdk.Stack.of(node)
    parts = []
    for scope in node.node.scopes:
        if scope is stack or isinstance(scope, cdk.App) or scope.node.id in GENERIC or not scope.node.id:
            continue
        part = CDK_SINGLETONS.get(scope.node.id, scope.node.id).replace("Custom::", "").replace("CustomResourceProvider", "")
        part = re.sub(r"[0-9a-fA-F]{32}$|^AWS[0-9a-f]{32}$", "", part)
        if part and (not parts or kebab(part) != parts[-1]):  # pezzi uguali in fila (es. X/X) una volta sola
            parts.append(kebab(part))
    words = "-".join(parts).split("-")
    # parole ripetute in fila (es. bucket-notifications-handler-...-handler-role) una volta sola
    return "-".join(w for i, w in enumerate(words) if w and (i == 0 or w != words[i - 1]))


def physical_name(node, rule) -> str:
    """Nome completo (stringa o token) di una risorsa senza nome, dentro la lunghezza massima del tipo."""
    prop, max_length, suffix, style = rule
    stack = cdk.Stack.of(node)
    prefix = stack.stack_name
    base = servizio(node) or "resource"
    if style == "path":
        return f"/{prefix}/{base}"
    limit = max_length - SUFFIX_LENGTH.get(suffix, 0) - len(prefix) - 1
    if len(base) > limit:  # troppo lungo: inizio del nome + hash del percorso, sempre diverso tra risorse diverse
        digest = hashlib.sha1(node.node.path.encode()).hexdigest()[:6]
        base = base[:limit - 7].rstrip("-") + "-" + digest
    name = f"{prefix}-{base}"
    if style == "snake":
        name = name.replace("-", "_")
    if suffix == "account":
        return cdk.Fn.join("-", [name, stack.account])
    if suffix == "region":
        return cdk.Fn.join("-", [name, stack.region])
    return name


def _snake(prop: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", prop).lower()


def current_name(node, prop: str):
    """Nome gia' impostato su una risorsa L1 (dal codice o da CDK); None per le CfnResource generiche e se manca."""
    if type(node) is cdk.CfnResource:
        return None
    first, _, nested = prop.partition(".")
    value = getattr(node, _snake(first), None)
    if value is not None and cdk.Token.is_unresolved(value) and cdk.Stack.of(node).resolve(value) is None:
        return None  # nome "pigro" di CDK che resta vuoto: lo genererebbe CloudFormation
    if value is None or not nested:
        return value
    resolved = cdk.Stack.of(node).resolve(value)
    if isinstance(resolved, dict):
        return resolved.get(nested, resolved.get(nested[0].lower() + nested[1:]))
    return None


def conforms(node, name, style: str) -> bool:
    """Il nome segue la convenzione? (i nomi "pigri" di CDK, es. XxxDefaultPolicy1234, contano per il valore finale)"""
    stack_name = cdk.Stack.of(node).stack_name
    if cdk.Token.is_unresolved(name):
        resolved = cdk.Stack.of(node).resolve(name)
        if not isinstance(resolved, str):
            return True  # nome costruito nel codice (es. con account o region): lo controllano i test
        name = resolved  # nome "pigro" di CDK (es. XxxDefaultPolicy1234): conta il valore finale
    if style == "path":
        return f"/{stack_name}/" in name or f"/{stack_name}-" in name
    prefix = stack_name.replace("-", "_") + "_" if style == "snake" else stack_name + "-"
    return name.startswith(prefix)


def set_name_tag(node, name, apply_to_launched=True) -> None:
    manager = cdk.TagManager.of(node)  # anche le risorse con l'interfaccia nuova dei tag (ITaggableV2)
    if manager is None and node.cfn_resource_type == "AWS::DynamoDB::GlobalTable":
        manager = cdk.TagManager.of(node.node.scope)  # TableV2: i tag delle repliche li gestisce il costrutto L2
    if manager is not None:
        manager.set_tag("Name", name, 400, apply_to_launched)


@jsii.implements(cdk.IAspect)
class PhysicalNames:
    """Nome aws-py-cdkXX-<servizio> a ogni risorsa che ne puo' avere uno, e tag Name uguale al nome."""

    def visit(self, node):
        if isinstance(node, cdk.Stack):  # lo stack CloudFormation: tag Name uguale al suo nome (aws-py-cdkXX)
            node.tags.set_tag("Name", node.stack_name, 400)
            return
        if not isinstance(node, cdk.CfnResource):
            return
        stack = cdk.Stack.of(node)
        if not STACK_NAME.match(stack.stack_name):
            raise ValueError(f"nome dello stack {stack.stack_name!r}: deve essere aws-py-cdkXX (app.py e test)")
        kind = node.cfn_resource_type
        if kind in TAG_ONLY:
            set_name_tag(node, f"{stack.stack_name}-{servizio(node)}")
        elif kind in NO_AWS_PREFIX:
            prop, prefix = NO_AWS_PREFIX[kind]
            name = current_name(node, prop)
            if name is None or not str(stack.resolve(name)).startswith(f"{prefix}{stack.stack_name}-"):
                name = f"{prefix}{stack.stack_name}-{servizio(node)}"
                node.add_property_override(prop, name)
            set_name_tag(node, name)
        elif kind in RULES:
            rule = RULES[kind]
            name = current_name(node, rule[0])
            if name is None or not conforms(node, name, rule[3]):
                old = stack.resolve(name) if name is not None else None
                if isinstance(old, str):
                    REPLACED_NAMES.setdefault(stack.stack_name, set()).add(old)
                name = physical_name(node, rule)
                node.add_property_override(rule[0], name)
            # Auto Scaling group: il tag Name non passa alle istanze (lo hanno gia' dal launch template)
            set_name_tag(node, name, kind != "AWS::AutoScaling::AutoScalingGroup")
        else:  # ogni altra risorsa che accetta tag (stage delle API, add-on EKS, ...): solo il tag Name
            set_name_tag(node, f"{stack.stack_name}-{servizio(node)}")


# ---------------------------------------------------------------- controllo dei template (test)

def _render(value) -> str:
    """Valore leggibile: Ref di account/region e Fn::Join diventano stringhe di esempio della lunghezza massima."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and "Ref" in value:
        return {"AWS::AccountId": "123456789012", "AWS::Region": "ap-southeast-4"}.get(value["Ref"], "<ref>")
    if isinstance(value, dict) and "Fn::Join" in value:
        separator, parts = value["Fn::Join"]
        return separator.join(_render(p) for p in parts)
    return "<token>"


def check_template(template: dict, stack_name: str) -> list:
    """Problemi di nomi e tag Name di un template sintetizzato (lista vuota se tutto e' in regola)."""
    problems, seen = [], {}
    text = json.dumps(template)
    for old in sorted(REPLACED_NAMES.get(stack_name, ())):
        if old not in template["Resources"] and json.dumps(old) in text:  # (le policy IAM di CDK hanno come nome l'id logico)
            problems.append(f"nome sostituito {old!r} ancora citato nel template: va dato nel codice con nome_risorsa")
    for logical_id, resource in template["Resources"].items():
        kind, props = resource["Type"], resource.get("Properties") or {}
        tags = props.get("Tags", props.get("FileSystemTags"))
        if isinstance(tags, list):
            tag_name = next((t.get("Value") for t in tags if isinstance(t, dict) and t.get("Key") == "Name"), None)
        elif isinstance(tags, dict):
            tag_name = tags.get("Name")
        else:
            tag_name = next((t.get("Value") for r in props.get("Replicas", []) for t in r.get("Tags", [])
                             if t.get("Key") == "Name"), None)
        if kind in TAG_ONLY:
            if not (isinstance(tag_name, str) and tag_name.startswith(stack_name + "-")):
                problems.append(f"{logical_id} ({kind}): tag Name {tag_name!r}")
            continue
        if kind in NO_AWS_PREFIX:
            prop, prefix = NO_AWS_PREFIX[kind]
            name = props.get(prop)
            if not (isinstance(name, str) and name.startswith(f"{prefix}{stack_name}-") and tag_name == name):
                problems.append(f"{logical_id} ({kind}): nome {name!r}, tag Name {tag_name!r}")
            continue
        if kind not in RULES:
            if tags and not (isinstance(tag_name, str) and tag_name.startswith(stack_name + "-")):
                problems.append(f"{logical_id} ({kind}): tag Name {tag_name!r}")
            continue
        prop, max_length, suffix, style = RULES[kind]
        value = props
        for part in prop.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if value is None:
            problems.append(f"{logical_id} ({kind}): senza nome")
            continue
        name = _render(value)
        if style == "path" and name.startswith(SERVICE_LOG_GROUPS):
            continue
        prefix = stack_name.replace("-", "_") if style == "snake" else stack_name
        ok_start = (f"/{prefix}/" in name or f"/{prefix}-" in name) if style == "path" else name.startswith(prefix + ("_" if style == "snake" else "-"))
        if not ok_start:
            problems.append(f"{logical_id} ({kind}): {name!r} non inizia con {prefix}")
        if len(name) > max_length:
            problems.append(f"{logical_id} ({kind}): {name!r} piu' lungo di {max_length}")
        body = name.split("/")[-1] if style == "path" else name
        if style != "path" and not re.fullmatch(r"[a-z0-9_]+" if style == "snake" else r"[a-z0-9-]+", body):
            problems.append(f"{logical_id} ({kind}): {name!r} non e' tutto minuscolo con -")
        if suffix and not re.search({"account": r"-\d{12}$", "region": r"-[a-z]{2}(-[a-z]+)+-\d$"}[suffix], name):
            problems.append(f"{logical_id} ({kind}): {name!r} senza {suffix} alla fine")
        if (tags is not None or tag_name is not None) and json.dumps(tag_name) != json.dumps(value):
            problems.append(f"{logical_id} ({kind}): tag Name {tag_name!r} diverso dal nome {value!r}")
        key = (kind, json.dumps(value))
        if key in seen:
            problems.append(f"{logical_id} ({kind}): stesso nome di {seen[key]}")
        seen[key] = logical_id
    return problems


def _tag_value(tags):
    if isinstance(tags, dict):
        return tags.get("Name")
    return next((t.get("Value") for t in tags if isinstance(t, dict) and t.get("Key") == "Name"), None)

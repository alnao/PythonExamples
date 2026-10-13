"""
Stack del Pocket RAG serverless (Francoforte):

    browser ── CloudFront ──┬── /*      bucket S3 del sito (privato, Origin Access Control)
                            └── /api/*  HTTP API Gateway ── Lambda Api
    browser ── POST prefirmato ── bucket documenti (uploads/) ── evento ── Lambda Ingest
    Lambda ── Bedrock (Titan embedding, chat, immagini) e indice S3 Vectors
"""

from aws_cdk import (
    CfnOutput,
    CfnResource,
    Duration,
    Fn,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_s3_notifications as s3n,
    aws_s3vectors as s3vectors,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

# Lunghezze massime ammesse da AWS per i nomi assegnati in physical_names
NAME_LIMITS = {"FunctionName": 64, "RoleName": 64, "PolicyName": 128, "LayerName": 140}

# Modelli Bedrock: i profili "eu." instradano le richieste nelle region europee
MODELS = {
    "EMBEDDING_MODEL": "amazon.titan-embed-text-v2:0",
    "CHAT_MODEL": "eu.amazon.nova-lite-v1:0",
    # Amazon Nova Lite: circa 0,0003 $ a immagine; "" = immagini non accettate
    "IMAGE_MODEL": "eu.amazon.nova-lite-v1:0",
}
GEO_PREFIXES = ("eu.", "us.", "apac.", "global.")
MAX_UPLOAD_MB = 250

# Nomi fissi delle risorse (al posto dei suffissi casuali di CDK e CloudFormation):
# Lambda e altre risorse NAME-<nome>, log group /NAME/<nome>, bucket BUCKET_PREFIX-<nome>
# (i nomi dei bucket devono essere minuscoli), ruoli e policy IAM <nome dello stack>-<nome>Service...
NAME = "Cdk33BedrockServerless"
BUCKET_PREFIX = "alnao-dev-cdk-cdk33bedrockserverless"
# Risorse create internamente da CDK, riconosciute dal percorso del construct
SUPPORT_OWNERS = (
    ("/Custom::S3AutoDeleteObjectsCustomResourceProvider/", "AutoDeleteObjects"),
    ("/BucketNotificationsHandler", "BucketNotifications"),
    ("/Notifications/HandlerPolicy/", "BucketNotifications"),
    ("/Custom::CDKBucketDeployment", "BucketDeployment"),
    ("/SiteContent/AwsCliLayer/", "AwsCli"),
    ("/Api/", "Api"),
    ("/Ingest/", "Ingest"),
)


class Cdk33BedrockServerlessStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, layer_dir: str = "layer", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Documenti originali e stato dell'indicizzazione (il browser carica con un POST prefirmato)
        documents = s3.Bucket(
            self, "Documents",
            bucket_name=f"{BUCKET_PREFIX}-documents",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.POST], allowed_origins=["*"],
                              allowed_headers=["*"])],
        )

        # Indice vettoriale: 1024 dimensioni (Titan v2), distanza coseno, testo non filtrabile
        vector_bucket = s3vectors.CfnVectorBucket(self, "Vectors", vector_bucket_name=f"{BUCKET_PREFIX}-vectors")
        vector_bucket.apply_removal_policy(RemovalPolicy.DESTROY)
        index = s3vectors.CfnIndex(
            self, "Index",
            vector_bucket_arn=vector_bucket.attr_vector_bucket_arn,
            index_name="docs",
            data_type="float32",
            dimension=1024,
            distance_metric="cosine",
            metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                non_filterable_metadata_keys=["text"]),
        )
        index.apply_removal_policy(RemovalPolicy.DESTROY)

        # Chiave delle API generata da Secrets Manager
        api_key = secretsmanager.Secret(
            self, "ApiKey",
            secret_name=f"{NAME}-ApiKey",
            description="Chiave X-API-Key del Pocket RAG serverless",
            generate_secret_string=secretsmanager.SecretStringGenerator(exclude_punctuation=True, password_length=40),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Librerie Python (pypdf, python-docx, ...) create da build_layer.sh
        libraries = _lambda.LayerVersion(
            self, "Libraries",
            layer_version_name=f"{NAME}-Libraries",
            code=_lambda.Code.from_asset(layer_dir),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            compatible_architectures=[_lambda.Architecture.X86_64],
            description="Librerie del Pocket RAG serverless",
        )
        environment = {
            "DOCS_BUCKET": documents.bucket_name,
            "INDEX_ARN": index.attr_index_arn,
            "CHAT_TEMPERATURE": "0.2",
            "CHUNK_SIZE": "1000",
            "CHUNK_OVERLAP": "200",
            **MODELS,
        }

        # file fino a 250 MB: 3008 MB di memoria (e quindi piu' CPU; e' anche il massimo concesso di default
        # agli account nuovi, oltre serve una richiesta in Service Quotas), il massimo di 15 minuti e nessun
        # nuovo tentativo automatico (su un file enorme triplicherebbe tempi e costi)
        ingest_fn = self.function("Ingest", "ingest.handler", libraries, environment,
                                  timeout=Duration.minutes(15), memory_size=3008, retry_attempts=0)
        api_fn = self.function("Api", "api.handler", libraries,
                               {**environment, "API_KEY_SECRET_ARN": api_key.secret_arn,
                                "MAX_UPLOAD_MB": str(MAX_UPLOAD_MB)},
                               timeout=Duration.seconds(29), memory_size=512)

        # Permessi minimi
        documents.grant_read_write(ingest_fn)
        documents.grant_read_write(api_fn)
        api_key.grant_read(api_fn)
        bedrock_models = iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=self.model_arns())
        ingest_fn.add_to_role_policy(bedrock_models)
        api_fn.add_to_role_policy(bedrock_models)
        ingest_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["s3vectors:PutVectors", "s3vectors:DeleteVectors"], resources=[index.attr_index_arn]))
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["s3vectors:QueryVectors", "s3vectors:GetVectors", "s3vectors:DeleteVectors"],
            resources=[index.attr_index_arn]))

        # Ogni file in uploads/ avvia l'indicizzazione
        documents.add_event_notification(s3.EventType.OBJECT_CREATED, s3n.LambdaDestination(ingest_fn),
                                         s3.NotificationKeyFilter(prefix="uploads/"))

        # API: tutte le richieste /api/* alla Lambda Api
        http_api = apigw.HttpApi(self, "HttpApi", api_name=f"{NAME}-HttpApi", description="API del Pocket RAG serverless")
        http_api.add_routes(path="/api/{proxy+}", methods=[apigw.HttpMethod.ANY],
                            integration=integrations.HttpLambdaIntegration("ApiIntegration", api_fn))

        # Sito statico e API sullo stesso dominio CloudFront (niente CORS per le API)
        site = s3.Bucket(
            self, "Site",
            bucket_name=f"{BUCKET_PREFIX}-site",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        api_domain = Fn.select(2, Fn.split("/", http_api.api_endpoint))
        distribution = cloudfront.Distribution(
            self, "Distribution",
            comment="Pocket RAG serverless",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    site, origin_access_control=cloudfront.S3OriginAccessControl(
                        self, "SiteAccessControl", origin_access_control_name=f"{NAME}-Site")),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(api_domain, protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                ),
            },
        )
        s3deploy.BucketDeployment(self, "SiteContent", sources=[s3deploy.Source.asset("web")],
                                  destination_bucket=site, distribution=distribution, distribution_paths=["/*"])

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "ApiKeyCommand", value=(
            f"aws secretsmanager get-secret-value --secret-id {api_key.secret_name} "
            f"--region {self.region} --query SecretString --output text"))
        CfnOutput(self, "DocumentsBucket", value=documents.bucket_name)

        self.physical_names()

    def physical_names(self) -> None:
        """Nomi fissi per Lambda, ruoli, policy e layer, comprese le risorse create internamente da
        CDK (svuotamento dei bucket, notifiche S3, deploy del sito). Le Lambda di supporto ricevono
        anche un log group dello stack (con i tag e cancellato dal destroy) al posto di quello che
        Lambda creerebbe da sola al primo avvio."""
        for resource in [c for c in self.node.find_all() if isinstance(c, CfnResource)]:
            owner = next((name for marker, name in SUPPORT_OWNERS if marker in f"/{resource.node.path}/"), None)
            kind = resource.cfn_resource_type
            if owner is None:
                continue
            if kind == "AWS::Lambda::Function":
                self.set_name(resource, "FunctionName", f"{NAME}-{owner}")
                if not (isinstance(resource, _lambda.CfnFunction) and resource.logging_config is not None):
                    log_group = logs.LogGroup(self, f"{resource.node.scope.node.id}Logs", log_group_name=f"/{NAME}/{owner}",
                                              retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
                    resource.add_property_override("LoggingConfig.LogGroup", log_group.log_group_name)
            elif kind == "AWS::IAM::Role":
                self.set_name(resource, "RoleName", f"{self.stack_name}-{owner}ServiceRole")
            elif kind == "AWS::IAM::Policy":
                self.set_name(resource, "PolicyName", f"{self.stack_name}-{owner}ServicePolicy")
            elif kind == "AWS::Lambda::LayerVersion":
                self.set_name(resource, "LayerName", f"{NAME}-{owner}")

    @staticmethod
    def set_name(resource: CfnResource, prop: str, value: str) -> None:
        """Assegna un nome fisso controllando la lunghezza: meglio un errore in cdk synth che in deploy."""
        if len(value) > NAME_LIMITS[prop]:
            raise ValueError(f"{prop} '{value}' ha {len(value)} caratteri, AWS ne ammette al massimo {NAME_LIMITS[prop]}")
        resource.add_property_override(prop, value)

    def function(self, name: str, handler: str, layer: _lambda.ILayerVersion, environment: dict,
                 timeout: Duration, memory_size: int, retry_attempts: int = None) -> _lambda.Function:
        log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/{NAME}/{name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        return _lambda.Function(
            self, name,
            function_name=f"{NAME}-{name}",
            runtime=_lambda.Runtime.PYTHON_3_13,
            architecture=_lambda.Architecture.X86_64,
            handler=handler,
            code=_lambda.Code.from_asset("lambda"),
            layers=[layer],
            environment=environment,
            timeout=timeout,
            memory_size=memory_size,
            retry_attempts=retry_attempts,
            log_group=log_group,
        )

    def model_arns(self) -> list:
        """ARN dei modelli: per i profili cross-region servono il profilo e il modello in ogni region."""
        arns = []
        for model_id in filter(None, MODELS.values()):
            if model_id.startswith(GEO_PREFIXES):
                base_model = model_id.split(".", 1)[1]
                arns.append(f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/{model_id}")
                arns.append(f"arn:aws:bedrock:*::foundation-model/{base_model}")
            else:
                arns.append(f"arn:aws:bedrock:{self.region}::foundation-model/{model_id}")
        return arns

"""
Stack del RAG con Bedrock Knowledge Base su S3 Vectors (Francoforte): estrazione del testo,
chunking, embedding e indice sono gestiti da Bedrock, le Lambda chiedono solo i brani e la risposta.

    browser ── CloudFront ──┬── /*      bucket S3 del sito (privato, Origin Access Control)
                            └── /api/*  HTTP API Gateway ── Lambda Api ──┬── Knowledge Base: Retrieve (brani)
                                                                         └── profilo Chat (con i tag) ── Nova Lite
    browser ── POST prefirmato ── bucket documenti (uploads/) ── eventi S3 ── coda SQS ── Lambda Sync
        Lambda Sync ── StartIngestionJob ── Knowledge Base ── Titan (embedding) ── indice S3 Vectors
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
    aws_bedrock as bedrock,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_event_sources as event_sources,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_s3_notifications as s3n,
    aws_s3vectors as s3vectors,
    aws_secretsmanager as secretsmanager,
    aws_sqs as sqs,
)
from constructs import Construct

# Lunghezze massime ammesse da AWS per i nomi assegnati in physical_names
NAME_LIMITS = {"FunctionName": 64, "RoleName": 64, "PolicyName": 128, "LayerName": 140}

# Embedding fatti dalla Knowledge Base (modello di base, nella region) e risposte con Nova Lite
# tramite il profilo cross-region "eu." copiato in un profilo dell'applicazione con i tag
EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
CHAT_MODEL = "eu.amazon.nova-lite-v1:0"
DIMENSIONS = 1024
# parti da 300 token con il 20% di sovrapposizione (i valori di default di Bedrock)
CHUNK_MAX_TOKENS = 300
CHUNK_OVERLAP_PERCENT = 20
# la Knowledge Base non indicizza file oltre 50 MB
MAX_UPLOAD_MB = 50
DOCS_PREFIX = "uploads/"

# Nomi fissi delle risorse (al posto dei suffissi casuali di CDK e CloudFormation):
# Lambda e altre risorse NAME-<nome>, log group /NAME/<nome>, bucket BUCKET_PREFIX-<nome>
# (i nomi dei bucket devono essere minuscoli), ruoli e policy IAM <nome dello stack>-<nome>Service...
NAME = "Cdk34BedrockKnowledgeBase"
BUCKET_PREFIX = "alnao-dev-cdk-cdk34bedrockknowledgebase"
# Risorse create internamente da CDK, riconosciute dal percorso del construct
SUPPORT_OWNERS = (
    ("/Custom::S3AutoDeleteObjectsCustomResourceProvider/", "AutoDeleteObjects"),
    ("/BucketNotificationsHandler", "BucketNotifications"),
    ("/Notifications/HandlerPolicy/", "BucketNotifications"),
    ("/Custom::CDKBucketDeployment", "BucketDeployment"),
    ("/SiteContent/AwsCliLayer/", "AwsCli"),
    ("/KnowledgeBaseRole/", "KnowledgeBase"),
    ("/Api/", "Api"),
    ("/Sync/", "Sync"),
)


class Cdk34BedrockKnowledgeBaseStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Documenti originali (il browser carica con un POST prefirmato): sono la sorgente della Knowledge Base
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

        # Indice vettoriale: 1024 dimensioni (Titan v2), distanza coseno; testo delle parti e metadati
        # di Bedrock non filtrabili, altrimenti superano i 2 KB di metadati filtrabili per vettore
        vector_bucket = s3vectors.CfnVectorBucket(self, "Vectors", vector_bucket_name=f"{BUCKET_PREFIX}-vectors")
        vector_bucket.apply_removal_policy(RemovalPolicy.DESTROY)
        index = s3vectors.CfnIndex(
            self, "Index",
            vector_bucket_arn=vector_bucket.attr_vector_bucket_arn,
            index_name="docs",
            data_type="float32",
            dimension=DIMENSIONS,
            distance_metric="cosine",
            metadata_configuration=s3vectors.CfnIndex.MetadataConfigurationProperty(
                non_filterable_metadata_keys=["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]),
        )
        index.apply_removal_policy(RemovalPolicy.DESTROY)

        # Ruolo della Knowledge Base: legge i documenti, calcola gli embedding, scrive l'indice. Policy inline
        # (nel ruolo stesso): la Knowledge Base controlla l'accesso all'indice gia' quando viene creata
        embedding_arn = f"arn:aws:bedrock:{self.region}::foundation-model/{EMBEDDING_MODEL}"
        kb_role = iam.Role(
            self, "KnowledgeBaseRole",
            description="Ruolo della Knowledge Base del cdk34",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com", conditions={
                "StringEquals": {"aws:SourceAccount": self.account},
                "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:{self.region}:{self.account}:knowledge-base/*"},
            }),
            inline_policies={"KnowledgeBase": iam.PolicyDocument(statements=[
                iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=[embedding_arn]),
                iam.PolicyStatement(actions=["s3:ListBucket"], resources=[documents.bucket_arn],
                                    conditions={"StringEquals": {"aws:ResourceAccount": self.account}}),
                iam.PolicyStatement(actions=["s3:GetObject"], resources=[documents.arn_for_objects(f"{DOCS_PREFIX}*")],
                                    conditions={"StringEquals": {"aws:ResourceAccount": self.account}}),
                iam.PolicyStatement(actions=["s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:DeleteVectors",
                                             "s3vectors:QueryVectors", "s3vectors:GetIndex"],
                                    resources=[index.attr_index_arn]),
            ])},
        )

        knowledge_base = bedrock.CfnKnowledgeBase(
            self, "KnowledgeBase",
            name=NAME,
            description="RAG gestito da Bedrock su S3 Vectors",
            role_arn=kb_role.role_arn,
            knowledge_base_configuration=bedrock.CfnKnowledgeBase.KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=bedrock.CfnKnowledgeBase.VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=embedding_arn,
                    embedding_model_configuration=bedrock.CfnKnowledgeBase.EmbeddingModelConfigurationProperty(
                        bedrock_embedding_model_configuration=bedrock.CfnKnowledgeBase.BedrockEmbeddingModelConfigurationProperty(
                            dimensions=DIMENSIONS, embedding_data_type="FLOAT32")),
                ),
            ),
            storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
                type="S3_VECTORS",
                s3_vectors_configuration=bedrock.CfnKnowledgeBase.S3VectorsConfigurationProperty(
                    index_arn=index.attr_index_arn),
            ),
        )

        # Sorgente: i file in uploads/ del bucket; parser di default (testo di PDF, Office, HTML, CSV),
        # parti a dimensione fissa; DELETE = i vettori si cancellano insieme alla sorgente
        data_source = bedrock.CfnDataSource(
            self, "DataSource",
            knowledge_base_id=knowledge_base.attr_knowledge_base_id,
            name="Documents",
            description="File caricati dal sito",
            data_deletion_policy="DELETE",
            data_source_configuration=bedrock.CfnDataSource.DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=bedrock.CfnDataSource.S3DataSourceConfigurationProperty(
                    bucket_arn=documents.bucket_arn, inclusion_prefixes=[DOCS_PREFIX]),
            ),
            vector_ingestion_configuration=bedrock.CfnDataSource.VectorIngestionConfigurationProperty(
                chunking_configuration=bedrock.CfnDataSource.ChunkingConfigurationProperty(
                    chunking_strategy="FIXED_SIZE",
                    fixed_size_chunking_configuration=bedrock.CfnDataSource.FixedSizeChunkingConfigurationProperty(
                        max_tokens=CHUNK_MAX_TOKENS, overlap_percentage=CHUNK_OVERLAP_PERCENT)),
            ),
        )

        # Profilo di inferenza dell'applicazione per le risposte: ha i tag dello stack, cosi' il costo di
        # Nova Lite arriva al Project dell'esempio in Cost Explorer (chiamando l'ID del modello resterebbe senza tag)
        chat_source = f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/{CHAT_MODEL}"
        chat_profile = bedrock.CfnApplicationInferenceProfile(
            self, "ChatProfile",
            inference_profile_name=f"{NAME}-Chat",
            description=f"Risposte della Knowledge Base con {CHAT_MODEL}",
            model_source=bedrock.CfnApplicationInferenceProfile.InferenceProfileModelSourceProperty(copy_from=chat_source),
        )

        # Chiave delle API generata da Secrets Manager
        api_key = secretsmanager.Secret(
            self, "ApiKey",
            secret_name=f"{NAME}-ApiKey",
            description="Chiave X-API-Key del RAG con Bedrock Knowledge Base",
            generate_secret_string=secretsmanager.SecretStringGenerator(exclude_punctuation=True, password_length=40),
            removal_policy=RemovalPolicy.DESTROY,
        )

        environment = {
            "DOCS_BUCKET": documents.bucket_name,
            "DOCS_PREFIX": DOCS_PREFIX,
            "KNOWLEDGE_BASE_ID": knowledge_base.attr_knowledge_base_id,
            "DATA_SOURCE_ID": data_source.attr_data_source_id,
        }
        # nessun layer: il boto3 del runtime Python 3.13 ha gia' i client bedrock-agent e bedrock-agent-runtime
        api_fn = self.function("Api", "api.handler", {
            **environment,
            "API_KEY_SECRET_ARN": api_key.secret_arn,
            "CHAT_MODEL": chat_profile.attr_inference_profile_arn,
            "CHAT_MODEL_NAME": CHAT_MODEL,
            "MAX_UPLOAD_MB": str(MAX_UPLOAD_MB),
        }, timeout=Duration.seconds(29))
        sync_fn = self.function("Sync", "sync.handler", environment, timeout=Duration.seconds(30))

        # Permessi minimi
        documents.grant_read_write(api_fn)
        documents.grant_delete(api_fn)
        api_key.grant_read(api_fn)
        api_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:Retrieve", "bedrock:StartIngestionJob", "bedrock:ListIngestionJobs",
                     "bedrock:ListKnowledgeBaseDocuments"],
            resources=[knowledge_base.attr_knowledge_base_arn]))
        # il profilo e, sotto, il profilo cross-region e il modello in ogni region europea
        api_fn.add_to_role_policy(iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=[
            chat_profile.attr_inference_profile_arn, chat_source,
            f"arn:aws:bedrock:*::foundation-model/{CHAT_MODEL.split('.', 1)[1]}"]))
        sync_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:StartIngestionJob"], resources=[knowledge_base.attr_knowledge_base_arn]))

        # La Knowledge Base non segue il bucket da sola: ogni file aggiunto o cancellato in uploads/ finisce in
        # una coda e la Lambda Sync avvia una sincronizzazione (incrementale) per tutto il gruppo di eventi.
        # Con una sincronizzazione gia' in corso la Lambda fallisce e i messaggi tornano visibili dopo 2 minuti
        sync_failed = sqs.Queue(self, "SyncFailed", queue_name=f"{NAME}-SyncFailed",
                                retention_period=Duration.days(14), enforce_ssl=True)
        sync_queue = sqs.Queue(
            self, "SyncQueue",
            queue_name=f"{NAME}-Sync",
            visibility_timeout=Duration.minutes(2),
            retention_period=Duration.days(1),
            enforce_ssl=True,
            # 30 tentativi a 2 minuti l'uno dall'altro: circa un'ora per aspettare la sincronizzazione in corso
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=30, queue=sync_failed),
        )
        for event_type in (s3.EventType.OBJECT_CREATED, s3.EventType.OBJECT_REMOVED):
            documents.add_event_notification(event_type, s3n.SqsDestination(sync_queue),
                                             s3.NotificationKeyFilter(prefix=DOCS_PREFIX))
        sync_fn.add_event_source(event_sources.SqsEventSource(
            sync_queue, batch_size=100, max_batching_window=Duration.seconds(20), max_concurrency=2))

        # API: tutte le richieste /api/* alla Lambda Api
        http_api = apigw.HttpApi(self, "HttpApi", api_name=f"{NAME}-HttpApi",
                                 description="API del RAG con Bedrock Knowledge Base")
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
            comment="RAG con Bedrock Knowledge Base",
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
        CfnOutput(self, "KnowledgeBaseId", value=knowledge_base.attr_knowledge_base_id)

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

    def function(self, name: str, handler: str, environment: dict, timeout: Duration) -> _lambda.Function:
        log_group = logs.LogGroup(self, f"{name}Logs", log_group_name=f"/{NAME}/{name}",
                                  retention=logs.RetentionDays.ONE_WEEK, removal_policy=RemovalPolicy.DESTROY)
        return _lambda.Function(
            self, name,
            function_name=f"{NAME}-{name}",
            runtime=_lambda.Runtime.PYTHON_3_13,
            architecture=_lambda.Architecture.X86_64,
            handler=handler,
            code=_lambda.Code.from_asset("lambda"),
            environment=environment,
            timeout=timeout,
            memory_size=256,
            log_group=log_group,
        )

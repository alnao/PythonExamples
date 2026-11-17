# AWS CDK - Esempi in Python

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

Esempi di infrastruttura AWS descritta con **AWS CDK v2 in Python**, quasi tutti versioni CDK degli esempi del repository [AwsCloudFormationExamples](https://github.com/alnao/AwsCloudFormationExamples). Ogni cartella è un progetto indipendente con il suo README (deploy, verifica, costi, pulizia), i test che sintetizzano lo stack in locale senza chiamare AWS e gli stessi file comuni: `tags.py` (tag standard), `naming.py` (nomi delle risorse) e, per gli esempi con una rete, `network.py` (VPC e subnet di default).

Tutti gli esempi usano il bootstrap dell'account con i nomi del repository, descritto in [bootstrap](./bootstrap/README.md):
```bash
cd AWS/CDK/<esempio>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit                                 # sintesi e test in locale, nessuna chiamata AWS
#../bootstrap/bootstrap.sh create eu-central-1    # una volta per region
cdk deploy                                        # stack aws-py-cdkXX
cdk destroy
```


## 📋 Elenco degli esempi

| # | Esempio | Servizi principali |
|---|---------|--------------------|
| 01 | [Bucket S3](./cdk01bucketS3/) | S3 |
| 02 | [Istanza EC2](./cdk02ec2/) | EC2, Session Manager |
| 03 | [Sito web statico su S3](./cdk03websiteS3/) | S3 website |
| 04 | [Sito statico con CloudFront](./cdk04cloudFront/) | CloudFront, S3 |
| 05 | [Funzione Lambda](./cdk05lambda/) | Lambda, CloudWatch Logs |
| 06 | [EventBridge](./cdk06eventBridge/) | EventBridge, Lambda, S3 |
| 07 | [Step Functions](./cdk07stepFunction/) | Step Functions, Lambda |
| 08 | [API Gateway con stage e alias](./cdk08apiGateway/) | API Gateway REST, Lambda |
| 09 | [API CRUD su DynamoDB](./cdk09dynamoApiCrud/) | API Gateway, Lambda, DynamoDB |
| 10 | [Lambda authorizer con JWT](./cdk10lambdaAuth/) | API Gateway, Lambda, Secrets Manager |
| 11 | [Database RDS e Aurora Serverless v2](./cdk11rds/) | RDS, Aurora |
| 12 | [Lambda Application S3 Utils](./cdk12lambdaApplicationS3Utils/) | S3, Lambda, Aurora, DynamoDB, API Gateway, CloudFront |
| 13 | [Job AWS Glue](./cdk13glueJob/) | Glue, S3 |
| 14 | [Glue crawler e job da S3 a RDS](./cdk14glueCrawlerRDS/) | Glue, RDS, Step Functions, EventBridge |
| 15 | [Coda SQS](./cdk15sqs/) | SQS, Lambda, API Gateway |
| 16 | [Topic SNS](./cdk16sns/) | SNS, Step Functions, Lambda |
| 17 | [Istanza EC2 con Elastic IP](./cdk17elasticIP/) | EC2, Elastic IP |
| 18 | [File system EFS con EC2](./cdk18efs/) | EFS, EC2 |
| 19 | [WordPress su una istanza EC2](./cdk19wordpressSingle/) | EC2, RDS, Elastic IP |
| 20 | [Auto Scaling group con load balancer](./cdk20autoScaling/) | Auto Scaling, ALB |
| 21 | [Auto Scaling group con WordPress](./cdk21autoScalingWordpress/) | Auto Scaling, ALB, EFS, RDS |
| 22 | [Allarmi CloudWatch](./cdk22cloudWatchAlarm/) | CloudWatch, SNS (sopra il 21) |
| 23 | [Repository ECR](./cdk23ecr/) | ECR |
| 24 | [Cluster ECS su EC2](./cdk24ecs/) | ECS, Auto Scaling, ALB |
| 25 | [VPC con endpoint e Client VPN](./cdk25vpcEndpoint/) | VPC, endpoint, Client VPN |
| 26 | [Blockchain con Lambda](./cdk26blockchainLambda/) | Lambda, DynamoDB, API Gateway, CloudFront |
| 27 | [Cluster EKS](./cdk27eks/) | EKS, RDS |
| 28 | [Pipeline CI/CD con CodePipeline](./cdk28codePipelineCICD/) | CodePipeline, CodeBuild, ECR, ECS Fargate, CloudFront |
| 29 | [API GraphQL con AppSync](./cdk29GraphQL/) | AppSync, DynamoDB, CloudFront |
| 30 | [WebSocket: gioco "indovina il numero"](./cdk30WebSocket/) | API Gateway WebSocket e HTTP, Lambda, DynamoDB |
| 31 | [Elastic Beanstalk con Docker](./cdk31ElasticBeanstalk/) | Elastic Beanstalk |
| 32 | [Wiki con S3 Vectors](./cdk32wikiS3Vector/) | S3 Vectors, Bedrock (embedding), Lambda |
| 33 | [Bedrock Serverless, Pocket RAG](./cdk33bedrockServerless/) | Bedrock, S3 Vectors, Lambda |
| 34 | [Bedrock Knowledge Base su S3 Vectors](./cdk34bedrockKnowledgeBase/) | Bedrock Knowledge Base, S3 Vectors, Lambda, SQS |
| – | [Bootstrap](./bootstrap/) | bootstrap CDK dell'account (bucket ed ECR `alnao-dev-cdk`) |


## 🔎 Cosa fa ogni esempio

- **[01 Bucket S3](./cdk01bucketS3/)**: un bucket S3 privato con versioning, cifratura e accesso solo in HTTPS. Le versioni precedenti dei file spariscono dopo 30 giorni e al destroy il bucket viene svuotato e cancellato.
- **[02 Istanza EC2](./cdk02ec2/)**: un'istanza Amazon Linux 2023 nella VPC di default, senza porte aperte, gestita con Session Manager. Disco e interfaccia di rete ricevono i tag da un launch template collegato all'istanza.
- **[03 Sito web statico su S3](./cdk03websiteS3/)**: un sito servito dall'endpoint website di S3, con le pagine della cartella `web/` caricate da CDK al deploy. L'endpoint website è solo HTTP, per l'HTTPS c'è il 04.
- **[04 Sito statico con CloudFront](./cdk04cloudFront/)**: CloudFront in HTTPS davanti a un bucket privato letto con Origin Access Control. A ogni deploy le pagine vengono ricaricate e la cache invalidata.
- **[05 Funzione Lambda](./cdk05lambda/)**: una Lambda Python 3.13 su ARM con il suo log group di 7 giorni. È l'esempio base per vedere come CDK impacchetta e pubblica il codice.
- **[06 EventBridge](./cdk06eventBridge/)**: due regole EventBridge che invocano una Lambda, una sui file caricati nella cartella `INPUT/` del bucket e una schedulata nei giorni feriali.
- **[07 Step Functions](./cdk07stepFunction/)**: una macchina a stati che avvia un job simulato con una Lambda, aspetta e ne controlla lo stato finché non termina o fallisce.
- **[08 API Gateway con stage e alias](./cdk08apiGateway/)**: un'API REST con gli stage `dev` e `prod`, ognuno collegato a un alias diverso della stessa Lambda con una stage variable.
- **[09 API CRUD su DynamoDB](./cdk09dynamoApiCrud/)**: create, read, update e delete degli item di una tabella DynamoDB, con una Lambda per operazione e permessi minimi per ognuna.
- **[10 Lambda authorizer con JWT](./cdk10lambdaAuth/)**: un'API protetta da un authorizer che verifica token JWT HS256, con il segreto generato in Secrets Manager. Uno script crea un token di prova.
- **[11 Database RDS e Aurora Serverless v2](./cdk11rds/)**: un'istanza RDS (MySQL, MariaDB o PostgreSQL) con la password in Secrets Manager e, a richiesta, un cluster Aurora Serverless v2 che va in pausa a 0 ACU con la Data API.
- **[12 Lambda Application S3 Utils](./cdk12lambdaApplicationS3Utils/)**: gli zip caricati su S3 vengono estratti, gli Excel convertiti in CSV e i CSV caricati in Aurora Serverless con la Data API. Ci sono anche log su DynamoDB, API REST, una pagina web su CloudFront, una scansione notturna del bucket e un invio SFTP facoltativo.
- **[13 Job AWS Glue](./cdk13glueJob/)**: un job Glue 5.0 (Spark) che legge un CSV di prova da S3 e lo riscrive in un'altra cartella con le righe ordinate.
- **[14 Glue crawler e job da S3 a RDS](./cdk14glueCrawlerRDS/)**: un CSV caricato in S3 avvia una Step Function che esegue un workflow Glue, con il crawler che aggiorna il Data Catalog e il job che scrive le righe in RDS MySQL.
- **[15 Coda SQS](./cdk15sqs/)**: una coda con dead-letter queue e due Lambda esposte da API Gateway, una che invia i messaggi e una che li legge e li cancella.
- **[16 Topic SNS](./cdk16sns/)**: una Step Function pubblica notifiche su un topic SNS, ricevute da una Lambda e, se indicata, da un indirizzo email.
- **[17 Istanza EC2 con Elastic IP](./cdk17elasticIP/)**: un'istanza con Apache e un Elastic IP associato a un'interfaccia di rete dello stack. L'indirizzo resta lo stesso anche dopo stop, start o sostituzione dell'istanza.
- **[18 File system EFS con EC2](./cdk18efs/)**: un'istanza monta un file system EFS cifrato come cartella del sito Apache. I file restano su EFS anche se l'istanza viene sostituita.
- **[19 WordPress su una istanza EC2](./cdk19wordpressSingle/)**: WordPress installato al primo avvio su un'istanza con Elastic IP, con il database su RDS MySQL e la password letta da Secrets Manager.
- **[20 Auto Scaling group con load balancer](./cdk20autoScaling/)**: istanze Apache in un Auto Scaling group dietro un Application Load Balancer, con scaling sulla CPU. Funziona nella VPC di default senza NAT gateway.
- **[21 Auto Scaling group con WordPress](./cdk21autoScalingWordpress/)**: WordPress su più istanze dietro un load balancer, con il codice condiviso su EFS e il database su RDS. Il primo server installa WordPress, gli altri lo trovano pronto.
- **[22 Allarmi CloudWatch](./cdk22cloudWatchAlarm/)**: estende il 21 con allarmi su CPU, server malati ed errori 5xx, step scaling, un topic SNS per le notifiche e una dashboard.
- **[23 Repository ECR](./cdk23ecr/)**: un repository per le immagini Docker con scansione al push, regole di ciclo di vita e svuotamento automatico al destroy.
- **[24 Cluster ECS su EC2](./cdk24ecs/)**: un cluster ECS con un capacity provider su Auto Scaling group che esegue l'API Flask del progetto Docker dietro un load balancer.
- **[25 VPC con endpoint e Client VPN](./cdk25vpcEndpoint/)**: una VPC completa con gli endpoint gateway di S3 e DynamoDB e i flow log, più un Client VPN endpoint facoltativo per entrare nella rete dal proprio PC. È l'unico esempio che crea una VPC propria.
- **[26 Blockchain con Lambda](./cdk26blockchainLambda/)**: una blockchain didattica con le transazioni in DynamoDB e il mining proof of work in una Lambda, con le API su API Gateway e una pagina web su CloudFront.
- **[27 Cluster EKS](./cdk27eks/)**: un cluster Kubernetes gestito con un node group e un database RDS MySQL, su cui si installa con `kubectl` un microservizio Spring Boot.
- **[28 Pipeline CI/CD con CodePipeline](./cdk28codePipelineCICD/)**: a ogni commit su GitHub, CodeBuild costruisce l'immagine del backend, la pipeline aggiorna un servizio ECS Fargate e pubblica il frontend su S3 dietro CloudFront.
- **[29 API GraphQL con AppSync](./cdk29GraphQL/)**: un'API GraphQL per una lista di note, con resolver VTL diretti su DynamoDB e una pagina web che si aggiorna da sola con le subscription.
- **[30 WebSocket](./cdk30WebSocket/)**: il gioco multigiocatore "indovina il numero" con API Gateway WebSocket e HTTP API, Lambda e DynamoDB. Le notifiche arrivano ai giocatori in tempo reale.
- **[31 Elastic Beanstalk con Docker](./cdk31ElasticBeanstalk/)**: un'applicazione Elastic Beanstalk che esegue un'immagine Docker dietro un load balancer. Elastic Beanstalk crea da solo istanze, Auto Scaling group e log.
- **[32 Wiki con S3 Vectors](./cdk32wikiS3Vector/)**: una wiki di file di testo con ricerca per significato, con embedding Titan e un indice S3 Vectors, senza un LLM che scrive risposte.
- **[33 Bedrock Serverless, Pocket RAG](./cdk33bedrockServerless/)**: un sistema RAG con Amazon Bedrock completamente serverless: si caricano documenti e si fanno domande, pagando solo l'uso.
- **[34 Bedrock Knowledge Base su S3 Vectors](./cdk34bedrockKnowledgeBase/)**: lo stesso RAG del 33, con divisione dei file ed embedding affidati a una Bedrock Knowledge Base. Le Lambda chiedono i brani più simili e scrivono la risposta con Nova Lite.


## 🏷️ Tag obbligatori

Ogni risorsa che accetta tag ha questi sei tag (convenzione del repository in `CLAUDE.md`). Li mette `tags.py` di ogni esempio, che `app.py` e i test applicano con `apply_tags(app)`.

| Tag | Valore | Esempio (cdk05lambda) |
|-----|--------|-----------------------|
| `Name` | nome della risorsa, `aws-py-cdkXX-<servizio>` (vedi sotto) | `aws-py-cdk05-hello` |
| `Environment` | `dev` | `dev` |
| `Project` | `Development.aws.py-CDK.<cartella>` | `Development.aws.py-CDK.cdk05lambda` |
| `Owner` | `AlNao` | `AlNao` |
| `CostCenter` | `dev` | `dev` |
| `ManagedBy` | `CDK` | `CDK` |

Oltre ai tag di primo livello:
- `tags.py` mette i tag anche sulle risorse che CDK crea da solo come `CfnResource` generiche (Lambda e ruoli di supporto) e sulle risorse che un launch template crea all'avvio (istanze, dischi, interfacce di rete). Il tag `Name` di un Auto Scaling group non passa alle istanze, che hanno il loro.
- ogni Lambda, comprese quelle di supporto di CDK, scrive in un log group dello stack con i tag e 7 giorni di scadenza, e il suo ruolo non può crearne altri. Così Lambda non lascia log group senza tag.
- ogni esempio ha il test `test_all_resources_tagged`, che controlla i tag di ogni risorsa del template, esclusi i tipi che CloudFormation non permette di taggare. Ci sono anche il test sui log group delle Lambda e `test_all_resources_named` per il tag `Name`.
- anche lo **stack CloudFormation** `aws-py-cdkXX` ha i tag standard, con `Name` uguale al nome dello stack (test `test_stack_tags`). CloudFormation copia i tag dello stack sulle risorse che li supportano, ma il tag scritto sulla risorsa vince: ogni risorsa mantiene il suo `Name`.
- non si possono taggare da CloudFormation le interfacce di rete gestite dai servizi (NAT, load balancer, RDS, EFS, Glue, Fargate) e gli IP pubblici assegnati all'avvio, che non sono risorse.

`Project` serve a filtrare i costi per esempio in Cost Explorer, dopo averlo attivato come *cost allocation tag*. Il bootstrap ha `Project=Development.aws.py-CDK.bootstrap`.


## 🔤 Convenzione dei nomi

Lo stack di ogni esempio si chiama **`aws-py-cdkXX`**, dove `XX` è il numero dell'esempio, e ogni risorsa si chiama **`aws-py-cdkXX-<servizio>`**, tutto minuscolo con i trattini, con il **tag `Name` uguale al nome**. `<servizio>` dice cosa fa la risorsa, per esempio `aws-py-cdk09-create-item`, `aws-py-cdk12-process-csv` o `aws-py-cdk21-load-balancer`.

Le regole stanno in `naming.py`, lo stesso file in ogni esempio:
- `PhysicalNames` è un aspect registrato da `apply_tags`. Dà il nome a tutte le risorse che possono averne uno a partire dall'id del costrutto CDK (`"CreateItem"` → `create-item`), comprese quelle che CDK crea da solo (ruoli, policy, Lambda di supporto, log group, security group). Rispetta la lunghezza massima di ogni tipo: se il nome è troppo lungo, lo accorcia e aggiunge un breve hash.
- `nome_risorsa(self, "servizio")` serve per i nomi scritti nel codice. È necessario quando una risorsa è citata per nome come stringa: connessioni e classificatori Glue, data source AppSync usate dai resolver, ARN costruiti a mano, URL nelle uscite.
- `check_template()` controlla il template sintetizzato nel test `test_all_resources_named` di ogni esempio. Verifica prefisso, minuscole, lunghezze, suffissi, tag `Name` uguale al nome e nomi doppi. Segnala anche un nome sostituito che resta citato come stringa da un'altra risorsa, che altrimenti farebbe fallire il deploy.

Eccezioni, imposte da AWS:

| Risorsa | Nome | Perché |
|---------|------|--------|
| Bucket S3 | `aws-py-cdkXX-<servizio>-<account>` | i nomi dei bucket sono unici in tutto AWS: l'id dell'account lo prende CDK dal profilo del deploy, non è un parametro |
| Ruoli e instance profile IAM | `aws-py-cdkXX-<servizio>-<region>` | i nomi IAM valgono per tutto l'account, non per region |
| Log group | `/aws/lambda/aws-py-cdkXX-<funzione>`, `/aws-glue/jobs/aws-py-cdkXX-…`, `/aws/vendedlogs/states/aws-py-cdkXX-…`, `/aws-py-cdkXX/<servizio>` | il percorso del servizio serve ai permessi e alle convenzioni di AWS; AppSync scrive solo in `/aws/appsync/apis/<id>` |
| Database del Glue Data Catalog, data source AppSync | `aws_py_cdkXX_<servizio>` | accettano solo lettere, numeri e `_` |
| Capacity provider ECS | `cp-aws-py-cdkXX-<servizio>` | il nome non può iniziare con `aws` |
| Risorse senza nome (istanze EC2, Elastic IP, interfacce di rete, EFS, VPC, CloudFront, stage delle API, …) | solo il tag `Name` `aws-py-cdkXX-<servizio>` | CloudFormation non ha una proprietà per il nome |

Nomi fissi significano che lo stesso esempio si può deployare **una sola volta per account e region** (in region diverse sì: per questo i ruoli IAM hanno la region nel nome). Inoltre CloudFormation non può sostituire una risorsa con nome fisso: se una modifica richiede la sostituzione, bisogna fare `cdk destroy` e un nuovo deploy. Il bootstrap (`alnao-dev-cdk`) è condiviso da tutti gli esempi e mantiene i suoi nomi.

Le risorse create a mano con la CLI, come indicato in alcuni README (certificati del 25, token GitHub del 28), seguono la stessa convenzione per il tag `Name` e hanno `ManagedBy=Sh`.


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Prima versione: elenco degli esempi con una descrizione breve, tag obbligatori e convenzione dei nomi aws-py-cdkXX-<servizio> |
| 2026-11-17 | Tag Name anche sugli stack CloudFormation (uguale al nome dello stack) |


# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.


# AWS CDK 14 - Glue crawler e job da S3 a RDS

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Caricamento automatico di file **CSV** da **S3** a un database **RDS MySQL** con **AWS Glue**: un file caricato avvia una **Step Function** che esegue un workflow Glue (**crawler** e poi **job**). Versione CDK in Python dell'esempio CloudFormation [Esempio14glueCrawlerRDS](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio14glueCrawlerRDS).

- **🪣 Bucket dello stack** con le notifiche EventBridge attive: un file `.csv` caricato in `INPUT/` genera un evento *Object Created*
- **🔀 Step Function** avviata dalla regola EventBridge: chiama direttamente Glue (`startWorkflowRun`, poi `getWorkflowRun` ogni 30 secondi, senza Lambda come nel CloudFormation) e termina con successo o errore in base all'esito del workflow; se un workflow è già in corso riprova dopo un minuto
- **🕷️ Crawler Glue** con un classificatore CSV (separatore `;`, intestazione presente) che aggiorna la tabella `input` del Data Catalog
- **⚙️ Job Glue 5.0** (Spark) che legge la tabella del catalogo e scrive le righe nella tabella `persone` di RDS tramite una connessione JDBC; il *job bookmark* fa leggere solo i file nuovi a ogni esecuzione
- **🗄️ RDS MySQL 8.4** `db.t4g.micro` cifrato nelle subnet indicate, raggiungibile solo dal security group di Glue; utente e password generati in Secrets Manager
- **🔌 Endpoint gateway S3** (gratuito) sulla tabella di routing indicata: la connessione JDBC fa lavorare Glue dentro la VPC e senza endpoint (o NAT) il job non legge S3
- **📋 Log** del job (`/aws-glue/jobs/aws-py-cdk14-job`) e della Step Function in log group dello stack con 7 giorni, cancellati al destroy


## 🔧 Architettura

```
aws s3 cp persone.csv s3://<bucket>/INPUT/ ── EventBridge (Object Created, INPUT/*.csv)
    └── Step Function aws-py-cdk14-runner
          ├── glue:startWorkflowRun ── workflow aws-py-cdk14-workflow
          │       ├── trigger ON_DEMAND ── crawler aws-py-cdk14-crawler ── Data Catalog: aws_py_cdk14_csv.input
          │       └── trigger CONDITIONAL (crawler SUCCEEDED) ── job aws-py-cdk14-job (Glue 5.0, bookmark)
          │                                                         └── connessione JDBC (VPC) ── RDS MySQL mydb.persone
          └── ogni 30 s glue:getWorkflowRun ── COMPLETED senza errori → Succeeded, altrimenti Failed
subnet della connessione ── endpoint gateway S3 (route table) ── bucket
```

```
├── app.py                              # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk14glue_crawler_rds/
│   ├── cdk14glue_crawler_rds_stack.py  # 🏗️ bucket, RDS, Glue (catalogo, crawler, connessione, job, workflow), Step Function, regola
│   ├── naming.py                       # 🏷️ nomi aws-py-cdk14-<servizio> e tag Name di ogni risorsa
│   └── tags.py                         # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── glue/csv_to_rds.py                  # ⚙️ script Spark del job
├── data/persone.csv                    # 📄 CSV di prova
├── tests/unit/                         # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk14glueCrawlerRDS/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
# endpoint gateway S3 gia' presenti: se ce n'e' uno sulla tabella di routing della VPC di default, aggiungere --parameters routetableid=""
aws ec2 describe-vpc-endpoints --region $AWS_REGION --filters Name=service-name,Values=com.amazonaws.$AWS_REGION.s3 --query "VpcEndpoints[].[VpcId,VpcEndpointType,RouteTableIds]" --output table
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid`, `subnetid1`, `subnetaz1` (zona della subnet 1), `subnetid2` e `routetableid` (tabella di routing della subnet 1, per l'endpoint gateway S3), che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Il database impiega circa 10 minuti a essere creato.

Verifica (crawler e job insieme impiegano qualche minuto):
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk14 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws s3 cp data/persone.csv s3://$(out BucketName)/INPUT/persone.csv
aws stepfunctions list-executions --state-machine-arn $(out StateMachineArn) --query "executions[].[name,status,startDate]" --output table
aws glue get-workflow-runs --name $(out WorkflowName) --query "Runs[].[Status,Statistics.SucceededActions,Statistics.FailedActions]" --output table
aws glue get-job-runs --job-name $(out JobName) --query "JobRuns[].[StartedOn,JobRunState,ErrorMessage]" --output table
aws logs tail /aws-glue/jobs/$(out JobName) --since 30m
```
Il database non è raggiungibile da Internet: per controllare la tabella `persone` si può usare un'istanza o Session Manager nella stessa VPC, oppure (più semplice) rilanciare il caricamento di un secondo file e verificare che il job bookmark legga solo quello.

**Tag**: bucket, RDS (istanza, subnet group, security group, segreto), crawler, job, workflow, trigger, endpoint S3, Step Function, regola EventBridge, ruoli, log group e Lambda di supporto di CDK hanno i tag standard (`Project=Development.aws.py-CDK.cdk14glueCrawlerRDS`, `ManagedBy=CDK`); database e classificatore del Data Catalog, connessione Glue, regole dei security group e policy non accettano tag. Le interfacce di rete che Glue e RDS creano nelle subnet sono gestite dai servizi e non hanno tag; i log del crawler finiscono nel log group comune `/aws-glue/crawlers`. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk14-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| RDS MySQL `db.t4g.micro` | ~0,018 $/ora | ~13 $ |
| Storage RDS gp3 | 20 GB × ~0,13 $/GB | ~2,60 $ |
| Secrets Manager | 0,40 $ per segreto | 0,40 $ |
| Glue crawler | 0,44 $ per DPU-ora, minimo 10 minuti per esecuzione | ~0,07 $ per caricamento |
| Glue job | 0,44 $ per DPU-ora, 2 DPU, minimo 1 minuto | ~0,02-0,03 $ per caricamento |
| Step Functions, EventBridge, S3, endpoint gateway S3 | a consumo / gratuiti | ~0 $ |
| **Totale fisso** | | **~16 $** |

La voce principale è il database, che si paga a ore anche quando non si caricano file.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk14glueCrawlerRDS --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il database viene cancellato senza snapshot finale e senza backup (`RemovalPolicy.DESTROY`, retention 0), il bucket svuotato e cancellato, l'endpoint S3 rimosso dalla tabella di routing
- il segreto del database resta *in attesa di cancellazione* per 7 giorni (non si paga)
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔐 **Credenziali da Secrets Manager** nella connessione Glue (`SECRET_ID`) invece di copiarle nelle proprietà della connessione
- ☁️ **Aurora Serverless v2** con pausa a 0 ACU al posto dell'istanza sempre accesa (vedi cdk11)
- 🔔 **Notifica SNS** quando il workflow fallisce


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Aggiunti README e test dello stack (prima mancavano), log group del job Glue dello stack con tag e 7 giorni (--continuous-log-logGroup) |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk14-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk14, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named; database del Data Catalog aws_py_cdk14_csv (solo _), log group della Step Function /aws/vendedlogs/states/aws-py-cdk14-runner |
| 2026-11-17 | Tag Name aws-py-cdk14 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


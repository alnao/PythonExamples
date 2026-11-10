# AWS CDK 31 - Elastic Beanstalk con Docker

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'applicazione **AWS Elastic Beanstalk** che esegue un'immagine **Docker** su istanze EC2 dietro un **Application Load Balancer**: Elastic Beanstalk crea da solo istanze, Auto Scaling group, load balancer, security group e log. Versione CDK in Python dell'esempio CloudFormation [Esempio31ElasticBeanstalk](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio31ElasticBeanstalk), che eseguiva l'immagine `pathsgames/pathsgames` (porta 8042, stato su `/api/echo/status`).

- **📦 Source bundle automatico**: la cartella [app](./app/) con il solo `Dockerrun.aws.json` (immagine e porta del container) diventa uno zip caricato da CDK nel bucket del bootstrap; nell'esempio CloudFormation bucket e chiave del bundle erano parametri da preparare a mano
- **🐳 Piattaforma Docker su Amazon Linux 2023**: nginx sulle istanze riceve il traffico sulla porta 80 e lo inoltra al container sulla porta 8042
- **⚖️ Ambiente LoadBalanced** con Application Load Balancer, da 1 a 2 istanze `t3.micro`, controllo di salute su `/api/echo/status`
- **🩺 Health reporting enhanced** e **log delle istanze in CloudWatch** (7 giorni, cancellati con l'ambiente)
- **🔐 Istanze** con IMDSv2 obbligatorio, disco gp3 e Session Manager al posto di SSH
- **🗂️ Ciclo di vita delle versioni**: al massimo 10 versioni registrate nell'applicazione

Per cambiare immagine basta modificare `app/Dockerrun.aws.json` (nome e porta) e, se serve, `HEALTH_PATH` nello stack, poi `cdk deploy`: CDK carica un nuovo bundle, registra una nuova versione ed Elastic Beanstalk la installa.

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio31) | CDK (cdk31) |
|---|---|---|
| Source bundle | parametri `SourceBundleS3Bucket` e `SourceBundleS3Key`, zip da caricare a mano | asset CDK della cartella `app/` |
| Controllo di salute | opzioni `aws:elb:healthcheck` (del Classic Load Balancer) e porta 8042 | Application Load Balancer, `process:default` sulla porta 80 di nginx |
| Ruoli | `AWSElasticBeanstalkService` (deprecata), web e worker tier | `AWSElasticBeanstalkEnhancedHealth` e managed updates; web tier, Docker e Session Manager |
| Log | sulle istanze | anche in CloudWatch, 7 giorni |
| Piattaforma | parametro con default vuoto | parametro obbligatorio, nome letto con la CLI |


## 🔧 Architettura

```
cdk deploy ── zip di app/ (Dockerrun.aws.json) ── bucket alnao-dev-cdk ── versione dell'applicazione
Elastic Beanstalk <stack>-app
└── ambiente <stack>-env (VPC di default)
    ├── Application Load Balancer :80 ── controllo /api/echo/status
    └── Auto Scaling group 1-2 × t3.micro (Docker su AL2023)
            nginx :80 ── container pathsgames/pathsgames :8042
            log ── CloudWatch /aws/elasticbeanstalk/<stack>-env/... (7 giorni)
```

```
├── app.py                              # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── app/Dockerrun.aws.json              # 🐳 il source bundle: immagine e porta del container
├── docker-compose.yml                  # 🧪 prova in locale della stessa immagine
├── cdk31elastic_beanstalk/
│   ├── cdk31elastic_beanstalk_stack.py # 🏗️ ruoli, applicazione, versione, ambiente
│   └── tags.py                         # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                         # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, la VPC di default nella region.

```bash
cd PythonExamples/AWS/CDK/cdk31ElasticBeanstalk/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

docker compose up      # facoltativo: prova in locale su http://localhost:8042/api/echo/status

REGION=eu-central-1
# nome esatto della piattaforma Docker più recente (cambia a ogni aggiornamento di AWS)
STACK_NAME=$(aws elasticbeanstalk list-available-solution-stacks --region $REGION \
  --query "SolutionStacks[?contains(@, 'Amazon Linux 2023') && ends_with(@, 'running Docker')] | [0]" --output text)
echo $STACK_NAME

#../bootstrap/bootstrap.sh create $REGION
cdk deploy --parameters solutionstack="$STACK_NAME"
```
Parametro facoltativo: `instancetype` (default `t3.micro`). Il deploy dura circa 10 minuti (creazione dell'ambiente). Al termine `cdk deploy` stampa `ApplicationName`, `EnvironmentName` ed `EnvironmentURL`.

Comandi utili:
```bash
ENV=Cdk31ElasticBeanstalkStack-env
aws elasticbeanstalk describe-environments --environment-names $ENV --query "Environments[0].[Status,Health,HealthStatus,CNAME,VersionLabel]"
aws elasticbeanstalk describe-environment-health --environment-name $ENV --attribute-names All
aws elasticbeanstalk describe-events --environment-name $ENV --max-items 20 --query "Events[].[EventDate,Severity,Message]" --output table
aws elasticbeanstalk describe-application-versions --application-name Cdk31ElasticBeanstalkStack-app --query "ApplicationVersions[].[VersionLabel,DateCreated,Status]" --output table
aws elasticbeanstalk request-environment-info --environment-name $ENV --info-type tail   # poi retrieve-environment-info
aws logs describe-log-groups --log-group-name-prefix /aws/elasticbeanstalk/$ENV
```
Con la [EB CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html) (`pip install awsebcli`) si possono anche aprire i log e una sessione sulle istanze, ma l'ambiente resta gestito dallo stack: le modifiche vanno fatte con `cdk deploy`.

**Tag**: l'ambiente e i ruoli hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk31ElasticBeanstalk`, `ManagedBy=CDK`), ed Elastic Beanstalk li copia sulle risorse che crea (istanze, volumi, Auto Scaling group, load balancer, security group, stack CloudFormation interno `awseb-...`). Non hanno tag l'applicazione, la versione e l'instance profile, che CloudFormation non permette di taggare, e i log group creati da Elastic Beanstalk.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS. Elastic Beanstalk non ha un costo proprio: si pagano le risorse che crea, che hanno costi fissi orari anche senza traffico.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| Application Load Balancer | 0,027 $/ora + LCU (traffico minimo) | ~20 $ |
| IP pubblici | load balancer (2) e istanza (1) nella VPC di default, 0,005 $/ora ciascuno | ~11 $ |
| EC2 `t3.micro` | 1-2 istanze × 0,012 $/ora | 9-18 $ |
| EBS gp3 | 8 GB per istanza × 0,095 $/GB | ~1 $ |
| S3 (bundle nel bucket del bootstrap) | pochi KB | ~0 $ |
| CloudWatch Logs | pochi MB, 7 giorni | < 0,10 $ |
| **Totale** | | **~41-50 $** |

Per una prova economica si può usare un ambiente `SingleInstance` (senza load balancer, opzione `EnvironmentType`): resta solo l'istanza con il suo IP.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk31ElasticBeanstalk --query "ResourceTagMappingList[].ResourceARN" --output text
```
- la cancellazione dell'ambiente termina istanze, load balancer e Auto Scaling group e cancella lo stack interno `awseb-...`; i log group in CloudWatch si cancellano con l'ambiente (`DeleteOnTerminate`)
- Elastic Beanstalk crea anche un bucket `elasticbeanstalk-<region>-<account>` (con i log e le configurazioni salvate) che non fa parte dello stack e resta: se non serve ad altri ambienti si svuota e si cancella a mano
- i bundle restano nel bucket del bootstrap `alnao-dev-cdk`, condiviso con gli altri progetti CDK
- il bootstrap resta: `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔁 **docker-compose.yml** nel bundle per eseguire più container (per esempio applicazione e Redis)
- 🔒 **HTTPS** sul load balancer con un certificato ACM e un dominio Route 53
- 🌐 **VPC dedicata** (opzioni `aws:ec2:vpc`) con istanze in subnet private
- 🚦 **Deploy immutabili** o **traffic splitting** e **managed platform updates** in una finestra di manutenzione


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


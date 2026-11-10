# AWS CDK 24 - Cluster ECS su EC2

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un cluster **Amazon ECS** con istanze EC2 che esegue un'immagine Docker dietro un **Application Load Balancer**. Versione CDK in Python dell'esempio CloudFormation [Esempio24ecs](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio24ecs), che usava i template annidati di *ecs-refarch-cloudformation* per VPC, security group e load balancer.

- **🌐 VPC nuova** `10.184.0.0/16` con due subnet pubbliche (load balancer, NAT) e due private (istanze), un solo NAT gateway per contenere i costi
- **🖥️ Istanze ECS-optimized** Amazon Linux 2023 (`t3.micro`) in un Auto Scaling group collegato al cluster come **capacity provider**: ECS aggiunge e toglie istanze (da 1 a 2) secondo i task da eseguire, e prima di spegnerne una sposta i task (*managed draining*)
- **🐳 Servizio con 2 task** dell'API Flask [Docker/03ApiPersoneNoDb](../../../Docker/03ApiPersoneNoDb/) (porta 5001), rete *bridge* con porte dell'host dinamiche: più task sulla stessa istanza
- **🔀 Load balancer**: `/persone` e `/test` vanno al servizio, ogni altro percorso riceve un 404 fisso; controllo di salute su `/test`
- **🛟 Circuit breaker**: un deploy con task che non partono torna da solo alla versione precedente
- **📦 Immagine**: costruita da CDK al deploy e caricata nel repository ECR del bootstrap; con `-c ecr_repository=<nome>` il servizio usa l'immagine `:latest` di un repository esistente, per esempio quello del [cdk23ecr](../cdk23ecr/) (come faceva l'esempio CloudFormation con l'esempio 23)

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio24) | CDK (cdk24) |
|---|---|---|
| VPC, security group, ALB | template annidati di *ecs-refarch-cloudformation* | costrutti CDK, regole dei security group calcolate da CDK |
| Istanze | Auto Scaling group a dimensione fissa con `cfn-signal` | capacity provider con *managed scaling* e *managed draining* |
| Porta del container | 80 (andava cambiata in `app.py` e nel `Dockerfile`) | 5001 come nel progetto Docker, porta dell'host dinamica |
| Immagine | caricata a mano nel repository dell'esempio 23 | costruita da CDK, oppure da un repository esistente |
| Ruolo del servizio | ruolo IAM `ecs-service-...` con policy inline | ruolo collegato al servizio ECS (creato da AWS) |
| Log | log group con 365 giorni | log group `/ecs/<stack>` con 7 giorni |


## 🔧 Architettura

```
Internet ── ALB (subnet pubbliche) ──┬── /persone, /persone/*, /test ── target group (porte dinamiche)
                                     └── altri percorsi: 404 fisso                │
                                                                                  ▼
Cluster ECS ── capacity provider ── Auto Scaling group (subnet private, 1-2 × t3.micro)
                                         └── servizio api-persone: 2 task bridge, container 5001 → porta host 32768-65535
Istanze ── NAT gateway ── Internet (immagine da ECR, agente ECS)
Task ── log group /ecs/<stack> (7 giorni)
```

```
├── app.py                 # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk24ecs/
│   ├── cdk24ecs_stack.py  # 🏗️ VPC, cluster, capacity provider, task definition, servizio, ALB
│   └── tags.py            # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/            # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, **Docker** in locale (per costruire l'immagine).

```bash
cd PythonExamples/AWS/CDK/cdk24ecs/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy                                        # immagine costruita da Docker/03ApiPersoneNoDb
cdk deploy -c ecr_repository=cdk23ecr-repository  # immagine :latest caricata nel repository del cdk23
```
Il deploy dura circa 10 minuti. Al termine `cdk deploy` stampa `ServiceUrl`, `ClusterName`, `ServiceName` e `LogGroupName`.

Prova del servizio:
```bash
URL=$(aws cloudformation describe-stacks --stack-name Cdk24EcsStack --query "Stacks[0].Outputs[?OutputKey=='ServiceUrl'].OutputValue" --output text)
curl $URL
curl -X POST $URL -H "Content-Type: application/json" -d '{"cognome": "Nao", "nome": "Andrea"}'
curl $URL      # la persona aggiunta compare solo se la richiesta arriva allo stesso task: ogni task ha la sua lista in memoria
```

Comandi utili:
```bash
CLUSTER=Cdk24EcsStack
aws ecs list-services --cluster $CLUSTER
aws ecs describe-services --cluster $CLUSTER --services api-persone --query "services[0].[status,runningCount,desiredCount,deployments[0].rolloutState]"
aws ecs list-tasks --cluster $CLUSTER
aws ecs list-container-instances --cluster $CLUSTER
aws ecs describe-capacity-providers --query "capacityProviders[?contains(name,'Cdk24')].[name,autoScalingGroupProvider.managedScaling]"
aws ecs update-service --cluster $CLUSTER --service api-persone --desired-count 3   # il capacity provider aggiunge un'istanza se serve
aws logs tail /ecs/Cdk24EcsStack --follow
```

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk24ecs`, `ManagedBy=CDK`); il servizio propaga i tag ai task (`PropagateTags=SERVICE`), l'Auto Scaling group alle istanze. Non hanno tag solo i tipi che CloudFormation non permette di taggare: rotte, associazioni delle subnet, attacco dell'Internet gateway, associazione cluster-capacity provider, listener e regole, instance profile, policy IAM inline, regole dei security group.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS. Lo stack ha costi fissi orari anche senza traffico.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| NAT gateway | 0,052 $/ora + 0,052 $/GB elaborato | ~38 $ |
| Application Load Balancer | 0,027 $/ora + LCU (traffico minimo) | ~20 $ |
| IP pubblici | 3 × 0,005 $/ora (2 del load balancer, 1 del NAT) | ~11 $ |
| EC2 `t3.micro` | 1-2 istanze × 0,012 $/ora | 9-18 $ |
| EBS | 30 GB gp3 per istanza (default dell'AMI ECS) × 0,095 $/GB | 3-6 $ |
| ECR (repository del bootstrap) | ~400 MB × 0,10 $/GB | 0,04 $ |
| CloudWatch Logs | pochi MB, 7 giorni | < 0,10 $ |
| **Totale** | | **~80-90 $** |

ECS con istanze EC2 non ha un costo proprio: si pagano le istanze. Il NAT è la voce più grande: per una prova breve va bene, per tenere lo stack acceso conviene mettere le istanze nelle subnet pubbliche senza NAT, oppure passare a Fargate (vedi il cdk28).


## 🧹 Pulizia

```bash
cdk destroy
# le revisioni della task definition restano INACTIVE dopo il destroy
aws ecs list-task-definitions --family-prefix Cdk24EcsStack-api-persone --status INACTIVE --query taskDefinitionArns --output text
aws ecs delete-task-definitions --task-definitions <arn>
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk24ecs --query "ResourceTagMappingList[].ResourceARN" --output text
```
- servizio, task, istanze, NAT, load balancer e log group si cancellano con lo stack
- l'immagine costruita da CDK resta nel repository ECR del bootstrap `alnao-dev-cdk`, condiviso con gli altri progetti: si cancella con il bootstrap (`../bootstrap/bootstrap.sh destroy <region>`) o a mano con `aws ecr batch-delete-image --repository-name alnao-dev-cdk --image-ids imageTag=<hash>`
- con `-c ecr_repository=...` l'immagine resta nel repository del cdk23, che va pulito con il suo stack


## 🚀 Sviluppi Futuri
- 📈 **Auto scaling dei task** (`service.auto_scale_task_count`) sulla CPU o sulle richieste del load balancer
- 🧩 **Rete awsvpc** con un security group per task e **Service Connect** per far parlare più servizi
- 🔒 **HTTPS** sul load balancer con un certificato ACM


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


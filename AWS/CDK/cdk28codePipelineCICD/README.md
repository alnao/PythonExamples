# AWS CDK 28 - Pipeline CI/CD con CodePipeline

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una pipeline **AWS CodePipeline** che a ogni commit su GitHub costruisce l'immagine Docker del backend con **CodeBuild**, la carica su **ECR**, aggiorna un servizio **ECS Fargate** e pubblica il frontend su **S3** dietro **CloudFront**. Versione CDK in Python dell'esempio CloudFormation [Esempio28codePipelineCICD](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio28codePipelineCICD), che costruiva il backend Java Spring Boot e il frontend del repository *JavaSpringBootExample*: qui il backend è l'API Flask [Docker/03ApiPersoneNoDb](../../../Docker/03ApiPersoneNoDb/) e il frontend è la cartella [frontend](./frontend/) di questo esempio, entrambi nel repository *PythonExamples*.

- **🔁 Pipeline V2** in tre fasi: *Source* (GitHub), *Build* (backend e frontend in parallelo), *Deploy* (ECS e S3 in parallelo)
- **🐳 Build del backend**: `docker build` in CodeBuild (modalità *privileged*), immagine con il tag del commit e `latest` nel repository ECR dello stack; l'immagine base arriva dalla galleria pubblica di ECR per evitare i limiti di download di Docker Hub
- **🚀 Deploy su Fargate**: l'azione ECS registra una nuova revisione della task definition con l'immagine del commit e aggiorna il servizio, con *circuit breaker* che torna indietro se i task non partono
- **🌐 Un solo dominio CloudFront**: `/` dal bucket S3 privato, `/persone*` e `/test` dal load balancer, quindi il frontend chiama le API senza CORS
- **🔑 Sorgente GitHub** con il token personale in Secrets Manager (secret `github/codepipeline/token`, come l'esempio CloudFormation) oppure con una connessione **AWS CodeConnections** (`-c connection_arn=...`)
- **💸 Senza NAT**: VPC con sole subnet pubbliche, il task Fargate ha un IP pubblico

Al primo `cdk deploy` il servizio parte con un'immagine costruita da CDK dalla cartella locale (così lo stack è subito funzionante); appena creata, la pipeline parte da sola e la sostituisce con quella costruita da GitHub.

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio28) | CDK (cdk28) |
|---|---|---|
| Applicazione | Spring Boot (Maven) e frontend del repository JavaSpringBootExample | Flask (`Docker/03ApiPersoneNoDb`) e frontend di questo esempio |
| Permessi | `PowerUserAccess` e `AdministratorAccess` sui ruoli | ruoli con i soli permessi delle azioni, calcolati da CDK |
| Frontend | bucket con sito web pubblico, API su un altro dominio | bucket privato e CloudFront con le API sullo stesso dominio |
| Primo avvio | il servizio aspetta un'immagine che ancora non c'è | immagine iniziale costruita da CDK |
| Sorgente | solo token GitHub | token GitHub oppure CodeConnections |
| Log e artefatti | log group 7 giorni, bucket degli artefatti da svuotare a mano | log group 7 giorni, bucket con scadenza a 30 giorni svuotato al destroy |
| Dominio personalizzato | record Route 53 facoltativo | non incluso (vedi sviluppi futuri) |


## 🔧 Architettura

```
GitHub alnao/PythonExamples (master) ── CodePipeline V2
   Source ── SourceCode (tutto il repository)
   Build  ──┬── CodeBuild backend: docker build Docker/03ApiPersoneNoDb ── push su ECR ── imagedefinitions.json
            └── CodeBuild frontend: file di AWS/CDK/cdk28codePipelineCICD/frontend
   Deploy ──┬── ECS: nuova task definition ── servizio Fargate "backend"
            └── S3: copia del frontend (Cache-Control no-cache)

browser ── CloudFront ──┬── /, /index.html, /app.js ── bucket S3 privato (Origin Access Control)
                        └── /persone*, /test ── ALB :80 ── task Fargate :5001 (subnet pubblica, IP pubblico)
```

```
├── app.py                                # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk28code_pipeline_cicd/
│   ├── cdk28code_pipeline_cicd_stack.py  # 🏗️ VPC, ECR, ECS Fargate, ALB, CloudFront, CodeBuild, CodePipeline
│   └── tags.py                           # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── frontend/                             # 🌐 index.html e app.js, pubblicati dalla pipeline
├── tests/unit/                           # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, **Docker** in locale (immagine iniziale), il repository su GitHub con la cartella `frontend` di questo esempio già presente sul branch (la pipeline la cerca lì).

1. **Accesso a GitHub**, una delle due strade:
   - token personale *classic* di GitHub (scope `repo`; per un repository pubblico basta `public_repo`) in Secrets Manager, come lo script `create_github_secret.sh` dell'esempio CloudFormation:
     ```bash
     REGION=eu-central-1
     TAGS="Key=Name,Value=aws-py-CDK.cdk28codePipelineCICD Key=Environment,Value=dev Key=Project,Value=Development.aws.py-CDK.cdk28codePipelineCICD Key=Owner,Value=AlNao Key=CostCenter,Value=dev Key=ManagedBy,Value=Sh"
     read -s -p "GitHub token: " GITHUB_TOKEN; echo
     aws secretsmanager create-secret --name github/codepipeline/token --secret-string "$GITHUB_TOKEN" --tags $TAGS --region $REGION
     ```
   - oppure una connessione CodeConnections creata dalla console (*Developer Tools* > *Settings* > *Connections*, va autorizzata su GitHub) e passata con `-c connection_arn=arn:aws:codeconnections:...`
2. **Deploy**:
   ```bash
   cd PythonExamples/AWS/CDK/cdk28codePipelineCICD/
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   pytest tests/unit

   #../bootstrap/bootstrap.sh create eu-central-1
   cdk deploy
   # altro repository o branch (stessa struttura di cartelle, o cartelle indicate)
   cdk deploy -c github_owner=<utente> -c github_repo=<repo> -c github_branch=<branch> \
              -c backend_dir=Docker/03ApiPersoneNoDb -c frontend_dir=AWS/CDK/cdk28codePipelineCICD/frontend
   ```

Al termine `cdk deploy` stampa `SiteUrl`, `BackendUrl`, `RepositoryUri` e `PipelineUrl`. La pipeline parte da sola dopo la creazione (5-8 minuti); poi ogni commit sul branch la fa ripartire (controllo periodico del repository con il token, evento immediato con CodeConnections).

Prova:
```bash
SITE=$(aws cloudformation describe-stacks --stack-name Cdk28CodePipelineCicdStack --query "Stacks[0].Outputs[?OutputKey=='SiteUrl'].OutputValue" --output text)
curl $SITE/test
curl $SITE/persone
curl -X POST $SITE/persone -H "Content-Type: application/json" -d '{"nome": "Andrea", "cognome": "Nao"}'
```

Comandi utili:
```bash
PIPELINE=Cdk28CodePipelineCicdStack-pipeline
aws codepipeline start-pipeline-execution --name $PIPELINE           # esecuzione manuale
aws codepipeline get-pipeline-state --name $PIPELINE --query "stageStates[].[stageName,latestExecution.status]" --output table
aws codepipeline list-pipeline-executions --pipeline-name $PIPELINE --max-items 5
aws logs tail /aws/codebuild/Cdk28CodePipelineCicdStack-backend --since 1h
aws ecs describe-services --cluster Cdk28CodePipelineCicdStack --services backend --query "services[0].[taskDefinition,runningCount,deployments[0].rolloutState]"
```

Nota: un nuovo `cdk deploy` riporta il servizio all'immagine costruita da CDK (la task definition dello stack); la pipeline successiva rimette quella del commit. Per evitarlo si può rilanciare la pipeline subito dopo il deploy.

**Tag**: tutte le risorse dello stack hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk28codePipelineCICD`, `ManagedBy=CDK`); il servizio propaga i tag ai task. Non hanno tag solo i tipi che CloudFormation non permette di taggare: rotte, associazioni delle subnet, attacco dell'Internet gateway, regole dei security group, listener, OAC, policy IAM inline, policy dei bucket. Il secret del token è creato con il comando sopra (`ManagedBy=Sh`); le revisioni della task definition registrate dalla pipeline non hanno tag.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| Application Load Balancer | 0,027 $/ora + LCU (traffico minimo) | ~20 $ |
| IP pubblici | 3 × 0,005 $/ora (2 del load balancer, 1 del task) | ~11 $ |
| ECS Fargate | 1 task da 0,25 vCPU e 0,5 GB: 0,0466 × 0,25 + 0,0051 × 0,5 $/ora | ~10 $ |
| CodePipeline V2 | 0,002 $ per minuto di azione, ~5 minuti per esecuzione | ~0,01 $ per commit |
| CodeBuild | `general1.small` ~0,006 $/minuto, ~4 minuti per esecuzione | ~0,03 $ per commit |
| ECR | al massimo 10 immagini da ~400 MB × 0,10 $/GB | < 0,40 $ |
| S3 (sito, artefatti) e CloudFront | pochi MB, dentro il free tier | ~0 $ |
| Secrets Manager | 1 segreto (token GitHub) × 0,40 $ | 0,40 $ |
| CloudWatch Logs | pochi MB, 7 giorni | < 0,10 $ |
| **Totale** | | **~42 $ + pochi centesimi per commit** |

Il costo fisso è quasi tutto load balancer, IP pubblici e Fargate: la pipeline in sé costa centesimi.


## 🧹 Pulizia

```bash
cdk destroy
# revisioni della task definition registrate dalla pipeline (restano INACTIVE)
aws ecs list-task-definitions --family-prefix Cdk28CodePipelineCicdStack-backend --query taskDefinitionArns --output text
aws ecs deregister-task-definition --task-definition <arn>   # solo quelle ancora ACTIVE
aws ecs delete-task-definitions --task-definitions <arn>
# token GitHub, se creato solo per questo esempio
aws secretsmanager delete-secret --secret-id github/codepipeline/token --force-delete-without-recovery
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk28codePipelineCICD --query "ResourceTagMappingList[].ResourceARN" --output text
```
- repository ECR (con le immagini), bucket del sito e degli artefatti (svuotati da CDK), log group, pipeline e progetti CodeBuild si cancellano con lo stack
- l'immagine iniziale costruita da CDK resta nel repository ECR del bootstrap `alnao-dev-cdk`, condiviso con gli altri progetti
- le Lambda di supporto di CDK (svuotamento dei bucket, regole del security group di default) scrivono in log group creati da Lambda, senza tag e non cancellati dallo stack: `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/Cdk28CodePipelineCicdStack` e `aws logs delete-log-group --log-group-name <nome>`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🎯 **Trigger con filtro sui percorsi** (pipeline V2 con CodeConnections): ripartire solo quando cambiano `Docker/03ApiPersoneNoDb` o la cartella `frontend`
- 🧪 **Fase di test** (pytest o Robot Framework) prima del deploy e **approvazione manuale** per un ambiente di produzione
- 🔵🟢 **Deploy blue/green** con CodeDeploy al posto del rolling update di ECS
- 🔒 **Load balancer raggiungibile solo da CloudFront** (prefix list `com.amazonaws.global.cloudfront.origin-facing`) e **dominio personalizzato** con ACM e Route 53


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


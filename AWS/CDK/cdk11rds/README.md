# AWS CDK 11 - Database RDS e Aurora Serverless v2

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un database relazionale gestito con **Amazon RDS** e, se richiesto, un cluster **Aurora MySQL Serverless v2**. Versione CDK in Python dell'esempio CloudFormation [Esempio11rds](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio11rds), che creava sempre entrambi.

- **🗄️ Istanza RDS** `db.t4g.micro` con disco gp3 cifrato da 20 GB: **MySQL 8.4** per default, oppure **MariaDB 11.8** o **PostgreSQL 17** con `-c engine=mariadb` / `-c engine=postgres`
- **🔑 Credenziali in Secrets Manager**: utente `alnao` e password generata (senza caratteri che disturbano gli URL e la shell); nessuna password nei parametri o nel template
- **🛡️ Security group** con la sola porta del database (3306 o 5432) aperta verso la rete indicata, per default `172.31.0.0/16` (la VPC di default); il database non è pubblico
- **☁️ Aurora Serverless v2 facoltativo** (`-c aurora=true`): cluster Aurora MySQL che scala da **0** a 2 ACU e **va in pausa** dopo 5 minuti senza connessioni (si paga solo lo storage), con la **Data API** per fare query dalla CLI senza bisogno di rete verso il database
- **🧹 Destroy pulito**: niente snapshot finale e niente backup automatici rimasti (nell'esempio CloudFormation andavano cancellati a mano)

| | CloudFormation (Esempio11) | CDK (cdk11) |
|---|---|---|
| Database creati | istanza RDS e cluster Aurora, sempre | istanza RDS; Aurora solo con `-c aurora=true` |
| Motore | parametro `EngineRDS` | context `engine` (mysql, mariadb, postgres) con versioni fissate |
| Aurora | Serverless v2 da 1 a 2 ACU, sempre acceso | da 0 a 2 ACU con pausa automatica, Data API |
| Accesso | porta 3306 da `SSHLocation` (default `0.0.0.0/0`) | porta del motore dalla rete `allowedcidr` (default VPC di default) |
| Al destroy | snapshot finale e backup automatici da cancellare a mano | nessuno snapshot, backup automatici cancellati |


## 🔧 Architettura

```
VPC (default o l'unica) ── subnet 1 e 2 (due zone) ── subnet group
   ├── istanza RDS db.t4g.micro (MySQL / MariaDB / PostgreSQL), segreto aws-py-cdk11-database...
   └── [con -c aurora=true] cluster Aurora MySQL Serverless v2 0-2 ACU, segreto, Data API
security group: porta 3306/5432 da allowedcidr
CLI ── aws rds-data execute-statement ── Data API (HTTPS) ── Aurora     (nessuna rete verso il database)
```

```
├── app.py                 # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk11rds/
│   ├── cdk11rds_stack.py  # 🏗️ security group, istanza RDS, cluster Aurora facoltativo
│   ├── naming.py          # 🏷️ nomi aws-py-cdk11-<servizio> e tag Name di ogni risorsa
│   └── tags.py            # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/            # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk11rds/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
# varianti
cdk deploy -c engine=postgres     # PostgreSQL al posto di MySQL
cdk deploy -c aurora=true         # anche il cluster Aurora Serverless v2
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid`, `subnetid1`, `subnetid2` e `allowedcidr` (il CIDR della VPC), che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Parametro facoltativo: `dbname` (default `cdk11rds`). Il deploy dura circa 10 minuti (15-20 con Aurora). Cambiare `engine` su uno stack già creato sostituisce il database (i dati si perdono).

Al termine `cdk deploy` stampa `Engine`, `DatabaseEndpoint`, `DatabasePort`, `DatabaseSecretArn` e, con Aurora, `AuroraClusterArn`, `AuroraEndpoint`, `AuroraReaderEndpoint`, `AuroraSecretArn`.

**Connessione all'istanza RDS**: il database non è pubblico, quindi ci si collega da una macchina nella stessa VPC (per esempio l'istanza del [cdk17elasticIP](../cdk17elasticIP/) o del [cdk19wordpressSingle](../cdk19wordpressSingle/), con Session Manager):
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk11 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws secretsmanager get-secret-value --secret-id $(out DatabaseSecretArn) --query SecretString --output text   # username, password, host
# dalla macchina nella VPC (sudo dnf install -y mariadb105 per il client MySQL, postgresql17 per PostgreSQL)
mysql -h <DatabaseEndpoint> -u alnao -p cdk11rds
```

**Query su Aurora con la Data API** (nessuna rete verso il database): la prima chiamata dopo la pausa risponde `DatabaseResumingException`, dopo circa 15 secondi il cluster è pronto.
```bash
CLUSTER=$(out AuroraClusterArn); SECRET=$(out AuroraSecretArn)
aws rds-data execute-statement --resource-arn $CLUSTER --secret-arn $SECRET --database cdk11rds --sql "SELECT NOW()"
aws rds-data execute-statement --resource-arn $CLUSTER --secret-arn $SECRET --database cdk11rds \
  --sql "CREATE TABLE IF NOT EXISTS persone (id INT AUTO_INCREMENT PRIMARY KEY, nome VARCHAR(100), cognome VARCHAR(100))"
aws rds-data execute-statement --resource-arn $CLUSTER --secret-arn $SECRET --database cdk11rds \
  --sql "INSERT INTO persone (nome, cognome) VALUES ('Alberto', 'Nao')"
aws rds-data execute-statement --resource-arn $CLUSTER --secret-arn $SECRET --database cdk11rds \
  --sql "SELECT * FROM persone" --format-records-as JSON --query formattedRecords --output text
```

Comandi utili:
```bash
aws rds describe-db-instances --query "DBInstances[].[DBInstanceIdentifier,Engine,EngineVersion,DBInstanceStatus,Endpoint.Address]" --output table
aws rds describe-db-clusters --query "DBClusters[].[DBClusterIdentifier,Status,ServerlessV2ScalingConfiguration]" --output table
aws cloudwatch get-metric-statistics --namespace AWS/RDS --metric-name ServerlessDatabaseCapacity --dimensions Name=DBClusterIdentifier,Value=<cluster> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) --period 300 --statistics Average   # 0 = in pausa
```

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk11rds`, `ManagedBy=CDK`): istanza, cluster, subnet group, segreti, security group. Non hanno tag solo gli agganci tra segreto e database (`SecretTargetAttachment`), che CloudFormation non permette di taggare. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk11-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS e di [Amazon RDS](https://aws.amazon.com/rds/pricing/).

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| Istanza RDS `db.t4g.micro` | ~0,018 $/ora (MySQL, MariaDB e PostgreSQL simili) | ~13 $ |
| Storage gp3 | 20 GB × 0,137 $/GB | ~2,70 $ |
| Backup automatici | 1 giorno, dentro lo spazio gratuito pari al disco | 0 $ |
| Secrets Manager | 1 segreto (2 con Aurora) × 0,40 $ | 0,40-0,80 $ |
| **Totale senza Aurora** | | **~16 $** |
| Aurora Serverless v2 in pausa | solo storage, pochi MB × 0,11 $/GB | ~0 $ |
| Aurora Serverless v2 attivo | 0,5-2 ACU × ~0,14 $/ACU-ora, solo mentre ci sono connessioni | 0,07-0,28 $ per ora di uso |
| Data API | ~0,35 $ per milione di richieste | ~0 $ |

Con la pausa a 0 ACU un cluster Aurora usato poche ore al mese costa meno dell'istanza RDS sempre accesa; la prima query dopo la pausa però attende circa 15 secondi.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk11rds --query "ResourceTagMappingList[].ResourceARN" --output text
# verifica: nessuno snapshot manuale rimasto
aws rds describe-db-snapshots --snapshot-type manual --query "DBSnapshots[].DBSnapshotIdentifier" --output text
```
- i database si cancellano **senza snapshot finale** e i backup automatici con loro: con dati da tenere togliere `RemovalPolicy.DESTROY` (CDK crea allora uno snapshot, che ha un costo di storage)
- i segreti si cancellano con lo stack
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔄 **Rotazione automatica** della password con Secrets Manager
- 🔌 **RDS Proxy** davanti al database per le Lambda
- 📖 **Read replica** e **Multi-AZ** per un ambiente di produzione
- 🐘 **Aurora PostgreSQL** Serverless v2 come alternativa al cluster MySQL


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Revisione degli esempi CDK: test eseguiti e tag standard verificati su tutte le risorse del template sintetizzato, nessuna modifica al codice |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk11-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk11, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk11 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


# AWS CDK 19 - WordPress su una istanza EC2

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

**WordPress** su una sola istanza **EC2** con il database su **RDS MySQL**. Versione CDK in Python dell'esempio CloudFormation [Esempio19wordpressSingle](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio19wordpressSingle), che usava due stack annidati (database e istanza) e `cfn-init`. È la versione "a una istanza" del [cdk21autoScalingWordpress](../cdk21autoScalingWordpress/), che aggiunge load balancer, Auto Scaling ed EFS.

- **🖥️ Istanza Amazon Linux 2023** (`t3.micro`) con Apache, PHP-FPM e WordPress in `/var/www/html`, installati al primo avvio
- **🗄️ RDS MySQL 8.4** `db.t4g.micro`, raggiungibile solo dall'istanza; utente e password generati in **Secrets Manager** e letti dall'istanza (la password non è un parametro e non finisce nei log)
- **📌 Elastic IP** su un'interfaccia di rete dello stack (come nel [cdk17elasticIP](../cdk17elasticIP/)): l'indirizzo del sito non cambia dopo stop e start, e l'interfaccia ha i tag
- **🚦 CloudFormation aspetta l'installazione**: lo script manda `cfn-signal` alla fine; se un comando fallisce, il log riporta `ERRORE cdk19: comando fallito alla riga N`; pacchetti, download e lettura del segreto vengono ripetuti fino a 30 volte
- **🔐 Nessuna porta SSH**: aperta solo la porta 80, si entra con **Session Manager**

| | CloudFormation (Esempio19) | CDK (cdk19) |
|---|---|---|
| Struttura | due stack annidati (`rdsMysql.yaml`, `ec2singleWP.yaml`) | un solo stack |
| Installazione | `cfn-init` e `cfn-hup` | script user data con `cfn-signal` |
| Password del database | parametro con default nel template | generata in Secrets Manager |
| IP pubblico | assegnato dalla subnet, cambia dopo stop e start | Elastic IP fisso |
| Accesso | key pair e porta 22 | Session Manager |
| Al destroy | snapshot finale del database | nessuno snapshot |


## 🔧 Architettura

```
Internet ── Elastic IP ── interfaccia di rete (security group: porta 80)
                               └── istanza EC2 AL2023: Apache + PHP-FPM + WordPress (/var/www/html)
                                        └── MySQL :3306 ── RDS db.t4g.micro (subnet 1 e 2, non pubblico)
istanza ── Secrets Manager (utente e password del database, letti al primo avvio)
```

```
├── app.py                              # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk19wordpress_single/
│   ├── cdk19wordpress_single_stack.py  # 🏗️ security group, RDS, interfaccia di rete, Elastic IP, istanza
│   ├── naming.py                       # 🏷️ nomi aws-py-cdk19-<servizio> e tag Name di ogni risorsa
│   └── tags.py                         # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                         # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk19wordpressSingle/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid`, `subnetid1` (istanza e database) e `subnetid2` (database), che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Le due subnet devono stare in zone diverse (lo chiede il subnet group del database). Parametri facoltativi: `instancetype` (default `t3.micro`) e `dbname` (default `wordpress`). Il deploy dura circa 15 minuti, quasi tutti per il database.

Al termine `cdk deploy` stampa `WebsiteUrl` (la prima visita apre l'installazione di WordPress), `ElasticIpAddress`, `InstanceId`, `DatabaseEndpoint` e `DatabaseSecretArn`.

**Verifica dell'istanza** (serve il plugin Session Manager della CLI):
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk19 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
curl -sI $(out WebsiteUrl)
aws ssm start-session --target $(out InstanceId)
# dentro l'istanza
    sudo cat /var/log/cloud-init-output.log
    curl -s localhost/wp-admin/install.php | head
```

**Se il deploy fallisce con `Received 1 FAILURE signal(s)`** lo script di installazione si è fermato su un comando: con `cdk deploy --no-rollback ...` l'istanza resta accesa e la riga `ERRORE cdk19` si legge con `aws ec2 get-console-output --instance-id <id> --latest --output text`; poi `cdk destroy` e nuovo deploy.

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk19wordpressSingle`, `ManagedBy=CDK`): istanza, disco, interfaccia di rete, Elastic IP, database, segreto, security group e ruolo. Non hanno tag solo i tipi che CloudFormation non permette di taggare: associazione dell'Elastic IP, regola del security group del database, instance profile, policy IAM inline, aggancio tra segreto e database. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk19-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| EC2 `t3.micro` | 0,012 $/ora | ~9 $ |
| Elastic IP | 0,005 $/ora | ~3,60 $ |
| EBS gp3 | 8 GB × 0,095 $/GB | ~0,80 $ |
| RDS `db.t4g.micro` | 0,017 $/ora + 20 GB gp3 | ~15 $ |
| Secrets Manager | 1 segreto × 0,40 $ | 0,40 $ |
| **Totale** | | **~29 $** |

Rispetto al cdk21 mancano load balancer, NAT ed EFS: costa circa la metà, ma un solo server non ha ridondanza.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk19wordpressSingle --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il database si cancella **senza snapshot finale** e senza backup automatici (con dati da tenere togliere `RemovalPolicy.DESTROY`)
- istanza e disco vengono terminati, interfaccia di rete ed Elastic IP rilasciati
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔒 **HTTPS** con Let's Encrypt (certbot) sull'istanza e un record Route 53 sull'Elastic IP
- 💾 **Backup** dell'istanza e del database con AWS Backup
- 🧩 Passaggio al [cdk21autoScalingWordpress](../cdk21autoScalingWordpress/) quando servono più server


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Revisione degli esempi CDK: test eseguiti e tag standard verificati su tutte le risorse del template sintetizzato, nessuna modifica al codice |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk19-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk19, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk19 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


# AWS CDK 18 - File system EFS con EC2

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un file system **Amazon EFS** montato da un'istanza **EC2** come cartella del sito **Apache**. Versione CDK in Python dell'esempio CloudFormation [Esempio18efs](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio18efs).

- **📁 EFS cifrato** con il mount target nella subnet indicata; la porta NFS 2049 è aperta solo al security group dell'istanza
- **🖥️ Istanza Amazon Linux 2023** con IP pubblico, IMDSv2, disco gp3 cifrato, **Session Manager** (niente SSH e key pair), solo la porta 80 aperta
- **🔁 Script di avvio robusto**: monta EFS in `/var/www/html` con TLS ripetendo il mount finché il nome DNS del mount target non è pronto (fino a 90 secondi dopo la creazione), lo aggiunge a `/etc/fstab`, aggiunge una riga alla pagina condivisa e avvia Apache
- **🏷️ Tag su tutto**: disco e interfaccia di rete creati da EC2 ricevono i tag da un launch template collegato all'istanza (come nel [cdk02](../cdk02ec2/)); il tag `Name` di EFS e istanza è quello standard (prima era il percorso del costrutto)

Rispetto alla prima versione: Amazon Linux 2 (fuori supporto dal 30/06/2026) sostituito da AL2023, zona `eu-west-1b` non più scritta nel codice, niente SSH aperto a Internet, metadati con IMDSv2 e mount con nuovi tentativi invece di un `sleep` fisso.


## 🔧 Architettura

```
Internet ── HTTP :80 ── istanza EC2 AL2023 (subnet pubblica, Apache)
                           └── /var/www/html ── NFS 2049 (TLS) ── mount target ── EFS cifrato
Session Manager ── istanza (ruolo AmazonSSMManagedInstanceCore + accesso a EFS)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk18efs/
│   ├── cdk18efs_stack.py           # 🏗️ security group, EFS, ruolo, launch template dei tag, istanza e script
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk18-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard, apply_tags e aspect dei launch template
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk18efs/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid` e `subnetid`, che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Verifica (lo script di avvio impiega un paio di minuti):
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk18 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
curl $(out WebsiteUrl)
aws efs describe-mount-targets --file-system-id $(out FileSystemId) --query "MountTargets[].[SubnetId,LifeCycleState,IpAddress]" --output table
aws ssm start-session --target $(out InstanceId)      # poi: df -h /var/www/html ; sudo tail /var/log/cloud-init-output.log
```
Per vedere che i file stanno su EFS e non sul disco dell'istanza: terminare l'istanza dalla console e rilanciare `cdk deploy`; CloudFormation ne crea una nuova che trova la pagina già presente e aggiunge la sua riga.

**Tag**: istanza, disco, interfaccia di rete, launch template, EFS, security group e ruolo hanno i tag standard (`Project=Development.aws.py-CDK.cdk18efs`, `ManagedBy=CDK`); instance profile, mount target, regole dei security group e policy IAM non accettano tag. L'interfaccia di rete del mount target è gestita da EFS e non ha tag; l'IP pubblico dell'istanza non è una risorsa e non ha tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk18-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| EC2 `t3.micro` | 0,012 $/ora | ~9 $ |
| IPv4 pubblico | 0,005 $/ora | ~3,60 $ |
| EBS gp3 | 8 GB × 0,095 $/GB | ~0,80 $ |
| EFS Standard | 0,36 $/GB al mese (pochi KB di pagina) | ~0 $ |
| **Totale** | | **~13 $** |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk18efs --query "ResourceTagMappingList[].ResourceARN" --output text
```
- l'istanza viene terminata con disco e interfaccia di rete; EFS viene cancellato con i file (`RemovalPolicy.DESTROY`)
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🧮 **Più istanze** dietro un load balancer che condividono lo stesso EFS (è il [cdk21](../cdk21autoScalingWordpress/))
- 🚪 **Access point** EFS con utente e cartella dedicati, mount con autorizzazione IAM
- 💾 **AWS Backup** del file system e classe di storage Infrequent Access per i file poco usati


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: Amazon Linux 2023 al posto di Amazon Linux 2 (fuori supporto), IMDSv2, Session Manager al posto di SSH e key pair, VPC e subnet come parametri tipizzati (niente zona eu-west-1b fissa), EFS cifrato con NFS aperto solo all'istanza, mount con TLS e nuovi tentativi, tag standard (anche Name) su EFS, istanza, disco e interfaccia di rete, test veri, README nuovo |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk18-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk18, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named; launch template dei tag rinominato WebServerTemplate |
| 2026-11-17 | Tag Name aws-py-cdk18 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |
| 2026-11-17 | Descrizioni security group senza apostrofo, deploy falliva |


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


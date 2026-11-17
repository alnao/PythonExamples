# AWS CDK 02 - Istanza EC2

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'istanza **EC2 Amazon Linux 2023** in una subnet pubblica di una VPC esistente, gestita con **Session Manager** (niente SSH e niente key pair). Versione CDK in Python dell'esempio CloudFormation [Esempio02istanzeEC2](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio02istanzeEC2); la prima versione aveva preso spunto dall'esempio di [cloudbrilliant](https://github.com/cloudbrilliant/cdk-ec2).

- **🖥️ Istanza** `t3.micro` (parametro `instancetype`) con IP pubblico, disco gp3 da 8 GB cifrato, IMDSv2 obbligatorio
- **🔐 Nessuna porta in ingresso**: il security group non ha regole in entrata, si entra con `aws ssm start-session` (ruolo `AmazonSSMManagedInstanceCore`)
- **🏷️ Tag anche su disco e interfaccia di rete**: con l'IP pubblico assegnato all'avvio l'interfaccia di rete la crea EC2, e CloudFormation non le darebbe i tag; un launch template collegato all'istanza applica i tag standard a istanza, disco e interfaccia
- **🌍 Nessuna zona fissa**: VPC e subnet sono parametri, la zona è quella della subnet (la prima versione aveva `eu-west-1b` scritto nel codice)


## 🔧 Architettura

```
VPC esistente ── subnet pubblica ── interfaccia di rete (creata da EC2, tag dal launch template, IP pubblico)
                                        └── istanza EC2 AL2023 ── disco gp3 8 GB cifrato
Session Manager ── istanza (ruolo AmazonSSMManagedInstanceCore, solo traffico in uscita)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk02ec2/
│   ├── cdk02ec2_stack.py           # 🏗️ security group, ruolo, launch template dei tag, istanza
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk02-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard, apply_tags e aspect dei launch template
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, plugin Session Manager della CLI per entrare nell'istanza.

```bash
cd PythonExamples/AWS/CDK/cdk02ec2/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid` e `subnetid`, che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Al termine `cdk deploy` stampa `InstanceId`, `PublicIp` e `SessionCommand`.

Verifica:
```bash
INSTANCE=$(aws cloudformation describe-stacks --stack-name aws-py-cdk02 --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" --output text)
aws ssm start-session --target $INSTANCE
# tag di disco e interfaccia di rete
aws ec2 describe-volumes --filters Name=attachment.instance-id,Values=$INSTANCE --query "Volumes[].Tags" --output table
aws ec2 describe-network-interfaces --filters Name=attachment.instance-id,Values=$INSTANCE --query "NetworkInterfaces[].TagSet" --output table
```

**Tag**: istanza, disco, interfaccia di rete, launch template, security group e ruolo hanno i tag standard (`Project=Development.aws.py-CDK.cdk02ec2`, `ManagedBy=CDK`); l'instance profile non accetta tag. L'IP pubblico assegnato all'avvio non è una risorsa e non ha tag: il suo costo in Cost Explorer non si può filtrare per `Project` (con un Elastic IP sì, vedi il cdk17). Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk02-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| EC2 `t3.micro` | 0,012 $/ora | ~9 $ |
| IPv4 pubblico | 0,005 $/ora | ~3,60 $ |
| EBS gp3 | 8 GB × 0,095 $/GB | ~0,80 $ |
| **Totale** | | **~13 $** |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk02ec2 --query "ResourceTagMappingList[].ResourceARN" --output text
```
- l'istanza viene terminata insieme a disco e interfaccia di rete (`DeleteOnTermination`)
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🌐 **Web server**: user data con Apache e porta 80 aperta (vedi cdk17 e cdk18)
- ⏰ **Spegnimento notturno** con EventBridge Scheduler per risparmiare
- 🆓 **IPv6**: subnet dual-stack senza il costo dell'IPv4 pubblico


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: Amazon Linux 2023, IMDSv2, Session Manager al posto di SSH e key pair, VPC e subnet come parametri tipizzati (niente zona eu-west-1b fissa), tag standard anche su disco e interfaccia di rete tramite launch template, test veri, README nuovo |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk02-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk02, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named; launch template dei tag rinominato InstanceTemplate |
| 2026-11-17 | Tag Name aws-py-cdk02 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


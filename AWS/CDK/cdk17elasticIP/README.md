# AWS CDK 17 - Istanza EC2 con Elastic IP

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'istanza **EC2** con un indirizzo IP pubblico fisso, un **Elastic IP**: l'indirizzo resta lo stesso anche se l'istanza viene fermata, riavviata o sostituita. Versione CDK in Python dell'esempio CloudFormation [Esempio17elasticIP](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio17elasticIP), che usava l'istanza dell'esempio 02 come stack annidato.

- **🔌 Interfaccia di rete dello stack**: l'ENI è creata a parte (con i tag standard) e collegata all'istanza come interfaccia principale; l'interfaccia che EC2 crea da sola con l'istanza non riceverebbe i tag
- **📌 Elastic IP associato all'interfaccia** (non all'istanza): se l'istanza viene sostituita basta ricollegare la stessa interfaccia, e l'IP la segue
- **🖥️ Istanza Amazon Linux 2023** (`t3.micro`) con Apache e una pagina di prova con l'id dell'istanza e la zona; disco gp3 cifrato con i tag dell'istanza, IMDSv2 obbligatorio
- **🔐 Nessuna porta SSH**: aperta solo la porta 80, si entra con **Session Manager** (il CloudFormation usava una key pair e la porta 22)

| | CloudFormation (Esempio17) | CDK (cdk17) |
|---|---|---|
| Istanza | stack annidato dell'esempio 02, key pair e SSH | istanza nello stack, Session Manager |
| Elastic IP | associato all'istanza (`InstanceId`) | associato all'interfaccia di rete dello stack |
| Interfaccia di rete | creata da EC2, senza tag | risorsa dello stack, con i tag |
| Tag | istanza con i tag dell'esempio 02 | tutte le risorse con i tag del cdk17, anche disco e interfaccia |


## 🔧 Architettura

```
Internet ── Elastic IP (fisso) ── interfaccia di rete (ENI dello stack, security group: solo porta 80)
                                        └── istanza EC2 AL2023, Apache :80 ── disco gp3 8 GB
Session Manager ── istanza (ruolo AmazonSSMManagedInstanceCore)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk17elastic_ip/
│   ├── cdk17elastic_ip_stack.py    # 🏗️ security group, interfaccia di rete, ruolo, istanza, Elastic IP
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk17-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk17elasticIP/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid` e `subnetid`, che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Parametro facoltativo: `instancetype` (default `t3.micro`). Al termine `cdk deploy` stampa `ElasticIpAddress`, `AllocationId`, `WebsiteUrl`, `InstanceId` e `NetworkInterfaceId`.

**Provare che l'IP resta fisso**: dopo uno stop e uno start l'istanza mantiene l'Elastic IP (un IP pubblico normale invece cambierebbe).
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk17 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
IP=$(out ElasticIpAddress); INSTANCE=$(out InstanceId)
curl http://$IP/
aws ec2 stop-instances --instance-ids $INSTANCE && aws ec2 wait instance-stopped --instance-ids $INSTANCE
aws ec2 start-instances --instance-ids $INSTANCE && aws ec2 wait instance-running --instance-ids $INSTANCE
curl http://$IP/          # stesso indirizzo, nuova data di avvio nella pagina
```
Mentre l'istanza è ferma l'Elastic IP continua a costare (è allocato), il disco anche; l'istanza no.

Comandi utili:
```bash
aws ec2 describe-addresses --query "Addresses[].[PublicIp,AllocationId,NetworkInterfaceId,InstanceId]" --output table
aws ec2 describe-network-interfaces --network-interface-ids $(out NetworkInterfaceId) --query "NetworkInterfaces[0].[Status,PrivateIpAddress,Association.PublicIp]"
aws ssm start-session --target $INSTANCE     # serve il plugin Session Manager della CLI
```

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk17elasticIP`, `ManagedBy=CDK`): istanza, disco (`PropagateTagsToVolumeOnCreation`), interfaccia di rete, Elastic IP, security group e ruolo. Non hanno tag solo l'associazione dell'Elastic IP e l'instance profile, che CloudFormation non permette di taggare. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk17-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| EC2 `t3.micro` | 0,012 $/ora | ~9 $ |
| Elastic IP | 0,005 $/ora, associato o no (come ogni IPv4 pubblico) | ~3,60 $ |
| EBS gp3 | 8 GB × 0,095 $/GB | ~0,80 $ |
| **Totale** | | **~13 $** |

Un Elastic IP allocato ma non associato costa come uno associato: va rilasciato quando non serve (il destroy dello stack lo fa).


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk17elasticIP --query "ResourceTagMappingList[].ResourceARN" --output text
```
- l'istanza viene terminata con il suo disco; interfaccia di rete ed Elastic IP vengono staccati e rilasciati
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🌍 **Record DNS** Route 53 che punta all'Elastic IP
- 🔁 **Failover**: Lambda che sposta l'Elastic IP su un'istanza di riserva quando la principale non risponde
- 🆓 **IPv6**: subnet dual-stack con indirizzi IPv6 pubblici, che non hanno il costo degli IPv4


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Revisione degli esempi CDK: test eseguiti e tag standard verificati su tutte le risorse del template sintetizzato, nessuna modifica al codice |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk17-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk17, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk17 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |
| 2026-11-17 | Descrizione interfaccia di rete senza apostrofo, deploy falliva |


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


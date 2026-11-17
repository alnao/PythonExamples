# AWS CDK 20 - Auto Scaling group con load balancer

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un **Auto Scaling group** di istanze **Apache** dietro un **Application Load Balancer**, nella VPC di default senza NAT gateway. Versione CDK in Python dell'esempio CloudFormation [Esempio20loadBalancer](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio20loadBalancer).

- **⚖️ Application Load Balancer** pubblico su due subnet in zone diverse
- **🖥️ Auto Scaling group** da 1 a 4 istanze (2 all'avvio) Amazon Linux 2023 con Apache e una pagina che mostra istanza e zona: aggiornando la pagina si vede il load balancer alternare i server
- **🔐 Istanze raggiungibili solo dal load balancer**: stanno nelle subnet pubbliche con un IP pubblico (per scaricare i pacchetti senza NAT gateway), ma la porta 80 è aperta solo al security group del load balancer; niente SSH e key pair, si entra con Session Manager
- **📈 Scaling sulla CPU** media (target 70%) e controllo di salute del load balancer: un'istanza che non risponde viene sostituita
- **🏷️ Tag anche su dischi e interfacce di rete** delle istanze: il launch template li applica a istanze, volumi e interfacce di rete (IMDSv2 obbligatorio, disco gp3 cifrato)

Perché la prima versione non funzionava nella VPC di default: le istanze stavano in subnet private che dovevano avere un NAT gateway; senza NAT non installavano Apache, il controllo di salute falliva e l'Auto Scaling group le sostituiva in continuazione. In più chiedeva una key pair con SSH aperto a tutti, usava Amazon Linux 2 (fuori supporto dal 30/06/2026) e le zone `eu-west-1a/b` scritte nel codice. Per la versione con subnet private, EFS e database vedere il [cdk21](../cdk21autoScalingWordpress/).


## 🔧 Architettura

```
Internet ── HTTP :80 ── Application Load Balancer (subnet 1 e 2)
                           └── target group (health check su /) ── Auto Scaling group 1..4 istanze
                                   istanze AL2023 + Apache (subnet 1 e 2, IP pubblico, porta 80 solo dal load balancer)
CloudWatch CPU media ── target tracking 70% ── aggiunge / toglie istanze
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk20auto_scaling/
│   ├── cdk20auto_scaling_stack.py  # 🏗️ security group, launch template, Auto Scaling group, load balancer
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk20-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard, apply_tags e aspect dei launch template
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk20autoScaling/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid`, `subnetid1` e `subnetid2`, che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Verifica (le istanze impiegano un paio di minuti a diventare sane):
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk20 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
for i in 1 2 3 4; do curl -s $(out WebsiteUrl) | grep Risponde; done      # istanze e zone diverse
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $(out AutoScalingGroupName) \
  --query "AutoScalingGroups[0].Instances[].[InstanceId,AvailabilityZone,HealthStatus,LifecycleState]" --output table
```

**Tag**: load balancer, target group, Auto Scaling group (propagati alle istanze), launch template (che li applica a istanze, dischi e interfacce di rete), security group e ruolo hanno i tag standard (`Project=Development.aws.py-CDK.cdk20autoScaling`, `ManagedBy=CDK`); listener, policy di scaling, instance profile, regole dei security group e policy IAM non accettano tag. Le interfacce di rete del load balancer sono gestite da ELB e non hanno tag; gli IP pubblici delle istanze e del load balancer non sono risorse e non hanno tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk20-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| EC2 `t3.micro` × 2 | 0,012 $/ora ciascuna | ~17 $ |
| Application Load Balancer | 0,027 $/ora + LCU (~0 per i test) | ~19,50 $ |
| IPv4 pubblici | 0,005 $/ora × (2 istanze + 2 del load balancer) | ~14,40 $ |
| EBS gp3 | 2 × 8 GB × 0,095 $/GB | ~1,50 $ |
| **Totale** | | **~52 $** |

Il NAT gateway della prima versione da solo costava circa 35 $ al mese più il traffico.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk20autoScaling --query "ResourceTagMappingList[].ResourceARN" --output text
```
- l'Auto Scaling group termina le istanze (con dischi e interfacce di rete), il load balancer viene cancellato
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔒 **HTTPS** sul load balancer con un certificato ACM e redirect dalla porta 80
- 🔔 **Allarmi e notifiche** su CPU e istanze malate (è il [cdk22](../cdk22cloudWatchAlarm/))
- 💸 **Istanze Spot** nell'Auto Scaling group con una politica mista on-demand/spot


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: funziona nella VPC di default senza NAT gateway (istanze in subnet pubbliche raggiungibili solo dal load balancer), Amazon Linux 2023 al posto di Amazon Linux 2, IMDSv2, Session Manager al posto di SSH e key pair, niente zone eu-west-1a/b fisse, health check con la nuova API, tag standard anche su interfacce di rete e dischi tramite il launch template, test veri, README nuovo |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk20-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk20, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk20 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


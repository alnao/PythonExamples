# AWS CDK 22 - Allarmi CloudWatch

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Allarmi **Amazon CloudWatch** sull'infrastruttura WordPress del [cdk21autoScalingWordpress](../cdk21autoScalingWordpress/) (load balancer, Auto Scaling group, RDS, EFS). Versione CDK in Python dell'esempio CloudFormation [Esempio22cloudWatchAlarm](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio22cloudWatchAlarm): come l'originale includeva il template dell'esempio 21 come stack annidato, qui la classe dello stack **estende** quella del cdk21 e aggiunge gli allarmi.

- **📈 Scaling sulla CPU**: due allarmi sulla CPU media dell'Auto Scaling group, sopra l'**84%** per 10 minuti aggiunge un server, sotto il **42%** per 10 minuti ne toglie uno (policy *step scaling*, da 1 a 3 server)
- **🩺 Salute del sito**: allarme se almeno un server non risponde al controllo di salute per 3 minuti, e se il load balancer genera più di 10 errori 5xx in 5 minuti
- **📣 Notifiche SNS**: gli allarmi di salute e lo scale-up scrivono su un topic SNS, con una email facoltativa (`-c alarm_email=...`)
- **📊 Dashboard CloudWatch** con lo stato degli allarmi, la CPU con le soglie, i server in servizio, le richieste e gli errori

| Allarme | Metrica | Condizione | Azione |
|---------|---------|------------|--------|
| `aws-py-cdk22-cpu-high` | `AWS/EC2 CPUUtilization` media dell'ASG, 5 minuti | > 84 per 2 periodi | +1 server, notifica (anche al ritorno OK) |
| `aws-py-cdk22-cpu-low` | come sopra | < 42 per 2 periodi | -1 server |
| `aws-py-cdk22-unhealthy-hosts` | `UnHealthyHostCount` massimo del target group, 1 minuto | ≥ 1 per 3 periodi | notifica (anche al ritorno OK) |
| `aws-py-cdk22-load-balancer5xx` | `HTTPCode_ELB_5XX_Count` somma, 5 minuti | > 10 | notifica |

Con un solo server e poco traffico l'allarme `CpuLow` resta quasi sempre in stato `ALARM`: è normale, l'Auto Scaling group non scende sotto il minimo di 1 server.


## 🔧 Architettura

```
CloudWatch ── CpuHigh ──┬── policy step scaling +1 ── Auto Scaling group (cdk21)
           │            └── topic SNS ── email (facoltativa)
           ├── CpuLow ───── policy step scaling -1 ── Auto Scaling group
           ├── UnhealthyHosts ── topic SNS
           └── LoadBalancer5xx ── topic SNS
Dashboard aws-py-cdk22-wordpress: stato degli allarmi, CPU, server in servizio, richieste, errori
```

```
├── app.py                               # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk22cloud_watch_alarm/
│   ├── cdk22cloud_watch_alarm_stack.py  # 🏗️ estende lo stack del cdk21: allarmi, scaling, SNS, dashboard
│   ├── naming.py                        # 🏷️ nomi aws-py-cdk22-<servizio> e tag Name di ogni risorsa
│   └── tags.py                          # 🏷️ tag standard del cdk22 (anche sulle risorse ereditate dal cdk21)
├── tests/unit/                          # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```
Lo stack importa il codice dalla cartella `../cdk21autoScalingWordpress`: i due progetti vanno tenuti uno accanto all'altro. Le risorse hanno i tag del cdk22 e i nomi derivati dal nome dello stack, quindi cdk21 e cdk22 si possono installare insieme nello stesso account.


## 🛠️ Deploy

Prerequisiti: gli stessi del cdk21 (per default la VPC di default della region, oppure una VPC con subnet private e NAT passata con i parametri).

```bash
cd PythonExamples/AWS/CDK/cdk22cloudWatchAlarm/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# test locali: sintesi dello stack, nessuna chiamata AWS
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy -c alarm_email=nome@example.com
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri del cdk21: `vpcid`, `publicsubnetids1`, `publicsubnetids2`, `privatesubnetid1`, `privatesubnetid2` e `instancespublicip` (vedi il [README del cdk21](../cdk21autoScalingWordpress/README.md)), che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

**Con la VPC di default** non ci sono subnet private né NAT: i server, il database e i mount target EFS vanno nelle stesse subnet pubbliche del load balancer. I server ricevono un IP pubblico (escono su Internet senza NAT, ma costano 0,005 $/ora in più ciascuno) e restano raggiungibili solo dal load balancer, perché il loro security group accetta la porta 80 solo da lì; il database non è pubblico (`PubliclyAccessible=false`) e accetta solo i server. Per un ambiente vero conviene una VPC con subnet private e NAT.

Senza `-c alarm_email=...` il topic non ha iscritti (le notifiche si vedono solo nella console). Con l'email, AWS manda un messaggio con il link di conferma: finché non si conferma, le notifiche non arrivano.

Al termine `cdk deploy` stampa, oltre agli output del cdk21, `AlarmTopicArn`, `CpuAlarmHighName` e `DashboardUrl`.

Se il deploy fallisce sull'Auto Scaling group con `Received 1 FAILURE signal(s) out of 1`, lo script di avvio dei server (è quello del cdk21) è terminato con un errore: per trovarlo vedi la sezione Deploy del [README del cdk21](../cdk21autoScalingWordpress/README.md) (`cdk deploy --no-rollback` e log della console), usando `Values=Development.aws.py-CDK.cdk22cloudWatchAlarm` nel filtro delle istanze.

**Provare gli allarmi**: lo stato di un allarme si può forzare a mano; l'azione parte subito e l'allarme torna allo stato reale alla valutazione successiva (entro 5 minuti).
```bash
STACK=aws-py-cdk22
aws cloudwatch describe-alarms --alarm-name-prefix $STACK --query "MetricAlarms[].[AlarmName,StateValue]" --output table
aws cloudwatch set-alarm-state --alarm-name $STACK-CpuHigh --state-value ALARM --state-reason "Prova scale-up"
aws autoscaling describe-scaling-activities --auto-scaling-group-name <AutoScalingGroupName> --max-items 3
aws cloudwatch describe-alarm-history --alarm-name $STACK-CpuHigh --history-item-type StateUpdate --max-items 5
```
Per un carico vero sulla CPU: `aws ssm start-session --target i-xxx` e dentro l'istanza `sudo dnf install -y stress-ng && stress-ng --cpu 2 --timeout 15m`.

Altri comandi utili:
```bash
aws cloudwatch disable-alarm-actions --alarm-names $STACK-CpuLow   # sospende le azioni di un allarme
aws cloudwatch enable-alarm-actions --alarm-names $STACK-CpuLow
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=<AutoScalingGroupName> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) --period 300 --statistics Average
```

**Tag**: tutte le risorse hanno i tag standard del cdk22 (`Project=Development.aws.py-CDK.cdk22cloudWatchAlarm`, `ManagedBy=CDK`), anche quelle ereditate dal cdk21. Non hanno tag solo i tipi che CloudFormation non permette di taggare: policy di scaling, dashboard, iscrizioni SNS, regole dei security group, mount target EFS, listener, instance profile, policy IAM inline. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk22-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| Infrastruttura del cdk21 | load balancer, 1 server, RDS, EFS, segreto (vedi il README del cdk21) | ~53 $ |
| Allarmi CloudWatch | 4 allarmi standard × 0,10 $ (i primi 10 dell'account sono gratuiti) | 0-0,40 $ |
| Dashboard | le prime 3 dell'account sono gratuite, poi 3 $ ciascuna | 0-3 $ |
| SNS | poche notifiche email (le prime 1.000 al mese sono gratuite) | 0 $ |
| Server aggiunti dallo scaling | 0,012 $/ora per ogni `t3.micro` in più | variabile |
| **Totale** | | **~53-57 $** |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk22cloudWatchAlarm --query "ResourceTagMappingList[].ResourceARN" --output text
```
- valgono le note del cdk21: il database si cancella senza snapshot finale, EFS con tutti i file, le istanze vengono terminate
- allarmi, policy di scaling, topic con le iscrizioni e dashboard si cancellano con lo stack
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🎯 **Target tracking** (`scale_on_cpu_utilization`) al posto delle due soglie fisse, da confrontare con lo step scaling
- 🧪 **Allarme composito** (CPU alta e server malati insieme) e **anomaly detection** sulle richieste
- 📨 **Chatbot** o Lambda iscritta al topic per mandare le notifiche su Slack o Teams


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-10 | Prima versione dell'esempio, ispirata all'esempio CloudFormation corrispondente |
| 2026-11-17 | Revisione degli esempi CDK: test eseguiti e tag standard verificati su tutte le risorse del template sintetizzato, nessuna modifica al codice |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk22-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk22, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named; corretto l'output DashboardUrl, che avrebbe puntato al vecchio nome della dashboard |
| 2026-11-17 | Tag Name aws-py-cdk22 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


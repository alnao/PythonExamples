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
| `<stack>-CpuHigh` | `AWS/EC2 CPUUtilization` media dell'ASG, 5 minuti | > 84 per 2 periodi | +1 server, notifica (anche al ritorno OK) |
| `<stack>-CpuLow` | come sopra | < 42 per 2 periodi | -1 server |
| `<stack>-UnhealthyHosts` | `UnHealthyHostCount` massimo del target group, 1 minuto | ≥ 1 per 3 periodi | notifica (anche al ritorno OK) |
| `<stack>-LoadBalancer5xx` | `HTTPCode_ELB_5XX_Count` somma, 5 minuti | > 10 | notifica |

Con un solo server e poco traffico l'allarme `CpuLow` resta quasi sempre in stato `ALARM`: è normale, l'Auto Scaling group non scende sotto il minimo di 1 server.


## 🔧 Architettura

```
CloudWatch ── CpuHigh ──┬── policy step scaling +1 ── Auto Scaling group (cdk21)
           │            └── topic SNS ── email (facoltativa)
           ├── CpuLow ───── policy step scaling -1 ── Auto Scaling group
           ├── UnhealthyHosts ── topic SNS
           └── LoadBalancer5xx ── topic SNS
Dashboard <stack>-WordPress: stato degli allarmi, CPU, server in servizio, richieste, errori
```

```
├── app.py                               # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk22cloud_watch_alarm/
│   ├── cdk22cloud_watch_alarm_stack.py  # 🏗️ estende lo stack del cdk21: allarmi, scaling, SNS, dashboard
│   └── tags.py                          # 🏷️ tag standard del cdk22 (anche sulle risorse ereditate dal cdk21)
├── tests/unit/                          # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```
Lo stack importa il codice dalla cartella `../cdk21autoScalingWordpress`: i due progetti vanno tenuti uno accanto all'altro. Le risorse hanno i tag del cdk22 e i nomi derivati dal nome dello stack, quindi cdk21 e cdk22 si possono installare insieme nello stesso account.


## 🛠️ Deploy

Prerequisiti: gli stessi del cdk21 (la VPC di default della region o l'unica presente, meglio se con subnet private e NAT).

```bash
cd PythonExamples/AWS/CDK/cdk22cloudWatchAlarm/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# test locali: sintesi dello stack, nessuna chiamata AWS
pytest tests/unit

# VPC e subnet recuperate con la CLI (comandi di sola lettura) e salvate come variabili d'ambiente
export AWS_REGION=eu-central-1               # usata anche da cdk deploy per scegliere la region
# VPC: quella di default, altrimenti l'unica presente nella region
export VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text)
if [ "$VPC_ID" = "None" ]; then
  VPCS=($(aws ec2 describe-vpcs --region $AWS_REGION --query "Vpcs[].VpcId" --output text))
  if [ ${#VPCS[@]} -eq 1 ]; then export VPC_ID=${VPCS[0]}; else echo "nessuna VPC di default e ${#VPCS[@]} VPC nella region: impostare VPC_ID a mano"; fi
fi
# subnet pubbliche: la loro tabella di routing ha una rotta verso l'Internet gateway (igw-...);
# nella VPC di default le subnet usano la tabella principale, quindi si prendono quelle con IP pubblico all'avvio, ordinate per zona
PUBLIC=($(aws ec2 describe-route-tables --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=route.gateway-id,Values=igw-*" --query "RouteTables[].Associations[].SubnetId" --output text))
if [ ${#PUBLIC[@]} -lt 2 ]; then
  PUBLIC=($(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" --query "sort_by(Subnets,&AvailabilityZone)[].SubnetId" --output text))
fi
# subnet private con uscita su Internet: la loro tabella di routing ha una rotta verso un NAT gateway (nat-...);
# se non ci sono (VPC di default) i server vanno nelle subnet pubbliche, con un IP pubblico
PRIVATE=($(aws ec2 describe-route-tables --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=route.nat-gateway-id,Values=nat-*" --query "RouteTables[].Associations[].SubnetId" --output text))
if [ ${#PRIVATE[@]} -lt 2 ]; then PRIVATE=("${PUBLIC[@]}"); echo "nessuna subnet privata con NAT: uso le subnet pubbliche"; fi
export PUBLIC_SUBNET_1=${PUBLIC[0]} PUBLIC_SUBNET_2=${PUBLIC[1]} PRIVATE_SUBNET_1=${PRIVATE[0]} PRIVATE_SUBNET_2=${PRIVATE[1]}
# controllo prima del deploy: quattro subnet, le due di ogni coppia in zone diverse
echo "VPC $VPC_ID - pubbliche $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 - private $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2"
aws ec2 describe-subnets --region $AWS_REGION --subnet-ids $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --query "Subnets[].[SubnetId,AvailabilityZone,CidrBlock,MapPublicIpOnLaunch]" --output table

#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy -c alarm_email=nome@example.com \
  --parameters vpcid=$VPC_ID \
  --parameters publicsubnetids1=$PUBLIC_SUBNET_1 --parameters publicsubnetids2=$PUBLIC_SUBNET_2 \
  --parameters privatesubnetid1=$PRIVATE_SUBNET_1 --parameters privatesubnetid2=$PRIVATE_SUBNET_2
```
Lo script prende la **VPC di default** della region o, se non c'è, l'**unica VPC** presente (con più VPC e nessuna di default va impostato a mano `export VPC_ID=vpc-xxx`). Le subnet pubbliche sono quelle con una rotta verso l'Internet gateway o, nella VPC di default, quelle con IP pubblico all'avvio; le private quelle con una rotta verso un NAT gateway. Se la VPC ha più di due subnet per tipo vengono prese le prime due: controllare la tabella stampata, ed eventualmente impostare a mano una variabile (es. `export PRIVATE_SUBNET_2=subnet-xxx`).

**Con la VPC di default** non ci sono subnet private né NAT: i server, il database e i mount target EFS vanno nelle stesse subnet pubbliche del load balancer. I server ricevono un IP pubblico (escono su Internet senza NAT, ma costano 0,005 $/ora in più ciascuno) e restano raggiungibili solo dal load balancer, perché il loro security group accetta la porta 80 solo da lì; il database non è pubblico (`PubliclyAccessible=false`) e accetta solo i server. Per un ambiente vero conviene una VPC con subnet private e NAT.

Senza `-c alarm_email=...` il topic non ha iscritti (le notifiche si vedono solo nella console). Con l'email, AWS manda un messaggio con il link di conferma: finché non si conferma, le notifiche non arrivano.

Al termine `cdk deploy` stampa, oltre agli output del cdk21, `AlarmTopicArn`, `CpuAlarmHighName` e `DashboardUrl`.

Se il deploy fallisce sull'Auto Scaling group con `Received 1 FAILURE signal(s) out of 1`, lo script di avvio dei server (è quello del cdk21) è terminato con un errore: per trovarlo vedi la sezione Deploy del [README del cdk21](../cdk21autoScalingWordpress/README.md) (`cdk deploy --no-rollback` e log della console), usando `Values=Development.aws.py-CDK.cdk22cloudWatchAlarm` nel filtro delle istanze.

**Provare gli allarmi**: lo stato di un allarme si può forzare a mano; l'azione parte subito e l'allarme torna allo stato reale alla valutazione successiva (entro 5 minuti).
```bash
STACK=Cdk22CloudWatchAlarmStack
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

**Tag**: tutte le risorse hanno i tag standard del cdk22 (`Project=Development.aws.py-CDK.cdk22cloudWatchAlarm`, `ManagedBy=CDK`), anche quelle ereditate dal cdk21. Non hanno tag solo i tipi che CloudFormation non permette di taggare: policy di scaling, dashboard, iscrizioni SNS, regole dei security group, mount target EFS, listener, instance profile, policy IAM inline.


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


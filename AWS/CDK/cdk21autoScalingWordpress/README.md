# AWS CDK 21 - Auto Scaling group con WordPress

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un **Application Load Balancer** davanti a un **Auto Scaling group** di istanze EC2 che eseguono **WordPress**: il codice e i file caricati stanno su un disco condiviso **EFS**, il database su **RDS MySQL**. Versione CDK in Python dell'esempio CloudFormation [Esempio21autoScalingWordpress](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio21autoScalingWordpress), che usava tre stack annidati (database dell'esempio 19, EFS dell'esempio 18, load balancer).

- **🌐 Load balancer pubblico** nelle subnet pubbliche, controllo di salute su `/hostname.html` e *sticky session* di 30 secondi (WordPress tiene la sessione sul server)
- **🖥️ Server in subnet private** (Amazon Linux 2023, Apache, PHP-FPM), da 1 a 3 istanze, sostituite se il load balancer le vede malate
- **📁 EFS condiviso**: il primo server installa WordPress in `/mnt/efs/wordpress`, gli altri lo trovano pronto; un `flock` sul disco condiviso evita due installazioni se partono insieme
- **🗄️ RDS MySQL 8.4** (`db.t4g.micro`), con utente e password generati in **Secrets Manager**: la password non è un parametro dello stack e non compare nei log
- **🚦 CloudFormation aspetta i server**: ogni istanza manda `cfn-signal` alla fine dello script; un aggiornamento del launch template sostituisce un server alla volta
- **🔐 Nessuna porta SSH**: si entra nei server con **Session Manager**

Differenze rispetto al template CloudFormation:
| | CloudFormation (Esempio21) | CDK (cdk21) |
|---|---|---|
| Installazione | `cfn-init` con `AWS::CloudFormation::Init` e `cfn-hup` | script user data con `cfn-signal` finale |
| Database | password come parametro (`DBPassword`) | password generata in Secrets Manager, letta dal server al primo avvio |
| Accesso ai server | chiave SSH (`KeyName`) e porta 22 | Session Manager, nessuna chiave |
| Chiavi di WordPress | quelle del file di esempio | generate a caso nel `wp-config.php` |
| Cancellazione del database | snapshot finale (costo di storage) | nessuno snapshot (`RemovalPolicy.DESTROY`) |


## 🔧 Architettura

```
Internet ── ALB (subnet pubbliche, porta 80) ── target group /hostname.html ──┬── EC2 (subnet privata 1)
                                                                               └── EC2 (subnet privata 2)
EC2 ──┬── EFS /mnt/efs/wordpress (NFS 2049)
      ├── RDS MySQL (3306), utente e password da Secrets Manager
      └── Internet tramite il NAT della VPC, o con IP pubblico nella VPC di default (pacchetti dnf, download di WordPress)
```

```
├── app.py                                   # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk21auto_scaling_wordpress/
│   ├── cdk21auto_scaling_wordpress_stack.py # 🏗️ security group, RDS, EFS, launch template, ASG, ALB
│   └── tags.py                              # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                              # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```

Lo stack è la base del [cdk22cloudWatchAlarm](../cdk22cloudWatchAlarm/), che lo estende con gli allarmi CloudWatch (come l'esempio 22 CloudFormation usava il 21 come stack annidato): per questo la classe espone `asg`, `alb`, `listener`, `target_group`, `database` e `file_system`.


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, la **VPC di default** della region (o l'unica presente); meglio ancora una VPC con due subnet pubbliche e due subnet private con uscita su Internet (NAT gateway).

```bash
cd PythonExamples/AWS/CDK/cdk21autoScalingWordpress/
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

# una volta per account e region: bootstrap con i nomi e i tag del repository (vedi AWS/CDK/bootstrap)
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk synth
cdk deploy \
  --parameters vpcid=$VPC_ID \
  --parameters publicsubnetids1=$PUBLIC_SUBNET_1 --parameters publicsubnetids2=$PUBLIC_SUBNET_2 \
  --parameters privatesubnetid1=$PRIVATE_SUBNET_1 --parameters privatesubnetid2=$PRIVATE_SUBNET_2
```

Lo script prende la **VPC di default** della region o, se non c'è, l'**unica VPC** presente (con più VPC e nessuna di default va impostato a mano `export VPC_ID=vpc-xxx`). Le subnet pubbliche sono quelle con una rotta verso l'Internet gateway o, nella VPC di default, quelle con IP pubblico all'avvio; le private quelle con una rotta verso un NAT gateway. Se la VPC ha più di due subnet per tipo vengono prese le prime due: controllare la tabella stampata, ed eventualmente impostare a mano una variabile (es. `export PRIVATE_SUBNET_2=subnet-xxx`).

**Con la VPC di default** non ci sono subnet private né NAT: i server, il database e i mount target EFS vanno nelle stesse subnet pubbliche del load balancer. I server ricevono un IP pubblico (escono su Internet senza NAT, ma costano 0,005 $/ora in più ciascuno) e restano raggiungibili solo dal load balancer, perché il loro security group accetta la porta 80 solo da lì; il database non è pubblico (`PubliclyAccessible=false`) e accetta solo i server. Per un ambiente vero conviene una VPC con subnet private e NAT.
Parametri facoltativi: `instancetype` (default `t3.micro`) e `dbname` (default `wordpress`). Il deploy dura circa 15 minuti, quasi tutti per il database.

Al termine `cdk deploy` stampa:
- `WebsiteURL`: l'indirizzo del sito, la prima visita apre l'installazione di WordPress (titolo, utente amministratore)
- `HealthURL`: la pagina del controllo di salute, con una riga per ogni server avviato
- `AutoScalingGroupName`, `DatabaseEndpoint`, `DatabaseSecretArn`, `FileSystemId`

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk21autoScalingWordpress`, `ManagedBy=CDK`); istanze e volumi creati dall'Auto Scaling group li ricevono dal launch template e da `PropagateAtLaunch`. Non hanno tag solo i tipi che CloudFormation non permette di taggare (regole dei security group, mount target EFS, listener, instance profile, policy IAM inline). Il test `test_all_resources_tagged` controlla ogni risorsa del template.

**Se il deploy fallisce con `Received 1 FAILURE signal(s) out of 1`**: lo script di avvio del server è terminato con un errore (`cfn-signal` manda il codice di uscita) e CloudFormation annulla lo stack, terminando anche l'istanza. Per leggere il log bisogna tenere l'istanza in vita, rifacendo il deploy senza rollback:
```bash
cdk deploy --no-rollback --parameters vpcid=$VPC_ID ...      # stessi parametri di prima
INSTANCE=$(aws ec2 describe-instances --region $AWS_REGION --filters "Name=tag:Project,Values=Development.aws.py-CDK.cdk21autoScalingWordpress" "Name=instance-state-name,Values=running" --query "Reservations[0].Instances[0].InstanceId" --output text)
aws ec2 get-console-output --region $AWS_REGION --instance-id $INSTANCE --latest --output text | grep -A3 -E "ERRORE cdk21|tentativo"
# oppure dentro l'istanza: aws ssm start-session --target $INSTANCE, poi sudo cat /var/log/cloud-init-output.log
cdk destroy     # poi si corregge e si rifà il deploy (uno stack in CREATE_FAILED va cancellato prima)
```
La riga `ERRORE cdk21: comando fallito alla riga N: <comando>` indica il comando che ha fermato lo script. Il mount di EFS, l'installazione dei pacchetti e il download di WordPress vengono già ripetuti fino a 30 volte, perché subito dopo la creazione il nome DNS del disco EFS può richiedere fino a 90 secondi. Se la VPC non ha `enableDnsHostnames` e `enableDnsSupport` attivi, il nome del disco non si risolve mai (nella VPC di default sono attivi).

**Verifica dei server** (Session Manager, serve il plugin della CLI):
```bash
ASG=$(aws cloudformation describe-stacks --stack-name Cdk21AutoScalingWordpressStack --query "Stacks[0].Outputs[?OutputKey=='AutoScalingGroupName'].OutputValue" --output text)
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $ASG --query "AutoScalingGroups[0].Instances[].[InstanceId,AvailabilityZone,HealthStatus]" --output table
aws ssm start-session --target i-xxxxxxxx
# dentro l'istanza
sudo cat /var/log/cloud-init-output.log
cat /mnt/efs/install.log /mnt/efs/wordpress/hostname.html
curl -s localhost/hostname.html
```
Nel file `install.log` la prima istanza scrive che ha installato WordPress, le successive che lo hanno trovato già presente.

**Provare lo scaling**: `aws autoscaling set-desired-capacity --auto-scaling-group-name $ASG --desired-capacity 2`; dopo qualche minuto `hostname.html` mostra due server. Le regole automatiche (allarmi sulla CPU) sono nel cdk22.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS. Lo stack ha costi fissi orari anche senza visite.

| Voce | Calcolo | Al mese (30 gg) |
|------|---------|-----------------|
| Application Load Balancer | 0,027 $/ora + LCU (traffico minimo) | ~20 $ |
| IP pubblici del load balancer | 2 × 0,005 $/ora | ~7 $ |
| EC2 `t3.micro` | 1 istanza × 0,012 $/ora (fino a 3 con lo scaling) | ~9 $ |
| EBS gp3 | 8 GB per istanza × 0,095 $/GB | ~1 $ |
| RDS `db.t4g.micro` | 0,017 $/ora + 20 GB gp3 | ~15 $ |
| EFS | poche centinaia di MB × 0,36 $/GB | < 0,50 $ |
| Secrets Manager | 1 segreto × 0,40 $ | 0,40 $ |
| **Totale** | | **~53 $** |

Il NAT gateway della VPC non è creato da questo stack: con subnet private serve ai server (circa 35 $/mese più il traffico, se non c'è già), con la VPC di default non serve e ogni server ha invece un IP pubblico (~3,60 $/mese). Conviene distruggere lo stack appena finita la prova.


## 🧹 Pulizia

```bash
cdk destroy
# verifica finale: risorse ancora presenti con i tag dell'esempio (la lista deve essere vuota,
# le risorse appena cancellate possono comparire ancora per qualche minuto)
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk21autoScalingWordpress --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il database si cancella **senza snapshot finale** e senza backup automatici: con dati da tenere, togliere `RemovalPolicy.DESTROY` (CDK crea allora uno snapshot, che ha un costo di storage)
- il file system EFS si cancella con tutti i file di WordPress, le istanze dell'Auto Scaling group e i loro volumi vengono terminati
- il bootstrap resta, perché è condiviso con gli altri progetti CDK: quando nella region non ci sono più stack CDK si toglie con `../bootstrap/bootstrap.sh destroy <region>`


## 🚀 Sviluppi Futuri
- 🔒 **HTTPS** sul load balancer con un certificato ACM e un record Route 53
- 🌍 **CloudFront** davanti al load balancer per la cache delle pagine e dei file statici
- 🗄️ **Aurora Serverless v2** al posto di RDS per scalare anche il database


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


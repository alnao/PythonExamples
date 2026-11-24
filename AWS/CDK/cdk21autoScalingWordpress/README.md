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
│   ├── naming.py                            # 🏷️ nomi aws-py-cdk21-<servizio> e tag Name di ogni risorsa
│   └── tags.py                              # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                              # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```

Lo stack è la base del [cdk22cloudWatchAlarm](../cdk22cloudWatchAlarm/), che lo estende con gli allarmi CloudWatch (come l'esempio 22 CloudFormation usava il 21 come stack annidato): per questo la classe espone `asg`, `alb`, `listener`, `target_group`, `database` e `file_system`.


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, la **VPC di default** della region (usata per default); meglio ancora, per un ambiente vero, una VPC con due subnet pubbliche e due subnet private con uscita su Internet (NAT gateway), passata con i parametri.

```bash
cd PythonExamples/AWS/CDK/cdk21autoScalingWordpress/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# test locali: sintesi dello stack, nessuna chiamata AWS
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid`, `publicsubnetids1`, `publicsubnetids2` (load balancer), `privatesubnetid1`, `privatesubnetid2` (server, database, EFS: per default le stesse subnet pubbliche) e `instancespublicip` (default `true`), che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`. Con una VPC che ha subnet private e NAT: `cdk deploy --parameters vpcid=... --parameters publicsubnetids1=... --parameters publicsubnetids2=... --parameters privatesubnetid1=... --parameters privatesubnetid2=... --parameters instancespublicip=false` (i server non hanno IP pubblico ed escono dal NAT).

**Con la VPC di default** non ci sono subnet private né NAT: i server, il database e i mount target EFS vanno nelle stesse subnet pubbliche del load balancer. I server ricevono un IP pubblico (escono su Internet senza NAT, ma costano 0,005 $/ora in più ciascuno) e restano raggiungibili solo dal load balancer, perché il loro security group accetta la porta 80 solo da lì; il database non è pubblico (`PubliclyAccessible=false`) e accetta solo i server. Per un ambiente vero conviene una VPC con subnet private e NAT.
Parametri facoltativi: `instancetype` (default `t3.micro`) e `dbname` (default `wordpress`). Il deploy dura circa 15 minuti, quasi tutti per il database.

Al termine `cdk deploy` stampa:
- `WebsiteURL`: l'indirizzo del sito, la prima visita apre l'installazione di WordPress (titolo, utente amministratore)
- `HealthURL`: la pagina del controllo di salute, con una riga per ogni server avviato
- `AutoScalingGroupName`, `DatabaseEndpoint`, `DatabaseSecretArn`, `FileSystemId`

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk21autoScalingWordpress`, `ManagedBy=CDK`); istanze e volumi creati dall'Auto Scaling group li ricevono dal launch template e da `PropagateAtLaunch`. Non hanno tag solo i tipi che CloudFormation non permette di taggare (regole dei security group, mount target EFS, listener, instance profile, policy IAM inline). Il test `test_all_resources_tagged` controlla ogni risorsa del template. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk21-<servizio>`, vedi `naming.py`).

**Se il deploy fallisce con `Received 1 FAILURE signal(s) out of 1`**: lo script di avvio del server è terminato con un errore (`cfn-signal` manda il codice di uscita) e CloudFormation annulla lo stack, terminando anche l'istanza. Per leggere il log bisogna tenere l'istanza in vita, rifacendo il deploy senza rollback:
```bash
cdk deploy --no-rollback                    # con gli stessi eventuali parametri di prima
INSTANCE=$(aws ec2 describe-instances --region $AWS_REGION --filters "Name=tag:Project,Values=Development.aws.py-CDK.cdk21autoScalingWordpress" "Name=instance-state-name,Values=running" --query "Reservations[0].Instances[0].InstanceId" --output text)
aws ec2 get-console-output --region $AWS_REGION --instance-id $INSTANCE --latest --output text | grep -A3 -E "ERRORE cdk21|tentativo"
# oppure dentro l'istanza: aws ssm start-session --target $INSTANCE, poi sudo cat /var/log/cloud-init-output.log
cdk destroy     # poi si corregge e si rifà il deploy (uno stack in CREATE_FAILED va cancellato prima)
```
La riga `ERRORE cdk21: comando fallito alla riga N: <comando>` indica il comando che ha fermato lo script. Il mount di EFS, l'installazione dei pacchetti e il download di WordPress vengono già ripetuti fino a 30 volte, perché subito dopo la creazione il nome DNS del disco EFS può richiedere fino a 90 secondi. Se la VPC non ha `enableDnsHostnames` e `enableDnsSupport` attivi, il nome del disco non si risolve mai (nella VPC di default sono attivi).

Se il log mostra `mount.nfs4: access denied by server while mounting`, il problema è l'autorizzazione al mount EFS: lo script usa ora `mount -t efs -o tls,iam` e `/etc/fstab` usa `tls,iam`, perché il ruolo EC2 deve autorizzare sia il mount sia la scrittura tramite IAM.


**Verifica dei server** (Session Manager, serve il plugin della CLI):
```bash
ASG=$(aws cloudformation describe-stacks --stack-name aws-py-cdk21 --query "Stacks[0].Outputs[?OutputKey=='AutoScalingGroupName'].OutputValue" --output text)
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


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-10 | Prima versione dell'esempio, ispirata all'esempio CloudFormation corrispondente |
| 2026-11-17 | Revisione degli esempi CDK: test eseguiti e tag standard verificati su tutte le risorse del template sintetizzato, nessuna modifica al codice |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | tags.py: aspect LambdaLogGroups comune a tutti gli esempi (log group dello stack per ogni Lambda); lo stack non ha Lambda, il template non cambia |
| 2026-11-17 | Nomi delle risorse aws-py-cdk21-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk21, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named; il tag Name dell'Auto Scaling group non passa alle istanze (hanno il loro dal launch template) |
| 2026-11-17 | Tag Name aws-py-cdk21 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |
| 2026-11-24 | Mount EFS autorizzato con IAM: tls,iam e policy esplicita |


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


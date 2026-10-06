# AlNao AWS Manager

Applicazione web **Flask + Bootstrap 5** che riunisce in un'unica interfaccia i tool della
cartella [AWS/Managers](../Managers/): Cost Explorer, Panoramic, Tag Manager, Manager dei
servizi e CloudWatch. Una sola navbar, una sola configurazione e una grafica unica, compatta
(caratteri piccoli), uguale per tutte le sezioni.

| Sezione | Da dove viene | Cosa fa |
|---|---|---|
| **Home** | nuova | riepilogo dei costi (solo cache, gratis) e delle risorse attive |
| **Cost Explorer** | `Managers/CostExplorer` | costi per servizio e per tag, zoom, dettaglio per usage type, Data Export |
| **Panoramic** | `Managers/PanoramicResources` | panoramica delle risorse dell'account, servizio per servizio |
| **Tag Manager** | `Managers/TagManager` | elenco e modifica dei tag, report multi-region |
| **Manager** | `Managers/ManagerFlask` (+ Security Group del `ManagerTk`) | gestione di 26 servizi con una seconda barra |
| **CloudWatch** | `Managers/ManagerFlaskCloudWatch` | allarmi e log |
| **Terraform** | nuova | risorse gestite da Terraform, dagli state sui bucket S3, con tipo, region e tag |
| **CloudFormation** | nuova | risorse gestite da CloudFormation, stack per stack, con tipo, region e tag |

Il `ManagerTk` (tkinter) non è stato portato; da lui arriva solo la gestione dei Security Group.

## Profilo e region

- il **profilo AWS** si sceglie nella navbar (tendina con i profili di `~/.aws`) e vale per
  tutte le sezioni
- la **region** si sceglie dentro le sezioni che la usano (Home, Panoramic, Tag Manager,
  Manager, CloudWatch); la scelta resta valida passando da una sezione all'altra.
  L'opzione **"Tutte"** legge in parallelo tutte le region della lista (`regions` in
  `config.json`): ogni risorsa mostra la sua region e dettagli e modifiche vengono fatti
  in quella. Le poche operazioni che creano qualcosa (un allarme, un log group) chiedono
  di scegliere una region precisa
- nel **Cost Explorer** la tendina "Region costi" è invece un filtro sui costi (default
  "Tutte"), indipendente dalle altre sezioni
- cambiare profilo o region ricarica la pagina

Entrambi sono salvati nella sessione Flask (un cookie); le API accettano comunque i
parametri `profile` e `region`.

## Conferma di ogni modifica

Ogni operazione che modifica risorse AWS apre una finestra di conferma con cosa verrà
fatto, il profilo e la region: avvio e arresto di EC2, nuova regola di un Security Group,
invalidazione CloudFront, modifica di un parametro SSM, attivazione di una regola
EventBridge, invio e ricezione di messaggi SQS (la ricezione li cancella), pubblicazione
SNS, upload su S3, tutte le modifiche dei tag, operazioni su allarmi, log group, stream ed
eventi di log, aggiornamento della lista delle region. Le letture non chiedono conferma.

## Icone dei tag (Manager e Panoramic)

Dopo il nome di ogni risorsa un'icona dice se ha i tag previsti dal Tag Manager
(regole in `config.json`), con il dettaglio nel tooltip:

| icona | quando |
|---|---|
| ℹ️ azzurra, "aws automatic" | un tag vale `aws_auto`: risorsa gestita in automatico, esente dalla regola |
| ⚠️ rossa, "Tag mancanti: ..." | manca almeno un tag di `tag_manager.required_tags` e la risorsa non rientra in un set di `compliant_tags` |
| 🏷️ verde | tag presenti: il tooltip mostra i tag standard (le chiavi di `suggested_tags`) con i valori |

I tag vengono dall'elenco di AWS quando li contiene (EC2, security group, RDS, EFS, ASG,
Elastic IP, API Gateway, VPC, subnet, EKS, Secrets Manager), altrimenti dalla Tagging API
per ARN, usando la stessa cache del Tag Manager (1 ora, `tag_manager.cache_ttl`; le modifiche
fatte dal Tag Manager la aggiornano). Una risorsa che la Tagging API non conosce non ha tag.
Se una region non si riesce a leggere, o per i servizi non coperti (utenti e ruoli IAM, nodi
EKS), l'icona non compare.

## Costi: le chiamate a Cost Explorer si pagano

Ogni richiesta a Cost Explorer costa **0,01 $**, quindi valgono le regole del CostExplorer
originale:

- la sezione Cost Explorer non chiama mai AWS da sola: legge la cache e, se manca qualcosa,
  propone **"Carica i dati dal cloud"** con una modale che elenca richieste e costo
- la cache su disco non scade ed è divisa per mese (`cache/costs/<filtri>/YYYY-MM.json`);
  nulla viene cancellato
- il **Data Export** (CUR 2.0) su S3 è la fonte gratuita: si configura nel file `.env`
  (modello `.env.example`)
- la **Home** mostra i costi solo da cache e Data Export: per i mesi mancanti rimanda al
  Cost Explorer. Usa la serie col raggruppamento di default (`TAG:Project`) se c'è,
  altrimenti una qualsiasi già in cache per lo stesso profilo e metrica

La cartella `cache/` e il file `.env` sono stati copiati da `Managers/CostExplorer`: i dati
già pagati restano disponibili.

Il periodo di partenza è **3M** (`cost_explorer.default_months`). Nelle tabelle sotto i
grafici la freccia accanto a un valore apre e chiude i suoi sottovalori (es. i sottoproject di
Project, chiusi all'apertura) e la lente in fondo alla riga filtra grafici e tabelle su quella voce (un secondo
clic toglie il filtro); per i servizi c'è anche il dettaglio per usage type.

Dettagli su zoom, filtri incrociati, sottovalori di Project, dettaglio per usage type e
Data Export: vedere il [README del CostExplorer](../Managers/CostExplorer/README.md) (le
funzionalità sono le stesse).

## Sezioni

### Home
- **Costi**: mese in corso (con la stima a fine mese se già calcolata oggi), mese precedente
  con la variazione, totale degli ultimi 3 mesi, quota dei costi senza tag, fonte di ogni mese
  e i primi 10 costi del mese (con il mese prima in grigio), con la tendina **Raggruppa per**:
  servizio o un tag di `suggested_tags` (prima Project e CostCenter). Per un tag servono il
  Data Export o una serie con quel tag già in cache (si carica dal Cost Explorer scegliendo il
  tag in "Secondo grafico per"); la scelta resta salvata nel browser
- **Risorse attive**: una tabella con una riga per ogni region di `regions` (config.json), una
  per i servizi globali e il totale; colonne EC2 accese, RDS disponibili, funzioni Lambda,
  tabelle DynamoDB, bucket S3 (nella riga della region del bucket), distribuzioni CloudFront
  (globali), load balancer, Elastic IP non associati e allarmi in ALARM. Le celle che costano
  anche senza uso sono evidenziate. Le letture (describe/list) sono gratuite

### Panoramic
Non legge nulla all'apertura: **Servizi principali** legge i servizi elencati in
`panoramic.main_services`, **Tutti i servizi** tutti i 27 (VPC di default e subnet, security
group, EC2, RDS, S3, CloudFront, Lambda, DynamoDB, API Gateway REST e HTTP, SQS, SNS, ECR, EKS e
nodi, CloudFormation, allarmi, utenti e ruoli IAM, Route 53, ElastiCache, load balancer,
Secrets Manager, parametri SSM, Kinesis, Step Functions, EFS). Indice con i conteggi, ricerca
in tutte le tabelle, "Nascondi servizi vuoti"; gli errori (es. permessi) sono indicati nella
sezione del servizio.

### Tag Manager
Come il TagManager originale (Tagging API + Resource Explorer, filtri, tag rapido, gestione
in massa, tag suggeriti e obbligatori, risorse di sistema), in più la region **"Tutte"**. I
tag obbligatori (`tag_manager.required_tags`) e le chiavi con i sottovalori
(`tag_manager.prefix_match_keys`) ora sono in `config.json`. Il **report multi-region** ha una
colonna per ogni tag suggerito.

### Manager
Seconda barra con i servizi: S3 (navigazione per cartelle, download con URL firmato, upload),
EC2 (dettaglio, avvio e arresto), Security Group (regole, nuova regola in ingresso),
CloudFront (origini, invalidazioni), SSM Parameter Store (modifica del valore), Lambda
(configurazione, invocazioni delle ultime 24 ore, ultimi log), EventBridge (event pattern,
target, attiva/disattiva), Step Functions (definizione ed esecuzioni), API Gateway (risorse e
stage), DynamoDB (righe a richiesta, vedi sotto), RDS, Glue (job ed esecuzioni), SQS (invio e
ricezione), SNS (sottoscrizioni e pubblicazione), Elastic IP, EFS (mount target), Auto Scaling
Group, load balancer (listener, target e salute), CloudWatch Alarms e Logs (vista semplice,
la gestione completa è nella sezione CloudWatch), ECR (immagini) e, in sola lettura,
CloudFormation (parametri, output, risorse, eventi e template), Route 53 (zone e record), Secrets
Manager (metadati e versioni; il valore solo con **Mostra valore**), ECS (cluster, servizi e task)
e VPC (subnet, route table, internet e NAT gateway). Tre colonne: elenco con
ricerca, dettaglio, sotto-risorse e azioni. Le proprietà della risorsa si aprono con i tag di
`suggested_tags` (nome in un badge blu con l'icona del tag) e il loro valore, con il badge rosso
"mancante" se il tag non c'è.

**DynamoDB**, pensato anche per tabelle molto grandi: aprire una tabella legge solo la
descrizione (`DescribeTable`, con numero di righe e dimensione stimati da AWS), le righe si
leggono con **Carica dati**, una pagina alla volta (25-500 righe), e **Carica altre righe**
riparte dall'ultima chiave letta. Le informazioni della tabella (con i tag) stanno al centro,
ricerca e dati a destra, in una colonna più larga.
- con il valore della **partition key** (della tabella o di un indice GSI/LSI) è una
  **Query**: legge solo quella partizione, con l'eventuale condizione sulla sort key
  (`=`, `<`, `≤`, `>`, `≥`, inizia con, tra) e l'ordine crescente o decrescente
- senza partition key è uno **Scan** della tabella o dell'indice
- il **filtro su un attributo** (`=`, `≠`, confronti, contiene, inizia con, esiste, non esiste;
  valore stringa, numero o booleano) si applica dopo la lettura: riduce le righe mostrate, non
  quelle lette. Uno Scan con filtro si ferma dopo `manager.dynamodb_max_read` righe lette
- sopra la tabella: righe mostrate, righe lette e RCU consumate; clic su una riga per vederla
  intera al posto delle informazioni (con il pulsante per tornare alla descrizione)

### CloudWatch
- **Allarmi**: elenco con filtro per stato e ricerca, storico, stato forzato, attivazione e
  disattivazione delle azioni, cancellazione, nuovo allarme sulla CPU di un Auto Scaling Group
- **Log**: log group con filtro per prefisso, stream, ultimi eventi, ricerca con un filter
  pattern (ultima ora, 24 ore, 7 o 30 giorni), creazione e cancellazione di gruppi e stream,
  scrittura di un evento

### Terraform
Risorse gestite da Terraform, lette dagli state (backend s3) sui bucket elencati in
`terraform.buckets`. Non legge nulla all'apertura: si sceglie un bucket o **Tutti** (la scelta
resta salvata nel browser) e si preme **Carica**.
- legge i file che finiscono con `terraform.state_suffixes` (`.tfstate`, i `.tfstate.backup`
  restano fuori), al massimo `terraform.max_states` per bucket; formato state versione 4
  (Terraform 0.12 e successivi)
- al browser arrivano solo indirizzo, tipo, nome, id, ARN, region, provider e tag di ogni
  risorsa: gli altri attributi degli state (spesso password e chiavi in chiaro) restano sul
  server. Uno state con lo stesso ETag non viene riscaricato (cache in memoria)
- region dall'attributo `region`, dall'ARN o dalla zona di disponibilità; "globale" per gli
  ARN senza region (IAM, CloudFront...)
- tabella degli state letti con versione di Terraform, serial, numero di risorse e output,
  errori per bucket o file
- tabella delle risorse ordinabile, con filtri per testo, tipo, region, state, **tag** (chiave,
  di default Project, e valore: solo i valori presenti, con il numero di risorse e
  "(senza tag)"; per Project i sottovalori sotto il padre come nel Tag Manager), data source
  (nascoste di default) e "Solo tag mancanti"; clic su una riga per la sottotabella dei tag
  (`tags_all`, cioè con i `default_tags` del provider): prima quelli di `suggested_tags`, con il
  badge rosso "mancante", poi gli altri

Permessi IAM: `s3:ListBucket` e `s3:GetObject` sui bucket degli state.

### CloudFormation
Risorse gestite da CloudFormation nella region scelta o in tutte (il Manager ha anche la
vista del singolo stack con eventi e template). Non legge nulla all'apertura: si preme
**Carica**.
- stack con `describe_stacks` (nested compresi, sotto il loro padre) e risorse di ogni stack
  con `list_stack_resources`, in parallelo
- i **tag** delle risorse vengono dalla Tagging API con la cache del Tag Manager (fino a
  un'ora; **Rileggi i tag** la aggiorna): CloudFormation mette su ogni risorsa che crea i tag
  `aws:cloudformation:stack-id` e `aws:cloudformation:logical-id`, che legano la risorsa allo
  stack e danno il suo ARN. Si leggono le region degli stack più us-east-1 (risorse globali come
  CloudFront). Una risorsa che non compare non ha tag (tipo senza tag); per uno stack nested
  valgono i tag dello stack
- tabella degli stack (stato, drift, Project, numero di risorse, protezione dalla
  cancellazione, descrizione): clic su uno stack per filtrarne le risorse
- tabella delle risorse ordinabile (risorsa, tipo, ID fisico, region, stack, stato con drift,
  Project, tag) con gli stessi filtri di Terraform (testo, tipo, region, tag con valore,
  "Solo tag mancanti") più stack e stato; clic su una riga per la sottotabella dei tag (i tag di
  sistema `aws:*` in fondo), con ARN, stack e motivo dello stato

Permessi IAM: `cloudformation:DescribeStacks`, `cloudformation:ListStackResources`,
`tag:GetResources`.

## Prerequisiti

- Python 3.8+ (il repository usa il venv condiviso `.venv` con Python 3.13)
- credenziali AWS configurate (`~/.aws/credentials` o variabili d'ambiente)
- permessi IAM di lettura sui servizi da consultare e, per le modifiche, quelli delle singole
  operazioni; per i costi `ce:GetCostAndUsage`, `ce:GetCostForecast`,
  `ce:ListCostAllocationTags` e, per il Data Export, `s3:ListBucket` e `s3:GetObject` sul bucket;
  per i tag `tag:*` e `resource-explorer-2:GetDefaultView`, `resource-explorer-2:Search`

## Installazione ed esecuzione

```bash
cd AWS/Manager
pip3 install -r requirements.txt
cp .env.example .env      # facoltativo: Data Export per i costi
./start.sh                # oppure: python3 app.py
```

Poi aprire [http://localhost:5042](http://localhost:5042). L'app ascolta solo su `127.0.0.1`
perché può modificare risorse AWS: per esporla in rete impostare `HOST=0.0.0.0`.

## Configurazione

Un solo `config.json` con i parametri di tutti i tool:

| chiave | descrizione |
|---|---|
| `port` | porta dell'app (`5042`, variabile `PORT`) |
| `default_profile`, `default_region` | valori iniziali (variabili `AWS_PROFILE`, `AWS_REGION`) |
| `regions` | region delle tendine e di "Tutte" (variabile `AWS_REGIONS`); il pulsante 🌍 del Tag Manager la rilegge da AWS |
| `old_regions` | region non usate, tenute come promemoria |
| `max_workers` | letture in parallelo sulle region |
| `suggested_tags` | tag suggeriti e loro valori (Tag Manager e Cost Explorer) |
| `compliant_tags` | set di tag che rendono una risorsa conforme anche senza i tag obbligatori |
| `resources_skipped` | risorse di sistema da non segnalare |
| `tag_manager` | `required_tags`, `prefix_match_keys`, `cache_ttl` (secondi), `page_size` |
| `cost_explorer` | `default_months`, `default_metric`, `default_group`, `prefix_match_keys`, `cur_service_names`, `service_aliases` |
| `panoramic` | `main_services`: servizi del pulsante "Servizi principali" |
| `terraform` | `buckets` (bucket con gli state), `state_suffixes` (suffissi dei file di state), `max_states` (state letti al massimo per bucket) |
| `manager` | `max_upload_mb` (upload su S3), `list_limit` (oggetti S3, righe DynamoDB per pagina, esecuzioni), `logs_limit` (eventi di log), `dynamodb_max_read` (righe lette al massimo da uno Scan con filtro a ogni clic) |

## Struttura del progetto

```
Manager/
├── app.py                  # applicazione Flask: navbar, profilo/region in sessione, blueprint
├── common.py               # config.json, profilo e region della richiesta, sessioni boto3, parallelo, JSON
├── config.json             # configurazione unica
├── requirements.txt
├── start.sh                # avvio con il venv del repository
├── .env.example            # Data Export per i costi (copiare in .env)
├── cache/                  # cache dei costi (copiata dal CostExplorer, non versionata)
├── sections/               # un blueprint per voce della navbar: pagine e API REST
│   ├── home.py
│   ├── costexplorer.py
│   ├── panoramic.py
│   ├── tagmanager.py
│   ├── manager.py          # registro dei 26 servizi: elenco, letture, azioni
│   ├── cloudwatch.py
│   ├── terraform.py
│   └── cloudformation.py
├── aws/                    # classi boto3, senza Flask
│   ├── cost_explorer.py, cost_cache.py, cur_source.py
│   ├── tag_manager.py
│   ├── cloudwatch_manager.py
│   ├── panoramic.py        # i 27 servizi della panoramica
│   ├── summary.py          # contatori della Home
│   ├── terraform_states.py # state di Terraform su S3: elenco, lettura, riassunto sicuro
│   ├── cloudformation_resources.py  # stack, risorse e tag di CloudFormation
│   └── services/           # l'SDK di AWS/SDK riscritto con boto3.Session(profilo, region)
├── templates/              # base.html (navbar, conferma), _macros.html, una pagina per sezione
└── static/
    ├── css/app.css         # grafica unica
    └── js/                 # common.js (API, messaggi, conferme), iac_common.js (Terraform e CloudFormation) e un file per sezione
```

## API REST

| Prefisso | Sezione |
|---|---|
| `POST /api/context` | salva profilo (`profile`) e/o region (`region`, `__all__` = tutte) |
| `/api/home/costs`, `/api/home/costs/group?group=TAG:<chiave>`, `/api/home/resources` | Home |
| `/api/ce/tags`, `/api/ce/costs`, `/api/ce/forecast`, `/api/ce/drilldown`, `/api/ce/cur/status` | Cost Explorer (stessi parametri dell'originale, `cache_only=1` e `refresh=1`) |
| `/api/panoramic/resources?scope=main\|all` | Panoramic |
| `/api/tags/resources`, `/api/tags/tag-keys`, `/api/tags/tag-values`, `/api/tags/add`, `/api/tags/remove`, `/api/tags/report/resources`, `/api/tags/regions/refresh` | Tag Manager |
| `GET /api/manager/<servizio>/list`, `GET /api/manager/<servizio>/<lettura>`, `POST /api/manager/<servizio>/<azione>`, `/api/manager/s3/download`, `/api/manager/s3/upload` | Manager |
| `/api/cloudwatch/alarms...`, `/api/cloudwatch/logs/...` | CloudWatch (nomi di gruppi e stream come parametri, non nel percorso) |
| `/api/terraform/resources?bucket=<bucket>` | Terraform (senza `bucket`: tutti quelli di `terraform.buckets`) |
| `/api/cloudformation/resources?region=<region>&refresh=1` | CloudFormation (`__all__` = tutte le region, `refresh=1` rilegge i tag) |

## Note tecniche

- le classi di `AWS/SDK` cambiavano la sessione di default di boto3 a ogni chiamata e quasi
  tutte ignoravano la region: in `aws/services/` ricevono una sessione già legata a profilo e
  region, così le letture in parallelo su più region non si pestano i piedi
- le liste usano i paginatori di boto3 (gli originali leggevano solo la prima pagina)
- l'upload su S3 passa direttamente dalla richiesta al bucket, senza file temporanei; il
  download usa un URL firmato nella region del bucket
- le risposte di boto3 (date, `Decimal` di DynamoDB) sono convertite in JSON da `common.JsonProvider`

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

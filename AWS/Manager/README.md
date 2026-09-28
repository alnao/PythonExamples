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
| **Manager** | `Managers/ManagerFlask` (+ Security Group del `ManagerTk`) | gestione di 21 servizi con una seconda barra |
| **CloudWatch** | `Managers/ManagerFlaskCloudWatch` | allarmi e log |

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

Dettagli su zoom, filtri incrociati, sottovalori di Project, dettaglio per usage type e
Data Export: vedere il [README del CostExplorer](../Managers/CostExplorer/README.md) (le
funzionalità sono le stesse).

## Sezioni

### Home
- **Costi**: mese in corso (con la stima a fine mese se già calcolata oggi), mese precedente
  con la variazione, totale degli ultimi 3 mesi, quota dei costi senza tag, primi servizi del
  mese confrontati col mese prima, fonte di ogni mese
- **Risorse attive** nella region scelta o in tutte: EC2 accese, RDS disponibili, funzioni
  Lambda, tabelle DynamoDB, load balancer, NAT Gateway, Elastic IP non associati, allarmi in
  ALARM, bucket S3 e distribuzioni CloudFront; le voci che costano anche senza uso sono
  evidenziate. Le letture (describe/list) sono gratuite

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
stage), DynamoDB (prime righe della tabella), RDS, Glue (job ed esecuzioni), SQS (invio e
ricezione), SNS (sottoscrizioni e pubblicazione), Elastic IP, EFS (mount target), Auto Scaling
Group, load balancer (listener, target e salute), CloudWatch Alarms e Logs (vista semplice,
la gestione completa è nella sezione CloudWatch) ed ECR (immagini). Tre colonne: elenco con
ricerca, dettaglio, sotto-risorse e azioni.

### CloudWatch
- **Allarmi**: elenco con filtro per stato e ricerca, storico, stato forzato, attivazione e
  disattivazione delle azioni, cancellazione, nuovo allarme sulla CPU di un Auto Scaling Group
- **Log**: log group con filtro per prefisso, stream, ultimi eventi, ricerca con un filter
  pattern (ultima ora, 24 ore, 7 o 30 giorni), creazione e cancellazione di gruppi e stream,
  scrittura di un evento

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
| `manager` | `max_upload_mb` (upload su S3), `list_limit` (oggetti S3, righe DynamoDB, esecuzioni), `logs_limit` (eventi di log) |

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
│   ├── manager.py          # registro dei 21 servizi: elenco, letture, azioni
│   └── cloudwatch.py
├── aws/                    # classi boto3, senza Flask
│   ├── cost_explorer.py, cost_cache.py, cur_source.py
│   ├── tag_manager.py
│   ├── cloudwatch_manager.py
│   ├── panoramic.py        # i 27 servizi della panoramica
│   ├── summary.py          # contatori della Home
│   └── services/           # l'SDK di AWS/SDK riscritto con boto3.Session(profilo, region)
├── templates/              # base.html (navbar, conferma), _macros.html, una pagina per sezione
└── static/
    ├── css/app.css         # grafica unica
    └── js/                 # common.js (API, messaggi, conferme) e un file per sezione
```

## API REST

| Prefisso | Sezione |
|---|---|
| `POST /api/context` | salva profilo (`profile`) e/o region (`region`, `__all__` = tutte) |
| `/api/home/costs`, `/api/home/resources` | Home |
| `/api/ce/tags`, `/api/ce/costs`, `/api/ce/forecast`, `/api/ce/drilldown`, `/api/ce/cur/status` | Cost Explorer (stessi parametri dell'originale, `cache_only=1` e `refresh=1`) |
| `/api/panoramic/resources?scope=main\|all` | Panoramic |
| `/api/tags/resources`, `/api/tags/tag-keys`, `/api/tags/tag-values`, `/api/tags/add`, `/api/tags/remove`, `/api/tags/report/resources`, `/api/tags/regions/refresh` | Tag Manager |
| `GET /api/manager/<servizio>/list`, `GET /api/manager/<servizio>/<lettura>`, `POST /api/manager/<servizio>/<azione>`, `/api/manager/s3/download`, `/api/manager/s3/upload` | Manager |
| `/api/cloudwatch/alarms...`, `/api/cloudwatch/logs/...` | CloudWatch (nomi di gruppi e stream come parametri, non nel percorso) |

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

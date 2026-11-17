# AWS CDK 12 - Lambda Application S3 Utils

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'applicazione **serverless** che lavora sui file di un bucket **S3**: gli zip caricati vengono estratti, gli Excel convertiti in CSV e i CSV caricati in un database **Aurora MySQL**, con log su **DynamoDB**, **API REST**, una **pagina web** e una scansione notturna del bucket. Versione CDK in Python dell'esempio CloudFormation/SAM [Esempio12lambdaApplicationS3Utils](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio12lambdaApplicationS3Utils).

- **📦 Catena di elaborazione** con regole EventBridge sugli eventi *Object Created* del bucket:
  - `INPUT/*.zip` (anche `.tar`, `.tar.gz`, `.tgz`) → Lambda **Decompress** → file estratti in `DEZIPPED/` (i percorsi con `../` restano dentro la cartella)
  - `DEZIPPED/*.xlsx` → Lambda **ConvertToCsv** (openpyxl) → primo foglio in `CSV/<nome>.csv`
  - `CSV/*.csv` → Lambda **ProcessCsv** → righe nella tabella `es12table` del database (creata al primo CSV con le sue colonne, `VARCHAR(100)`; le colonne che la tabella non ha vengono ignorate e scritte nel log) e una riga di log nella tabella DynamoDB `aws-py-cdk12-log`
  - `TOSENDSFTP/*` → Lambda **SendSftp** → server SFTP (facoltativa, con `-c sftp_host=...`)
- **🗄️ Aurora MySQL Serverless v2** con pausa automatica a 0 ACU dopo 5 minuti e **Data API**: le Lambda parlano con il database via HTTPS, senza stare nella VPC; il database riparte da solo alla prima richiesta (le Lambda riprovano finché è pronto)
- **🔍 Scansione notturna** (01:00 UTC) di tutti i file del bucket nella tabella `aws-py-cdk12-scan`: `nuovo=S` la prima volta che un file viene visto, `N` le volte successive; indici per cercare i file nuovi e per nome
- **🌐 API REST** (stage `dev`, CORS) con una Lambda per ogni percorso GET: `upload-zip` (URL prefirmato per caricare lo zip), `list-excel-files`, `download-excel-file` (URL prefirmato, solo Excel di `DEZIPPED/`), `read-rds-data`, `read-dynamodb-data`, `list-new-files`, `find-file`
- **🖥️ Pagina web** (Bootstrap 5) su S3 privato dietro CloudFront: carica gli zip, elenca e scarica gli Excel, mostra log, tabella del database (filtrabile), file nuovi e ricerca per nome
- **🔔 Allarmi CloudWatch** su errori di ProcessCsv e ReadRdsData e sui 5xx dell'API, verso un topic SNS (email con `-c alarm_email=...`)

| | CloudFormation/SAM (Esempio12) | CDK (cdk12) |
|---|---|---|
| Database | Aurora MySQL `db.t4g.medium` (o Serverless v2 con parametro), driver MySQL | Aurora Serverless v2 con pausa a 0 ACU, Data API |
| Lambda e database | Lambda nella VPC + VPC endpoint Secrets Manager (~17 $/mese) | Lambda fuori dalla VPC, nessun endpoint |
| Librerie | pandas, mysql-connector, paramiko (`sam build`) | openpyxl e paramiko in un layer creato da `build_layer.sh` (senza Docker) |
| Bucket | accesso pubblico abilitato con una policy | privato, upload e download con URL prefirmati |
| DynamoDB | provisioned 5/5 (~10 $/mese fuori free tier) | on-demand |
| Log di API Gateway | log di esecuzione con `AWS::ApiGateway::Account` (impostazione di tutto l'account) | solo metriche, nessuna impostazione di account |
| SFTP | sempre presente, parametri obbligatori | facoltativo, con il context |
| Pagina web | da avviare in locale con `python3 -m http.server` | su CloudFront, `config.js` scritto al deploy |
| Costo fisso | ~80-90 $/mese | ~1 $/mese (database in pausa) |

Correzioni rispetto alle Lambda del CloudFormation: `find-file` e `list-new-files` restituivano una lista invece di una stringa JSON (API Gateway rispondeva 502), la lettura dei log falliva con i numeri DynamoDB (`Decimal`), i nomi delle colonne del CSV finivano nella query SQL così com'erano (ora solo lettere, numeri e `_`), gli errori di ProcessCsv non arrivavano all'allarme perché la Lambda rispondeva 500 senza fallire.


## 🔧 Architettura

```
pagina web (CloudFront) ── API REST /dev ── Lambda API ──┬── URL prefirmati S3 (upload in INPUT/, download da DEZIPPED/)
                                                          ├── DynamoDB aws-py-cdk12-log, aws-py-cdk12-scan
                                                          └── Data API ── Aurora MySQL Serverless v2 (0-2 ACU)
bucket S3 ── EventBridge
  INPUT/*.zip      ── Decompress   ── DEZIPPED/
  DEZIPPED/*.xlsx  ── ConvertToCsv ── CSV/
  CSV/*.csv        ── ProcessCsv   ── Data API: CREATE TABLE / INSERT ── log in DynamoDB
  TOSENDSFTP/*     ── SendSftp (facoltativa) ── server SFTP (chiave in SSM)
EventBridge 01:00 UTC ── ScanS3 ── DynamoDB aws-py-cdk12-scan
CloudWatch (errori, 5xx) ── SNS aws-py-cdk12-alarms ── email (facoltativa)
```

```
├── app.py                                      # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk12lambda_application_s3_utils/
│   ├── cdk12lambda_application_s3_utils_stack.py  # 🏗️ bucket, tabelle, Aurora, layer, Lambda, regole, API, allarmi, sito
│   ├── naming.py                               # 🏷️ nomi aws-py-cdk12-<servizio> e tag Name di ogni risorsa
│   └── tags.py                                 # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/
│   ├── common.py                               # 🔧 client, risposte con CORS, chiave S3 dall'evento
│   ├── files.py                                # 📦 Decompress e ConvertToCsv
│   ├── database.py                             # 🗄️ ProcessCsv e ReadRdsData (Data API)
│   ├── api.py                                  # 🌐 Lambda delle API
│   ├── scan.py                                 # 🔍 scansione del bucket
│   ├── sftp.py                                 # 📤 invio SFTP (facoltativo)
│   └── requirements.txt                        # 📚 librerie del layer (openpyxl, paramiko)
├── build_layer.sh                              # 🧱 crea layer/ con le wheel ARM64 per Python 3.13
├── web/index.html                              # 🖥️ pagina web
├── tests/unit/                                 # 🧪 test dello stack e delle Lambda con S3, Data API e DynamoDB finti
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk12lambdaApplicationS3Utils/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit
./build_layer.sh                 # layer/ con openpyxl e paramiko (va rifatto se cambia lambda/requirements.txt)

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
#   facoltativi: -c alarm_email=nome@example.com
#                -c sftp_host=<host> -c sftp_user=<utente> -c sftp_port=22 -c sftp_key_param=/cdk12/sftp/private-key
```

**VPC e subnet**: per default lo stack usa la **VPC di default** della region e le sue subnet: CDK le legge al `cdk synth`/`cdk deploy` (chiamate di sola lettura con le credenziali del deploy) e le salva in `cdk.context.json`, che non va su git. I valori sono i default dei parametri `vpcid`, `subnetid1` e `subnetid2` (subnet del database), che si possono cambiare al deploy (`cdk deploy --parameters vpcid=vpc-xxx --parameters ...`, tutti i parametri della rete insieme); con `cdk deploy -c vpc_id=vpc-xxx` i default vengono presi da un'altra VPC. Se la region non ha più la VPC di default si ricrea con `aws ec2 create-default-vpc`.

Il cluster Aurora impiega circa 10 minuti a essere creato.

Per l'invio SFTP la chiave privata va salvata prima in SSM come SecureString (lo stack ne conosce solo il nome):
```bash
aws ssm put-parameter --name /cdk12/sftp/private-key --type SecureString --value file://chiave_privata.pem
```

Verifica:
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk12 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
# zip con un Excel di prova (serve openpyxl, gia' nei requirements-dev)
python3 -c "import openpyxl; wb=openpyxl.Workbook(); [wb.active.append(r) for r in [['Nome','Cognome','Eta'],['Alberto','Nao',24],['Andrea','Nao',44]]]; wb.save('/tmp/persone.xlsx')"
(cd /tmp && zip -q persone.zip persone.xlsx)
aws s3 cp /tmp/persone.zip s3://$(out BucketName)/INPUT/persone.zip
sleep 60      # estrazione, conversione e ripresa del database dalla pausa
aws s3 ls s3://$(out BucketName)/ --recursive
API=$(out ApiUrl)
curl ${API}read-dynamodb-data
curl ${API}read-rds-data          # se risponde 503 il database sta ripartendo: riprovare dopo qualche secondo
curl "${API}find-file?nomeFile=persone.csv"
echo "pagina web: $(out SiteUrl)"
```
La tabella della scansione si riempie alle 01:00 UTC; per provarla subito: `aws lambda invoke --function-name aws-py-cdk12-scan-s3 /tmp/scan.json && cat /tmp/scan.json`.

**Tag**: bucket, tabelle DynamoDB, cluster Aurora (istanza, subnet group, security group, segreto), layer, Lambda, ruoli, log group, regole EventBridge, API e stage, allarmi, topic, distribuzione CloudFront e Lambda di supporto di CDK hanno i tag standard (`Project=Development.aws.py-CDK.cdk12lambdaApplicationS3Utils`, `ManagedBy=CDK`); policy, permessi, configurazioni di invocazione delle Lambda, risorse e metodi dell'API, Origin Access Control e iscrizioni SNS non accettano tag. Le interfacce di rete del cluster Aurora sono gestite da RDS e non hanno tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk12-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Aurora Serverless v2 | ~0,14 $ per ACU-ora solo quando è attivo (0,5-2 ACU), 0 ACU in pausa | ~0 $ a riposo, ~0,10 $ per ogni ora di prove |
| Storage Aurora | ~0,11 $/GB al mese + I/O | ~0 $ (pochi MB) |
| Secrets Manager | 0,40 $ per segreto | 0,40 $ |
| Allarmi CloudWatch | 3 × 0,10 $ (10 gratuiti) | 0-0,30 $ |
| Lambda, API Gateway, DynamoDB on-demand, EventBridge, S3, CloudFront | a consumo, in gran parte nel free tier | ~0 $ per i test |
| **Totale fisso** | | **~1 $** |

Rispetto al CloudFormation (circa 80-90 $ al mese) mancano l'istanza Aurora sempre accesa e il VPC endpoint di Secrets Manager; con circa 1.000 file al giorno il costo resta basso perché si paga solo il tempo in cui il database è attivo.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk12lambdaApplicationS3Utils --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il cluster Aurora viene cancellato senza snapshot finale (`RemovalPolicy.DESTROY`), i bucket svuotati e cancellati, le tabelle DynamoDB cancellate con i dati
- il segreto del database resta *in attesa di cancellazione* per 7 giorni (non si paga)
- il parametro SSM con la chiave SFTP non è dello stack: se serviva solo per l'esempio `aws ssm delete-parameter --name /cdk12/sftp/private-key`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔐 **Autenticazione** delle API e della pagina (Cognito o Lambda authorizer, vedi cdk10)
- 🧾 **Step Function** al posto della catena di eventi, con un'unica esecuzione per ogni zip e lo stato di ogni passo
- 🐘 **PostgreSQL**: Aurora PostgreSQL con la Data API (lo SQL di creazione e inserimento va adattato)


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Prima versione completa (prima c'erano solo app.py e tags.py e la sintesi falliva): porting dell'Esempio12 CloudFormation/SAM con Aurora Serverless v2 e Data API, Lambda per zip, Excel, CSV, API, scansione notturna e SFTP facoltativo, layer creato da build_layer.sh, allarmi, pagina web su CloudFront, test dello stack e delle Lambda, README |
| 2026-11-17 | VPC e subnet per default quelle di default della region (lette da CDK al synth, salvate in cdk.context.json ignorato da git), sempre modificabili con i parametri o con -c vpc_id=... |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk12-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk12, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk12 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


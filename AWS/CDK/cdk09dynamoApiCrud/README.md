# AWS CDK 09 - API CRUD su DynamoDB

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'API REST **API Gateway** che legge e scrive gli item di una tabella **DynamoDB**, con una **Lambda** per ogni operazione (create, read, update, delete). Versione CDK in Python dell'esempio CloudFormation [Esempio09dynamoApiCrud](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio09dynamoApiCrud).

- **🗄️ Tabella DynamoDB** on-demand con chiave `id` (costrutto `TableV2`), cancellata al destroy
- **🐍 Quattro Lambda Python 3.13 su ARM** con lo stesso codice (`lambda/items.py`), ognuna con i soli permessi DynamoDB della sua operazione
- **✅ Risposte corrette**: 201 alla creazione (con `id` generato se manca), 400 per un body non valido, 404 se l'item non esiste, 409 se l'`id` è già usato; i numeri del JSON diventano `Decimal` per DynamoDB e tornano numeri nelle risposte
- **🚦 Stage `dev`** con limite di 10 richieste al secondo (picchi di 20)

Rispetto alla prima versione: con un prezzo decimale (`9.99`) la creazione falliva (DynamoDB non accetta i float), la lettura di un item con numeri falliva (`Decimal` non serializzabile in JSON), l'update poteva provare a cambiare la chiave e non c'erano 400/404; inoltre le Lambda erano Python 3.9 (deprecato) con il permesso di leggere e scrivere tutto.


## 🔧 Architettura

```
POST   /items       ── Lambda CreateItem (PutItem)        ──┐
GET    /items       ── Lambda ReadItem   (Scan)            ──┤
GET    /items/{id}  ── Lambda ReadItem   (GetItem)         ──┼── tabella DynamoDB aws-py-cdk09-items (id)
PUT    /items/{id}  ── Lambda UpdateItem (UpdateItem)      ──┤
DELETE /items/{id}  ── Lambda DeleteItem (DeleteItem)      ──┘
```

```
├── app.py                              # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk09dynamo_api_crud/
│   ├── cdk09dynamo_api_crud_stack.py   # 🏗️ tabella, Lambda con permessi minimi, API
│   ├── naming.py                       # 🏷️ nomi aws-py-cdk09-<servizio> e tag Name di ogni risorsa
│   └── tags.py                         # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/items.py                     # 🐍 handler create, read, update, delete
├── tests/unit/                         # 🧪 test dello stack e delle Lambda con una tabella finta (senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk09dynamoApiCrud/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
URL=$(aws cloudformation describe-stacks --stack-name aws-py-cdk09 --query "Stacks[0].Outputs[?OutputKey=='ItemsUrl'].OutputValue" --output text)
curl -X POST $URL -H 'Content-Type: application/json' -d '{"id": "1", "name": "Alberto", "description": "bellissimo", "price": 9.99}'
curl $URL
curl -X PUT $URL/1 -H 'Content-Type: application/json' -d '{"description": "magnifico"}'
curl $URL/1
curl -X DELETE $URL/1
curl -i $URL/1           # 404
```

**Tag**: tabella, API, stage, Lambda, ruoli e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk09dynamoApiCrud`, `ManagedBy=CDK`); risorse, metodi e deployment dell'API, permessi e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk09-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| DynamoDB on-demand | ~0,76 $ per milione di scritture, ~0,15 $ per milione di letture; storage 0,306 $/GB (25 GB gratuiti) | ~0 $ per i test |
| API Gateway REST | 3,70 $ per milione di richieste | ~0 $ |
| Lambda | free tier: 1 milione di richieste al mese | 0 $ |

Con la tabella on-demand non c'è un costo fisso: a riposo si paga solo lo storage.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk09dynamoApiCrud --query "ResourceTagMappingList[].ResourceARN" --output text
```
- la tabella viene cancellata con i dati, insieme a API, Lambda e log group
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔐 **Autenticazione** con un Lambda authorizer (vedi cdk10) o Cognito
- 📄 **Paginazione nell'API** (`limit` e `nextToken`) al posto della scan completa
- ✔️ **Validazione del body** con i modelli JSON Schema di API Gateway


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: Lambda in un solo modulo items.py con correzione dei numeri decimali (float in scrittura, Decimal in lettura), risposte 400/404/409, id generato, scan con paginazione, permessi minimi per ogni funzione, runtime Python 3.13 su ARM (il 3.9 è deprecato), TableV2 con nome dello stack, log group dello stack, test dello stack e delle Lambda con tabella finta, README nuovo (il precedente aveva il titolo del cdk13) |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk09-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk09, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk09 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


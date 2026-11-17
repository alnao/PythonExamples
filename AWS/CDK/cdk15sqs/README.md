# AWS CDK 15 - Coda SQS

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una coda **Amazon SQS** con due **Lambda** esposte da **API Gateway**: il *producer* invia i messaggi, il *consumer* li legge e li cancella. Versione CDK in Python dell'esempio CloudFormation [Esempio15sqs](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio15sqs); la prima versione aveva preso spunto dal [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/s3-sns-sqs-lambda-chain/s3_sns_sqs_lambda_chain/s3_sns_sqs_lambda_chain_stack.py).

- **📬 Coda standard** cifrata (SSE-SQS), solo HTTPS, visibility timeout 60 secondi
- **☠️ Dead-letter queue**: un messaggio ricevuto 3 volte senza essere cancellato passa nella DLQ, dove resta 14 giorni
- **🐍 Lambda Python 3.13 su ARM** con permessi separati: il producer può solo inviare, il consumer solo leggere e cancellare
- **🌐 API REST**: `POST /produce` con `{"message": "..."}` (400 se manca o è vuoto) e `GET /consume` che restituisce fino a 10 messaggi (long polling di 5 secondi) e li cancella in blocco
- **🧹 Nomi con il prefisso dello stack** (`aws-py-cdk15-queue`, `aws-py-cdk15-dlq`) al posto del parametro `QueueName`, code cancellate al destroy


## 🔧 Architettura

```
POST /produce {"message": "..."} ── Lambda Producer ── SendMessage ──┐
                                                                      ▼
                                                          coda aws-py-cdk15-queue ── dopo 3 ricezioni ── aws-py-cdk15-dlq
                                                                      │
GET /consume ── Lambda Consumer ── ReceiveMessage + DeleteMessageBatch ┘
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk15sqs/
│   ├── cdk15sqs_stack.py           # 🏗️ code, Lambda, API
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk15-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/producer.py, consumer.py # 🐍 codice delle funzioni
├── tests/unit/                     # 🧪 test dello stack e delle Lambda con una coda finta (senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk15sqs/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
URL=$(aws cloudformation describe-stacks --stack-name aws-py-cdk15 --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
curl ${URL}consume                                                    # {"messaggi": []} dopo 5 secondi
curl -X POST -H "Content-Type: application/json" -d '{"message":"messaggio evento cdk"}' ${URL}produce
curl -X POST -H "Content-Type: application/json" -d '{"message":"secondo messaggio"}' ${URL}produce
curl ${URL}consume                                                    # {"messaggi": ["messaggio evento cdk", "secondo messaggio"]}
```

**Tag**: code, API, stage, Lambda, ruoli e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk15sqs`, `ManagedBy=CDK`); policy delle code, risorse, metodi e deployment dell'API, permessi e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk15-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| SQS standard | 0,40 $ per milione di richieste, il primo milione gratuito | 0 $ per i test |
| API Gateway REST | 3,70 $ per milione di richieste | ~0 $ |
| Lambda | free tier: 1 milione di richieste al mese | 0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk15sqs --query "ResourceTagMappingList[].ResourceARN" --output text
```
- le code vengono cancellate con i messaggi, insieme ad API, Lambda e log group
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- ⚡ **Event source mapping**: la Lambda consumer invocata direttamente da SQS invece che dall'API
- 🔢 **Coda FIFO** con ordine garantito e deduplica dei messaggi
- 🔔 **Allarme CloudWatch** sui messaggi nella DLQ con notifica SNS (vedi cdk16 e cdk22)


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: coda cifrata con dead-letter queue, nomi delle code con il prefisso dello stack al posto del parametro QueueName, validazione del messaggio (400), cancellazione in blocco dei messaggi letti, permessi separati per producer e consumer, runtime Python 3.13 su ARM, log group dello stack, test dello stack e delle Lambda con coda finta, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk15-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk15, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk15 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


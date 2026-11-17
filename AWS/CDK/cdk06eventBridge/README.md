# AWS CDK 06 - EventBridge

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Due regole **Amazon EventBridge** che invocano una **Lambda**: una sui file caricati in un bucket S3, una schedulata. Versione CDK in Python dell'esempio CloudFormation [Esempio06eventBridge](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio06eventBridge); la prima versione aveva preso spunto dal [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/api-eventbridge-lambda/api_eventbridge_lambda/api_eventbridge_lambda.py).

- **🪣 Bucket dello stack** con le notifiche verso EventBridge attive (`event_bridge_enabled`): la prima versione ascoltava un bucket esterno (`prova-alberto`) che lo stack non creava, con le notifiche da attivare a mano, quindi la regola non scattava mai
- **📥 Regola "Object Created"** sui file della cartella `INPUT/` del bucket, con 2 tentativi in caso di errore
- **⏰ Regola schedulata**: dal lunedì al venerdì alle 18:00 UTC (`cron(0 18 ? * MON-FRI *)`)
- **🐍 Lambda Python 3.13 su ARM** che scrive nel log l'evento e un riassunto (bucket, chiave e dimensione del file, oppure l'orario dell'esecuzione schedulata); log group dello stack con 7 giorni, cancellato al destroy


## 🔧 Architettura

```
aws s3 cp ── bucket S3 (INPUT/...) ── evento "Object Created" ── EventBridge (regola ObjectCreated) ──┐
EventBridge (regola Schedule, lun-ven 18:00 UTC) ─────────────────────────────────────────────────────┴── Lambda EventConsumer ── log
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk06event_bridge/
│   ├── cdk06event_bridge_stack.py  # 🏗️ bucket, Lambda, regole EventBridge
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk06-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/event_consumer_lambda.py # 🐍 codice della funzione
├── tests/unit/                     # 🧪 test dello stack e della funzione (in locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk06eventBridge/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk06 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws s3 cp README.md s3://$(out BucketName)/INPUT/prova.md
sleep 30
aws logs tail /aws/lambda/$(out FunctionName) --since 5m      # riassunto: {"tipo": "file", "chiave": "INPUT/prova.md", ...}
aws events list-rules --name-prefix aws-py-cdk06 --query "Rules[].[Name,State,ScheduleExpression]" --output table
```

**Tag**: bucket, Lambda, ruoli, log group e regole EventBridge hanno i tag standard (`Project=Development.aws.py-CDK.cdk06eventBridge`, `ManagedBy=CDK`); bucket policy, permessi della Lambda e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk06-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| EventBridge | eventi dei servizi AWS (S3) e regole schedulate gratuiti | 0 $ |
| Lambda | free tier: 1 milione di richieste al mese | 0 $ |
| S3 e CloudWatch Logs | pochi KB | ~0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk06eventBridge --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il bucket viene svuotato e cancellato, le regole e la funzione cancellate insieme al log group
- se esiste ancora il log group `/aws/lambda/cdk06event-bridge` creato dalla prima versione dell'esempio va cancellato a mano: `aws logs delete-log-group --log-group-name /aws/lambda/cdk06event-bridge`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🚌 **Event bus personalizzato** con eventi applicativi pubblicati con `PutEvents`
- 🕒 **EventBridge Scheduler** al posto della regola schedulata (fusi orari e schedulazioni una tantum)
- 📮 **Dead-letter queue** SQS per gli eventi che la Lambda non riesce a elaborare


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: bucket creato dallo stack con le notifiche EventBridge attive (prima ascoltava un bucket esterno inesistente), runtime Python 3.13 su ARM (il 3.8 è deprecato), log group cancellato al destroy, tolto il permesso events:PutEvents inutile, Lambda che riassume l'evento, test dello stack e della Lambda, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk06-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk06, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk06 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


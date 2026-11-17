# AWS CDK 16 - Topic SNS

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un topic **Amazon SNS** con una **Step Function** che pubblica le notifiche e una **Lambda** (più un'email facoltativa) che le riceve. Versione CDK in Python dell'esempio CloudFormation [Esempio16sns](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio16sns).

- **📣 Topic** `aws-py-cdk16-notifications`, solo HTTPS (la prima versione lo chiamava `NotificationTopic`, nome generico che poteva scontrarsi con altri stack)
- **🐍 Lambda iscritta** (Python 3.13 su ARM) che scrive nel log id, oggetto e testo di ogni messaggio
- **📧 Email facoltativa** con `-c email=<indirizzo>`: AWS manda un link di conferma, finché non si conferma l'iscrizione resta *pending*; la prima versione aveva un indirizzo scritto nel codice
- **🔀 Step Function** `aws-py-cdk16-notify`: pubblica il campo `message` dell'input con l'oggetto `cdk16: <subject>` (`notifica` se `subject` manca); usa `definition_body` al posto del deprecato `definition`
- **📋 Log** della Lambda e della Step Function (livello ERROR) in log group dello stack, 7 giorni


## 🔧 Architettura

```
start-execution {"message": "...", "subject": "..."} ── Step Function aws-py-cdk16-notify ── SNS Publish
                                                                                              │
                                                     topic aws-py-cdk16-notifications ◄────────────┘
                                                       ├── Lambda aws-py-cdk16-logging ── log
                                                       └── email (facoltativa, -c email=...)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk16sns/
│   ├── cdk16sns_stack.py           # 🏗️ topic, iscrizioni, Step Function
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk16-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/index.py                 # 🐍 Lambda che riceve le notifiche
├── tests/unit/                     # 🧪 test dello stack e della funzione (in locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk16sns/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy                                   # oppure: cdk deploy -c email=nome@example.com
```

Verifica:
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk16 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws stepfunctions start-execution --state-machine-arn $(out StateMachineArn) --input '{"message": "test message from CLI to CDK SNS", "subject": "prova"}'
aws sns publish --topic-arn $(out TopicArn) --message "pubblicato direttamente sul topic"
sleep 10
aws logs tail /aws/lambda/$(out LoggingFunctionName) --since 5m
aws sns list-subscriptions-by-topic --topic-arn $(out TopicArn) --query "Subscriptions[].[Protocol,Endpoint,SubscriptionArn]" --output table
```

**Tag**: topic, Step Function, Lambda, ruoli e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk16sns`, `ManagedBy=CDK`); iscrizioni, policy del topic, permessi e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk16-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| SNS | 1 milione di pubblicazioni e 1.000 email gratuite al mese, consegne a Lambda gratuite | 0 $ per i test |
| Step Functions | 4.000 transizioni gratuite al mese | 0 $ |
| Lambda | free tier: 1 milione di richieste al mese | 0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk16sns --query "ResourceTagMappingList[].ResourceARN" --output text
```
- topic, iscrizioni, Step Function, Lambda e log group vengono cancellati
- se esiste ancora il log group `/aws/lambda/cdk16Logging` creato dalla prima versione dell'esempio va cancellato a mano: `aws logs delete-log-group --log-group-name /aws/lambda/cdk16Logging`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🎯 **Filtri sulle iscrizioni** (filter policy) per mandare a ogni iscritto solo i messaggi che gli interessano
- 📬 **Fan-out verso SQS**: più code iscritte allo stesso topic (vedi cdk15)
- 🔑 **Cifratura** del topic con una chiave KMS dello stack


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: tolto l'indirizzo email scritto nel codice (ora facoltativo con -c email=...), topic e Step Function con il prefisso dello stack, definition_body al posto del deprecato definition, oggetto della notifica, runtime Python 3.13 su ARM, log group dello stack, test dello stack e della Lambda, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk16-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk16, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk16 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


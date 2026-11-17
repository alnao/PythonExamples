# AWS CDK 05 - Funzione Lambda

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una funzione **AWS Lambda** in Python con il suo **log group**. Versione CDK in Python dell'esempio CloudFormation [Esempio05lambda](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio05lambda); la prima versione aveva preso spunto dal [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/tree/main/python/lambda-with-existing-s3-code).

- **🐍 Python 3.13 su ARM** (Graviton, circa il 20% più economico di x86), 128 MB, timeout 10 secondi
- **📦 Codice in `lambda/`**: CDK lo comprime e lo carica come asset nel bucket del bootstrap
- **📋 Log group dello stack**: `/aws/lambda/aws-py-cdk05-hello` con scadenza a 7 giorni, i tag standard e cancellato al destroy; nella prima versione aveva `Retain`, restava dopo il destroy e il deploy successivo falliva perché il nome era già usato
- **👋 Funzione di prova**: scrive l'evento nel log e risponde `Ciao <nome>!` (campo `nome` dell'evento, oppure la variabile d'ambiente `DEFAULT_NAME`)


## 🔧 Architettura

```
aws lambda invoke ── Lambda aws-py-cdk05-hello (python3.13, arm64) ── log group /aws/lambda/aws-py-cdk05-hello (7 giorni)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk05lambda/
│   ├── cdk05lambda_stack.py        # 🏗️ log group e funzione
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk05-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/cdk05lambda_code.py      # 🐍 codice della funzione
├── tests/unit/                     # 🧪 test dello stack e della funzione (in locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk05lambda/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
FUNCTION=$(aws cloudformation describe-stacks --stack-name aws-py-cdk05 --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text)
aws lambda invoke --function-name $FUNCTION --cli-binary-format raw-in-base64-out --payload '{"nome":"Alberto"}' /tmp/cdk05.json && cat /tmp/cdk05.json
aws logs tail /aws/lambda/$FUNCTION --since 10m
```

**Tag**: funzione, ruolo e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk05lambda`, `ManagedBy=CDK`); la policy IAM non accetta tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk05-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Lambda | 1 milione di richieste e 400.000 GB-secondi gratuiti al mese | 0 $ per i test |
| CloudWatch Logs | 0,63 $/GB scritto, 5 GB gratuiti | ~0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk05lambda --query "ResourceTagMappingList[].ResourceARN" --output text
```
- funzione, ruolo e log group vengono cancellati
- se esiste ancora il log group `/aws/lambda/cdk05lambda` creato dalla prima versione dell'esempio va cancellato a mano: `aws logs delete-log-group --log-group-name /aws/lambda/cdk05lambda`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔗 **Function URL** per chiamare la funzione via HTTPS senza API Gateway
- 📦 **Layer** con le librerie comuni a più funzioni
- 🔢 **Versioni e alias** per pubblicare una nuova versione in modo graduale (vedi cdk08)


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: runtime Python 3.13 su ARM, log group collegato alla funzione e cancellato al destroy (con Retain il deploy dopo un destroy falliva), nome della funzione con il prefisso dello stack, test dello stack e del codice della Lambda, README nuovo (il precedente era una copia di quello del cdk06) |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk05-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk05, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk05 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


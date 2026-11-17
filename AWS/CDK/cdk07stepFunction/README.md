# AWS CDK 07 - Step Functions

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Una macchina a stati **AWS Step Functions** che coordina due **Lambda**: avvia un job, aspetta, ne controlla lo stato e ripete finché il job non termina. Versione CDK in Python dell'esempio CloudFormation [Esempio07stepFunction](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio07stepFunction); la prima versione aveva preso spunto dal [repository aws-samples](https://github.com/aws-samples/aws-cdk-examples/blob/main/python/stepfunctions/stepfunctions/stepfunctions_stack.py).

- **🔁 Flusso**: `Submit Job` → `Wait 10 Seconds` → `Get Status` → `Job Complete?` (FAILED → `Fail`, SUCCEEDED → `Succeeded`, altrimenti di nuovo `Wait`)
- **🧪 Job simulato**: `submit.py` crea un job con un id, `status.py` lo fa terminare dopo `steps` controlli (default 2) e lo fa fallire se l'input contiene `"fail": true`
- **🐍 Lambda Python 3.13 su ARM** con nomi `aws-py-cdk07-submit` e `aws-py-cdk07-status` (la prima versione le chiamava `cdk06submit` e `cdk06status`)
- **📋 Log**: log group dello stack per le due Lambda e per la macchina a stati (livello `ALL`), 7 giorni, cancellati al destroy; timeout dell'esecuzione 10 minuti


## 🔧 Architettura

```
start-execution ── Step Function aws-py-cdk07-job
                     ├── Submit Job (Lambda Submit) ── {jobId, status: RUNNING, checks: 0, steps, fail}
                     ├── Wait 10 Seconds  ◄──────────────────────────┐
                     ├── Get Status (Lambda Status) ── checks + 1    │
                     └── Job Complete? ── RUNNING ───────────────────┘
                                       ├── SUCCEEDED ── Succeeded
                                       └── FAILED ───── Fail
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk07step_function/
│   ├── cdk07step_function_stack.py # 🏗️ Lambda, log group, macchina a stati
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk07-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/submit.py, status.py     # 🐍 job simulato
├── tests/unit/                     # 🧪 test dello stack e del giro completo del job (in locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk07stepFunction/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
SM=$(aws cloudformation describe-stacks --stack-name aws-py-cdk07 --query "Stacks[0].Outputs[?OutputKey=='StateMachineArn'].OutputValue" --output text)
aws stepfunctions start-execution --state-machine-arn $SM --input '{"steps": 3}'
aws stepfunctions start-execution --state-machine-arn $SM --input '{"fail": true}'
sleep 40
aws stepfunctions list-executions --state-machine-arn $SM --query "executions[].[name,status,startDate,stopDate]" --output table
aws logs tail /aws/vendedlogs/states/aws-py-cdk07-job --since 10m
```

**Tag**: macchina a stati, Lambda, ruoli e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk07stepFunction`, `ManagedBy=CDK`); le policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk07-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Step Functions Standard | 0,025 $ ogni 1.000 transizioni di stato, 4.000 gratuite al mese (circa 10 per esecuzione) | 0 $ per i test |
| Lambda | free tier: 1 milione di richieste al mese | 0 $ |
| CloudWatch Logs | 0,63 $/GB scritto, 5 GB gratuiti | ~0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk07stepFunction --query "ResourceTagMappingList[].ResourceARN" --output text
```
- macchina a stati, Lambda e log group vengono cancellati
- se esistono ancora i log group `/aws/lambda/cdk06submit` e `/aws/lambda/cdk06status` creati dalla prima versione dell'esempio vanno cancellati a mano con `aws logs delete-log-group --log-group-name <nome>`
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- ⚡ **Express workflow** per flussi brevi e molto frequenti (si paga per durata, non per transizione)
- 🔌 **Integrazioni dirette** con i servizi AWS (DynamoDB, SQS, Glue) senza Lambda, come nel cdk14
- 🔔 **Notifica SNS** in caso di fallimento (vedi cdk16)


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: nomi di Lambda e log group con il prefisso dello stack (prima cdk06submit e cdk06status), runtime Python 3.13 su ARM (il 3.9 è deprecato), log group cancellati al destroy, log della macchina a stati, job simulato che termina o fallisce su richiesta, test dello stack e delle Lambda, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk07-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk07, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk07 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


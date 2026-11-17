# AWS CDK 08 - API Gateway con stage e alias Lambda

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'API REST **API Gateway** con due **stage** (`dev` e `prod`), ognuno collegato a un **alias** diverso della stessa **Lambda** tramite una *stage variable*. Versione CDK in Python dell'esempio CloudFormation [Esempio08apiGateway](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio08apiGateway), sul modello dell'esempio [aws-samples api-stages-lambda](https://github.com/aws-samples/aws-cdk-examples/tree/main/python/api-stages-lambda).

- **🐍 Lambda Python 3.13 su ARM** con due alias, `dev` e `prod`, sulla versione corrente del codice
- **🔀 Stage variable `lambdaAlias`**: l'URI dell'integrazione termina con `:${stageVariables.lambdaAlias}`, quindi lo stage `dev` invoca l'alias `dev` e lo stage `prod` l'alias `prod`; nella prima versione l'integrazione chiamava sempre la funzione senza alias e la stage variable non serviva
- **🔐 Permessi separati**: ogni alias permette l'invocazione solo dal proprio stage (`SourceArn` con stage, metodo e percorso)
- **🚦 Limiti di richieste** su entrambi gli stage (10 al secondo, picchi di 20) e metriche CloudWatch
- **📋 Niente log di esecuzione di API Gateway**: richiederebbero il ruolo CloudWatch nelle impostazioni dell'account (vedi cdk10); il log group della Lambda è dello stack, 7 giorni


## 🔧 Architettura

```
GET https://<api>.execute-api.<region>.amazonaws.com/dev/stage_info  ── stage dev  (lambdaAlias=dev)  ──┐
GET https://<api>.execute-api.<region>.amazonaws.com/prod/stage_info ── stage prod (lambdaAlias=prod) ──┤
                                                                                                        └── integrazione AWS_PROXY
    arn:...:function:aws-py-cdk08-stage-info:${stageVariables.lambdaAlias} ── alias dev / alias prod ── versione della Lambda
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk08api_gateway/
│   ├── cdk08api_gateway_stack.py   # 🏗️ Lambda e alias, API, deployment, stage, permessi
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk08-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/function.py              # 🐍 risponde con stage e alias invocati
├── tests/unit/                     # 🧪 test dello stack e della funzione (in locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk08apiGateway/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk08 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
curl $(out DevUrl)      # {"apiStage": "dev", "lambdaAlias": "dev", ...}
curl $(out ProdUrl)     # {"apiStage": "prod", "lambdaAlias": "prod", ...}
```
Il deployment dell'API è dichiarato a mano (`deploy=False`): se si aggiungono metodi o risorse conviene cambiare la `description` del deployment, così CloudFormation ne crea uno nuovo.

**Tag**: API, stage, Lambda, ruolo e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk08apiGateway`, `ManagedBy=CDK`); risorse e metodi dell'API, deployment, versioni e alias della Lambda, permessi e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk08-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| API Gateway REST | 3,70 $ per milione di richieste (1 milione gratuito al mese nel primo anno) | ~0 $ per i test |
| Lambda | free tier: 1 milione di richieste al mese | 0 $ |
| CloudWatch Logs e metriche | metriche standard di API Gateway gratuite | ~0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk08apiGateway --query "ResourceTagMappingList[].ResourceARN" --output text
```
- API, stage, Lambda con alias e versioni e log group vengono cancellati
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🐤 **Rilascio graduale**: alias `prod` con `additional_versions` per mandare una percentuale del traffico alla nuova versione
- 🔑 **API key e usage plan** per lo stage `prod`
- 🧭 **Canary deployment** dello stage con le impostazioni canary di API Gateway


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: stage dev e prod che invocano gli alias dev e prod tramite la stage variable lambdaAlias (prima l'integrazione chiamava sempre la funzione senza alias), permessi per stage, tolto il metodo complete_version non funzionante, runtime Python 3.13 su ARM (il 3.8 è deprecato), log group dello stack, test dello stack e della Lambda, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk08-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk08, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk08 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


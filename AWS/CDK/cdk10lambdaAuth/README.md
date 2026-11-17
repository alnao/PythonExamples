# AWS CDK 10 - Lambda authorizer con JWT

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un'API REST **API Gateway** protetta da un **Lambda authorizer** che verifica un token **JWT** firmato con HS256. Versione CDK in Python dell'esempio CloudFormation [Esempio10lambdaAuthorizer](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio10lambdaAuthorizer).

- **🔑 Segreto in Secrets Manager**: la chiave per firmare e verificare i token è generata al deploy (48 caratteri), nessuna password nei parametri o nel codice
- **🛂 Lambda authorizer** di tipo TOKEN sull'header `Authorization` (`Bearer <token>`): con un token valido risponde `Allow` e passa l'utente (claim `sub`) alla risorsa; con un token mancante, scaduto o con la firma sbagliata API Gateway risponde **401**
- **🐍 Verifica JWT con la sola libreria standard** (`lambda/jwt_hs256.py`): controlla algoritmo (solo HS256, niente `none`), firma e scadenza; non serve `pyjwt` e quindi nemmeno Docker per il bundling
- **🧾 Script `make_token.py`** che legge il segreto dello stack e crea un token di prova
- **🚦 Stage `dev`** con limite di richieste e metriche, cache dell'authorizer disattivata (ogni richiesta verifica il token)

Perché la prima versione non funzionava: lo stage attivava i log di esecuzione e i data trace, che richiedono il ruolo CloudWatch nelle impostazioni di API Gateway dell'account (con il feature flag `disableCloudWatchRole` CDK non lo crea) e il deploy falliva con *CloudWatch Logs role ARN must be set in account settings*; inoltre `cdk synth` richiedeva Docker e il segreto era un parametro in chiaro con un valore di default nel codice.


## 🔧 Architettura

```
curl -H "Authorization: Bearer <token>" ── API Gateway (GET /, stage dev)
                                              ├── Lambda Authorizer ── Secrets Manager (segreto HS256)
                                              │      token valido → Allow + {user}  /  non valido → 401
                                              └── Lambda Protected ── {"messaggio": ..., "utente": ...}
make_token.py ── Secrets Manager ── token firmato (sub, iat, exp)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk10lambda_auth/
│   ├── cdk10lambda_auth_stack.py   # 🏗️ segreto, Lambda, authorizer, API
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk10-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/
│   ├── jwt_hs256.py                # 🔏 firma e verifica dei token (libreria standard)
│   ├── authorizer.py               # 🛂 Lambda authorizer
│   └── protected.py                # 🐍 risorsa protetta
├── make_token.py                   # 🧾 token di prova
├── tests/unit/                     # 🧪 test dello stack, dei token e delle Lambda (in locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate. Docker non serve più.

```bash
cd PythonExamples/AWS/CDK/cdk10lambdaAuth/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk10 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
URL=$(out ApiUrl)
curl -i $URL                                           # 401 {"message":"Unauthorized"}
curl -i -H "Authorization: Bearer abc.def.ghi" $URL    # 401
TOKEN=$(python3 make_token.py $(out JwtSecretArn) --user alberto --minutes 10)
curl -H "Authorization: Bearer $TOKEN" $URL            # {"messaggio": "Accesso autorizzato ...", "utente": "alberto"}
```

**Tag**: segreto, API, stage, Lambda, ruoli e log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk10lambdaAuth`, `ManagedBy=CDK`); authorizer, metodi e deployment dell'API, permessi e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk10-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Secrets Manager | 0,40 $ per segreto al mese + 0,05 $ ogni 10.000 letture | ~0,40 $ |
| API Gateway REST | 3,70 $ per milione di richieste | ~0 $ per i test |
| Lambda | free tier: 1 milione di richieste al mese (l'authorizer gira a ogni richiesta) | 0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk10lambdaAuth --query "ResourceTagMappingList[].ResourceARN" --output text
```
- API, Lambda, log group e segreto vengono cancellati (il segreto resta *in attesa di cancellazione* per 7 giorni, poi sparisce; non si paga)
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 👥 **Amazon Cognito** come emittente dei token, con l'authorizer Cognito al posto della Lambda
- 🔁 **Rotazione del segreto** con una Lambda di rotazione di Secrets Manager
- 🧩 **Authorizer di tipo REQUEST** per leggere anche query string e header diversi


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: corretto il deploy che falliva senza il ruolo CloudWatch di API Gateway (tolti log di esecuzione e data trace dello stage), segreto JWT generato in Secrets Manager al posto del parametro in chiaro, verifica HS256 con la libreria standard (niente pyjwt e niente Docker), risposta 401 per i token non validi, script make_token.py, runtime Python 3.13 su ARM, test dello stack e delle Lambda, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk10-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk10, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk10 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


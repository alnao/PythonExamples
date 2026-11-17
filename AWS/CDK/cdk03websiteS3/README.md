# AWS CDK 03 - Sito web statico su S3

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un **sito web statico** servito direttamente dall'endpoint website di **S3**, con le pagine caricate da CDK al deploy. Versione CDK in Python dell'esempio CloudFormation [Esempio03webSiteS3](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio03webSiteS3).

- **🌐 Hosting statico**: `index.html` come pagina iniziale ed `error.html` per le pagine che non esistono
- **📤 Pagine caricate da CDK**: la cartella `web/` viene copiata nel bucket a ogni `cdk deploy` (`BucketDeployment`), non serve più il comando `aws s3 cp`
- **🔓 Lettura pubblica** degli oggetti tramite bucket policy; le ACL pubbliche restano bloccate
- **⚠️ Solo HTTP**: l'endpoint website di S3 non supporta HTTPS, quindi il bucket **non** ha la regola "solo HTTPS" (`enforce_ssl`), che risponderebbe 403 a tutte le richieste del sito (era il motivo per cui la prima versione non funzionava). Per un sito in HTTPS con bucket privato vedere il [cdk04](../cdk04cloudFront/)
- **🧹 Destroy pulito**: il bucket ha un nome generato da CloudFormation (niente conflitti con nomi già usati) e al destroy viene svuotato e cancellato


## 🔧 Architettura

```
browser ── HTTP ── endpoint website S3 (http://<bucket>.s3-website.<region>.amazonaws.com)
                        └── bucket: index.html, error.html (lettura pubblica)
cdk deploy ── BucketDeployment (Lambda di CDK) ── copia web/ nel bucket
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk03website_s3/
│   ├── cdk03website_s3_stack.py    # 🏗️ bucket website e caricamento delle pagine
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk03-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── web/                            # 🌐 index.html ed error.html
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

Per pubblicare un bucket il **Blocco dell'accesso pubblico a livello di account** (S3 → *Block Public Access settings for this account*) deve permettere le bucket policy pubbliche, altrimenti il deploy fallisce sulla bucket policy:
```bash
aws s3control get-public-access-block --account-id $(aws sts get-caller-identity --query Account --output text)
```

```bash
cd PythonExamples/AWS/CDK/cdk03websiteS3/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica:
```bash
URL=$(aws cloudformation describe-stacks --stack-name aws-py-cdk03 --query "Stacks[0].Outputs[?OutputKey=='WebsiteUrl'].OutputValue" --output text)
curl $URL/                    # index.html
curl -i $URL/non-esiste       # 404 con error.html
```
Per cambiare le pagine basta modificare i file in `web/` e rilanciare `cdk deploy`.

**Tag**: bucket, Lambda e ruolo del `BucketDeployment`, log group e Lambda di svuotamento hanno i tag standard (`Project=Development.aws.py-CDK.cdk03websiteS3`, `ManagedBy=CDK`); bucket policy e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk03-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Storage S3 | 0,0245 $/GB | ~0 $ (due pagine) |
| Richieste GET | 0,0043 $ ogni 10.000 | ~0 $ per i test |
| Traffico in uscita | 0,09 $/GB (i primi 100 GB al mese gratuiti) | ~0 $ |
| Lambda del `BucketDeployment` | gira solo durante il deploy | ~0 $ |


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk03websiteS3 --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il bucket viene svuotato e cancellato, il log group del `BucketDeployment` anche
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔒 **HTTPS e bucket privato** con CloudFront (è il [cdk04](../cdk04cloudFront/))
- 🌍 **Dominio personalizzato** con Route 53 (bucket con lo stesso nome del dominio)
- 🔁 **Redirect** di un secondo bucket (`www.`) verso il primo


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: corretto il sito che rispondeva 403 (enforce_ssl sull'endpoint website solo HTTP), pagine caricate da BucketDeployment dalla cartella web/ con error.html, nome del bucket generato, tag standard anche sulle Lambda di supporto, test veri, README nuovo (il precedente era una copia di quello del cdk04) |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk03-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk03, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk03 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


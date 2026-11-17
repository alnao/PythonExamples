# AWS CDK 04 - Sito statico con CloudFront

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un **sito statico in HTTPS**: **CloudFront** davanti a un bucket **S3 privato**, letto con **Origin Access Control** (OAC). Versione CDK in Python dell'esempio CloudFormation [Esempio04webSiteCloudFront](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio04webSiteCloudFront); la prima versione aveva preso spunto dal [repository aws-samples](https://github.com/aws-samples/deploy-cloudfront-in-china-with-cdk/blob/main/Python/lib/cloudfront_in_china_stack.py).

- **🔒 Bucket privato**: accesso pubblico bloccato e solo HTTPS; la bucket policy permette la lettura solo a questa distribuzione (condizione `AWS:SourceArn`)
- **🌍 CloudFront** con il costrutto L2 `Distribution`: redirect da HTTP a HTTPS, `index.html` come pagina iniziale, compressione, cache ottimizzata, `PriceClass_100` (edge in Europa e Nord America)
- **📤 Pagine caricate da CDK**: la cartella `web/` viene copiata nel bucket a ogni deploy e la cache di CloudFront viene invalidata (`/*`)
- **🆕 OAC al posto di OAI**: la prima versione usava una Origin Access Identity (superata) e rendeva comunque pubblico il bucket

| | Prima versione | Versione attuale |
|---|---|---|
| Accesso al bucket | OAI + bucket pubblico | OAC, bucket privato |
| Distribuzione | `CfnDistribution` (L1) | `Distribution` (L2) |
| Pagine | `aws s3 cp` a mano | `BucketDeployment` con invalidazione |
| Nome bucket | fisso (`prova-alberto-cf`) | generato da CloudFormation |


## 🔧 Architettura

```
browser ── HTTPS ── CloudFront (https://<id>.cloudfront.net, redirect HTTP → HTTPS)
                        └── Origin Access Control ── bucket S3 privato (index.html)
cdk deploy ── BucketDeployment ── copia web/ nel bucket e invalida la cache
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk04cloud_front/
│   ├── cdk04cloud_front_stack.py   # 🏗️ bucket, distribuzione, caricamento delle pagine
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk04-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── web/                            # 🌐 index.html
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk04cloudFront/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy          # la distribuzione CloudFront richiede qualche minuto
```

Verifica:
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk04 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
curl $(out SiteUrl)/                                        # pagina servita da CloudFront
curl -I http://$(out SiteUrl | cut -d/ -f3)/                # 301 verso HTTPS
curl -I https://$(out BucketName).s3.$AWS_REGION.amazonaws.com/index.html   # 403: il bucket e' privato
```

**Tag**: bucket, distribuzione CloudFront, Lambda e ruoli di supporto di CDK, log group hanno i tag standard (`Project=Development.aws.py-CDK.cdk04cloudFront`, `ManagedBy=CDK`); Origin Access Control, bucket policy e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk04-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| CloudFront | free tier: 1 TB di traffico e 10 milioni di richieste al mese | 0 $ per i test |
| Invalidazioni | prime 1.000 al mese gratuite (una per deploy) | 0 $ |
| Storage S3 | 0,0245 $/GB | ~0 $ |
| Lambda del `BucketDeployment` | gira solo durante il deploy | ~0 $ |


## 🧹 Pulizia

```bash
cdk destroy         # disattivare e cancellare la distribuzione richiede alcuni minuti
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk04cloudFront --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il bucket viene svuotato e cancellato, la distribuzione disattivata e cancellata
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🌍 **Dominio personalizzato** con certificato ACM (in `us-east-1`) e record Route 53
- 🛡️ **AWS WAF** davanti alla distribuzione
- 📊 **Log di accesso** di CloudFront in un bucket


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: bucket privato con Origin Access Control al posto di OAI e bucket pubblico, Distribution L2 con redirect HTTPS, pagine della cartella web/ caricate da BucketDeployment con invalidazione, nome del bucket generato, tag standard anche sulle Lambda di supporto, test veri, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk04-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk04, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk04 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


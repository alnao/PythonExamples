# AWS CDK 01 - Bucket S3

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Il primo esempio CDK del repository: un **bucket S3** privato creato con il costrutto L2 `s3.Bucket`. Versione CDK in Python dell'esempio CloudFormation [Esempio01BucketS3](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio01BucketS3).

- **🪣 Nome `aws-py-cdk01-bucket-<account>`**: i nomi dei bucket sono unici in tutto AWS, quindi alla fine c'è l'id dell'account, che CDK prende dal profilo del deploy (non è un parametro)
- **🗂️ Versioning** attivo: le versioni precedenti dei file vengono cancellate dopo 30 giorni (regola di ciclo di vita)
- **🔐 Sicurezza**: cifratura SSE-S3, accesso pubblico bloccato, policy che rifiuta le richieste non HTTPS
- **🧹 Destroy pulito**: `RemovalPolicy.DESTROY` e `auto_delete_objects`, il bucket viene svuotato (anche delle versioni) e cancellato; lo svuotamento lo fa una Lambda di supporto di CDK, con i tag standard come il bucket


## 🔧 Architettura

```
bucket S3 (versioning, SSE-S3, solo HTTPS, nessun accesso pubblico)
  └── al destroy: custom resource CDK ── Lambda che svuota il bucket
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk01bucket_s3/
│   ├── cdk01bucket_s3_stack.py     # 🏗️ il bucket
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk01-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk01bucketS3/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION   # una volta per region (bootstrap con i nomi del repository)
cdk synth                                        # template CloudFormation generato, senza deploy
cdk deploy
```

Verifica:
```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name aws-py-cdk01 --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text)
echo "ciao" > /tmp/prova.txt
aws s3 cp /tmp/prova.txt s3://$BUCKET/prova.txt
aws s3 cp /tmp/prova.txt s3://$BUCKET/prova.txt          # seconda versione dello stesso file
aws s3api list-object-versions --bucket $BUCKET --prefix prova.txt --query "Versions[].[VersionId,IsLatest]" --output table
cdk diff                                                 # differenze tra codice e stack nel cloud
```

**Tag**: bucket, Lambda e ruolo di supporto e il log group della Lambda hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk01bucketS3`, `ManagedBy=CDK`); la bucket policy e la policy IAM dei log non accettano tag. Il log group lo crea lo stack (7 giorni, cancellato al destroy) e la Lambda può solo scriverci: prima lo creava Lambda da sola al primo svuotamento (`/aws/lambda/Cdk01BucketS3Stack-CustomS3AutoDeleteObjectsCustom-...`), senza tag e senza scadenza, e restava dopo il destroy. Quello creato da un deploy precedente va cancellato a mano: `aws logs delete-log-group --log-group-name <nome>`. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk01-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Storage S3 Standard | 0,0245 $/GB (con il versioning si pagano anche le versioni precedenti) | ~0 $ per i file di prova |
| Richieste | 0,0054 $ ogni 1.000 PUT, 0,0043 $ ogni 10.000 GET | ~0 $ |
| Lambda di svuotamento | gira solo al destroy | 0 $ |

Il bucket vuoto non costa nulla.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk01bucketS3 --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il bucket viene svuotato (file e versioni) e cancellato
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔑 **Cifratura con chiave KMS** dello stack al posto di SSE-S3
- 🧊 **Classi di storage**: regola di ciclo di vita che sposta i file vecchi in Glacier
- 📋 **Access log** del bucket in un secondo bucket


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: tag standard con priorità e aspect (anche sulla Lambda di svuotamento), bucket privato solo HTTPS con versioning e scadenza delle versioni precedenti, nome parametrico, auto_delete_objects, test veri al posto di quelli generati da cdk init, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk01-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk01, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named; tolto il parametro bucketname (il nome lo calcola CDK con l'account) |
| 2026-11-17 | Tag Name aws-py-cdk01 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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



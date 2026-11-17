# AWS CDK 13 - Job AWS Glue

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un **job AWS Glue** (Spark, Python) che legge un file CSV da **S3** e lo riscrive in un'altra cartella con le righe in ordine decrescente. Versione CDK in Python dell'esempio CloudFormation [Esempio13glueJob](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio13glueJob).

- **🪣 Bucket dello stack**: il CSV di prova (`data/persone.csv`, separatore `;`) viene caricato da CDK in `INPUT/`, il job scrive in `OUTPUT/`; i file temporanei di Glue (`temp/`) spariscono dopo 7 giorni
- **📜 Script del job** (`glue/invert_csv_data.py`) caricato da CDK come asset: non serve più copiarlo a mano nel bucket
- **⚙️ Glue 5.0** (la prima versione usava il 3.0), 2 worker `G.1X`, timeout 10 minuti, nessun nuovo tentativo, una sola esecuzione alla volta
- **📋 Log del job** in un log group dello stack (`/aws-glue/jobs/aws-py-cdk13-invert-csv`, argomento `--continuous-log-logGroup`) con 7 giorni e i tag standard; Spark UI con gli eventi in `sparkui-logs/`

Il job ordina le righe in ordine decrescente su tutte le colonne (`orderBy(desc(...))`), quindi il risultato dipende dal contenuto e non dalla posizione delle righe nel file.


## 🔧 Architettura

```
cdk deploy ── BucketDeployment ── s3://<bucket>/INPUT/persone.csv
aws glue start-job-run ── job Glue aws-py-cdk13-invert-csv (Spark, 2 × G.1X)
                             ├── legge  s3://<bucket>/INPUT/persone.csv
                             ├── scrive s3://<bucket>/OUTPUT/part-*.csv
                             └── log ── /aws-glue/jobs/aws-py-cdk13-invert-csv (7 giorni)
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk13glue_job/
│   ├── cdk13glue_job_stack.py      # 🏗️ bucket, dati di prova, ruolo, log group, job
│   ├── naming.py                   # 🏷️ nomi aws-py-cdk13-<servizio> e tag Name di ogni risorsa
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── glue/invert_csv_data.py         # ⚙️ script Spark del job
├── data/persone.csv                # 📄 CSV di prova
├── tests/unit/                     # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk13glueJob/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

export AWS_REGION=eu-central-1
#../bootstrap/bootstrap.sh create $AWS_REGION
cdk deploy
```

Verifica (il job impiega un paio di minuti, soprattutto per l'avvio dei worker):
```bash
out() { aws cloudformation describe-stacks --stack-name aws-py-cdk13 --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
JOB=$(out JobName); BUCKET=$(out BucketName)
aws glue start-job-run --job-name $JOB
aws glue get-job-runs --job-name $JOB --query "JobRuns[].[StartedOn,JobRunState,ExecutionTime,ErrorMessage]" --output table
aws s3 ls s3://$BUCKET/OUTPUT/
aws s3 cp s3://$BUCKET/OUTPUT/ - --recursive --exclude "*" --include "part-*"
```

**Tag**: bucket, job Glue, ruolo, log group, Lambda e ruoli di supporto di CDK hanno i tag standard (`Project=Development.aws.py-CDK.cdk13glueJob`, `ManagedBy=CDK`); bucket policy e policy IAM non accettano tag. Il tag `Name` di ogni risorsa è uguale al suo nome (`aws-py-cdk13-<servizio>`, vedi `naming.py`).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Per esecuzione |
|------|---------|----------------|
| Glue Spark | 0,44 $ per DPU-ora, 2 DPU, minimo 1 minuto per esecuzione | ~0,02-0,03 $ (1-2 minuti) |
| S3 e CloudWatch Logs | pochi KB | ~0 $ |

A riposo il job non costa nulla: si paga solo il tempo di esecuzione.


## 🧹 Pulizia

```bash
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk13glueJob --query "ResourceTagMappingList[].ResourceARN" --output text
```
- il bucket viene svuotato e cancellato, il job e il log group cancellati
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🕷️ **Crawler e Data Catalog** per leggere i CSV come tabelle (vedi cdk14)
- ⏰ **Trigger** schedulato o su evento S3 con EventBridge
- 🐍 **Job Python Shell** (più economico di Spark) per file piccoli


## Changelog
| Data | Modifica |
|------|----------|
| 2026-11-17 | Riscritto nello stile dei progetti recenti: bucket creato dallo stack con il CSV di prova (data/persone.csv) caricato da BucketDeployment, script del job in glue/ caricato come asset (prima andava copiato a mano in un bucket esistente), Glue 5.0 al posto del 3.0, nome del job con il prefisso dello stack, log group del job dello stack, test veri, README nuovo |
| 2026-11-17 | Log group dello stack (tag standard, 7 giorni, cancellato al destroy) anche per le Lambda di supporto di CDK, che prima creavano da sole log group senza tag (es. /aws/lambda/<stack>-CustomS3AutoDeleteObjectsCustom-...); i ruoli delle Lambda scrivono solo nel proprio log group (senza AWSLambdaBasicExecutionRole), test dedicato |
| 2026-11-17 | Nomi delle risorse aws-py-cdk13-<servizio> uguali al tag Name (naming.py comune a tutti gli esempi): stack aws-py-cdk13, bucket S3 con l'account alla fine, ruoli e instance profile IAM con la region, anche le risorse create da CDK; test test_all_resources_named |
| 2026-11-17 | Tag Name aws-py-cdk13 anche sullo stack CloudFormation (aspect PhysicalNames di naming.py), test test_stack_tags |


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


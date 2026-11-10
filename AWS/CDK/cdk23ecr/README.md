# AWS CDK 23 - Repository ECR

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Un repository **Amazon Elastic Container Registry** (ECR) dove caricare le immagini Docker. Versione CDK in Python dell'esempio CloudFormation [Esempio23ecr](https://github.com/alnao/AwsCloudFormationExamples/tree/master/Esempio23ecr), con in più le regole di ciclo di vita e lo svuotamento automatico al destroy.

- **🔎 Scansione a ogni push**: ECR controlla le vulnerabilità note dell'immagine appena caricata (scansione *basic*, gratuita)
- **♻️ Ciclo di vita**: le immagini senza tag si cancellano dopo 1 giorno e il repository tiene al massimo 10 immagini, così lo storage non cresce
- **🧹 Destroy pulito**: `EmptyOnDelete` cancella le immagini insieme al repository (nel CloudFormation andavano cancellate a mano)
- **🏷️ Tag mutabili**: il tag `latest` viene sovrascritto a ogni push

L'immagine di prova è l'API Flask del progetto [Docker/03ApiPersoneNoDb](../../../Docker/03ApiPersoneNoDb/) (porta 5001, `GET`/`POST /persone`), la stessa che il [cdk24ecs](../cdk24ecs/) esegue su ECS.

| Regola | Immagini | Azione |
|--------|----------|--------|
| 1 | senza tag, caricate da più di 1 giorno | cancellate |
| 2 | tutte, oltre le 10 più recenti | cancellate |


## 🔧 Architettura

```
docker build ── docker push ──> ECR <account>.dkr.ecr.<region>.amazonaws.com/cdk23ecr-repository
                                 ├── scansione delle vulnerabilità (a ogni push)
                                 └── regole di ciclo di vita (ogni giorno)
```

```
├── app.py                 # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk
├── cdk23ecr/
│   ├── cdk23ecr_stack.py  # 🏗️ repository, regole di ciclo di vita, output con i comandi docker
│   └── tags.py            # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── tests/unit/            # 🧪 test dello stack (sintesi locale, senza AWS)
└── cdk.json, requirements*.txt
```

Il bootstrap CDK del repository ha già un suo ECR (`alnao-dev-cdk`), dove CDK carica da solo le immagini costruite con `ContainerImage.from_asset` (come fa il cdk24): il repository di questo esempio serve per le immagini caricate a mano o da una pipeline (come nel cdk28).


## 🛠️ Deploy

```bash
cd PythonExamples/AWS/CDK/cdk23ecr/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/unit

#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy                                        # repository cdk23ecr-repository
cdk deploy --parameters reponame=altro-nome       # nome diverso
```

Al termine `cdk deploy` stampa `RepositoryUri`, `LoginCommand` e `PushCommand`. Caricamento dell'immagine di prova, dalla cartella principale del repository `PythonExamples`:
```bash
REGION=eu-central-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO=$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/cdk23ecr-repository
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com
docker build --platform linux/amd64 -t $REPO:latest Docker/03ApiPersoneNoDb
docker push $REPO:latest
# prova in locale della stessa immagine
docker run --rm -d -p 5001:5001 $REPO:latest && curl localhost:5001/persone
```

Comandi utili:
```bash
aws ecr describe-repositories --query "repositories[].[repositoryName,repositoryUri]" --output table
aws ecr list-images --repository-name cdk23ecr-repository --query "imageIds[].[imageTag,imageDigest]" --output table
aws ecr describe-image-scan-findings --repository-name cdk23ecr-repository --image-id imageTag=latest --query "imageScanFindings.findingSeverityCounts"
aws ecr get-lifecycle-policy-preview --repository-name cdk23ecr-repository     # dopo start-lifecycle-policy-preview
aws ecr batch-delete-image --repository-name cdk23ecr-repository --image-ids imageTag=latest
```

**Tag**: il repository ha i tag standard del repository (`Project=Development.aws.py-CDK.cdk23ecr`, `ManagedBy=CDK`), le immagini non hanno tag AWS propri (il costo dello storage va al repository).


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a novembre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS.

| Voce | Calcolo | Al mese |
|------|---------|---------|
| Storage | 0,10 $/GB-mese; l'immagine di prova (python:3.8 + Flask) è circa 400 MB compressi, al massimo 10 immagini | 0,04-0,40 $ |
| Scansione basic | gratuita | 0 $ |
| Trasferimento | gratuito verso servizi nella stessa region, verso Internet come EC2 | ~0 $ |
| **Totale** | | **< 0,50 $** |

Il repository vuoto non costa nulla.


## 🧹 Pulizia

```bash
# prima cancellare gli stack che usano le immagini (es. cdk24ecs se configurato con -c ecr_repository=...)
cdk destroy
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=Development.aws.py-CDK.cdk23ecr --query "ResourceTagMappingList[].ResourceARN" --output text
docker rmi $REPO:latest     # immagine locale
```
- le immagini del repository si cancellano con lui (`EmptyOnDelete`)
- il bootstrap resta (condiviso con gli altri progetti CDK): `../bootstrap/bootstrap.sh destroy <region>` quando nella region non ci sono più stack CDK


## 🚀 Sviluppi Futuri
- 🔐 **Cifratura KMS** con una chiave dedicata e **tag immutabili** per le immagini di produzione
- 🔁 **Replica** del repository in un'altra region
- 🛡️ **Enhanced scanning** con Amazon Inspector (a pagamento) e **pull through cache** da Docker Hub


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


# AWS CDK Bootstrap - bootstrap dell'account con i nomi del repository

## 🚀 Panoramica

Prima del primo `cdk deploy` ogni account e region va preparato con `cdk bootstrap`, che crea lo stack CloudFormation `CDKToolkit` con le risorse usate da tutti i progetti CDK: il bucket dove `cdk deploy` carica gli asset (codice delle Lambda, layer, file dei siti), un repository ECR per le immagini Docker, i ruoli IAM usati per il deploy e un parametro SSM con la versione del bootstrap.

Il bootstrap di default usa nomi generati (`cdk-hnb659fds-assets-<account>-<region>`, `/cdk-bootstrap/hnb659fds/version`, ...) e non ha tag. Lo script di questa cartella crea invece un bootstrap con nomi parlanti e con i tag standard del repository:

| Risorsa | Nome |
|---------|------|
| Bucket S3 degli asset | `alnao-dev-cdk` |
| Repository ECR | `alnao-dev-cdk` |
| Parametro SSM con la versione | `/cdk-bootstrap/alnao/dev/version` |
| Ruoli IAM | `cdk-alnaodev-<ruolo>-<account>-<region>` (qualifier `alnaodev`) |
| Stack CloudFormation | `CDKToolkit` |

Tag su tutte le risorse: `Name=aws-py-CDK.bootstrap`, `Environment=dev`, `Project=Development.aws.py-CDK.bootstrap`, `Owner=AlNao`, `CostCenter=dev`, `ManagedBy=CDK`.

Tutti i progetti CDK del repository (`AWS/CDK/cdk*`) usano questo bootstrap con un `DefaultStackSynthesizer` in `app.py`:
```python
SYNTHESIZER = cdk.DefaultStackSynthesizer(
    qualifier="alnaodev",
    file_assets_bucket_name="alnao-dev-cdk",
    image_assets_repository_name="alnao-dev-cdk",
    bootstrap_stack_version_ssm_parameter="/cdk-bootstrap/alnao/dev/version",
)
```
Un nuovo progetto CDK deve avere lo stesso blocco e passare `synthesizer=SYNTHESIZER` allo stack, altrimenti `cdk deploy` cerca il bootstrap di default e fallisce.

```
├── bootstrap.sh         # 🚀 crea (create) o toglie (destroy) il bootstrap di una region
├── patch_template.py    # 🧩 adatta il template ufficiale di cdk bootstrap ai nomi
└── README.md
```

Come funziona: `cdk bootstrap` permette di scegliere il nome del bucket (`--bootstrap-bucket-name`) e il qualifier, ma non il nome del repository ECR né quello del parametro SSM (il template lo costruisce come `/cdk-bootstrap/<qualifier>/version` e il qualifier non ammette `/`). Con `create` lo script prende il template ufficiale della versione di CDK installata (`cdk bootstrap --show-template`), con `patch_template.py` cambia solo i default di bucket, ECR e qualifier e il nome del parametro SSM, e lancia `cdk bootstrap --template` con i tag. Se una versione futura di CDK cambia il formato del template, `patch_template.py` si ferma con un errore invece di produrre un template sbagliato.


## 🛠️ Uso

Prerequisiti: AWS CLI configurata, AWS CDK v2 (`npm install -g aws-cdk`, oppure `CDK="npx aws-cdk" ./bootstrap.sh`), Python 3.

```bash
cd PythonExamples/AWS/CDK/bootstrap/
./bootstrap.sh                          # chiede azione (create | destroy) e region mostrando i default, poi conferma
./bootstrap.sh create eu-central-1      # crea o aggiorna il bootstrap nella region
./bootstrap.sh destroy eu-central-1     # toglie tutto il bootstrap dalla region
```

Note:
- i nomi dei bucket S3 sono unici in tutto il mondo: se `alnao-dev-cdk` fosse già preso, il bootstrap fallisce alla creazione del bucket e va scelto un altro nome (in `bootstrap.sh` e nel `SYNTHESIZER` di ogni `app.py`)
- per lo stesso motivo il bootstrap con questo nome si può fare in una sola region: per una seconda region servirebbe un bucket con un altro nome
- rilanciare lo script aggiorna lo stack esistente (per esempio dopo un aggiornamento di CDK che porta una nuova versione del bootstrap)
- il bucket degli asset accumula le versioni vecchie a ogni deploy; il template le fa scadere dopo 30 giorni e `cdk gc` pulisce gli asset non più usati

**Rimozione** (`destroy`): toglie dalla region lo stack `CDKToolkit` e tutto quello che resterebbe dopo di lui:
- legge dagli output dello stack i nomi di bucket e repository ECR, quindi funziona sia con questo bootstrap sia con quello di default (`cdk-hnb659fds-assets-...`)
- cancella il repository ECR con le sue immagini (un repository non vuoto bloccherebbe la cancellazione dello stack)
- cancella lo stack, che porta via ruoli IAM, policy e parametro SSM
- svuota il bucket degli asset (ha `DeletionPolicy: Retain` ed è versionato: vengono cancellate tutte le versioni e i delete marker, 1000 alla volta) e lo cancella

Va usato quando in quella region non ci sono più stack CDK, oppure per sostituire il bootstrap: gli stack CDK ancora presenti non si possono aggiornare né cancellare con `cdk` finché non si rifà il bootstrap, perché i loro ruoli di deploy vengono cancellati.

**Passare dal bootstrap di default a questo** (gli stack già deployati continuano a funzionare durante il passaggio):
```bash
./bootstrap.sh destroy eu-central-1     # toglie il bootstrap di default (cdk-hnb659fds-...)
./bootstrap.sh create eu-central-1      # crea quello con i nomi del repository
cd ../cdk33bedrockServerless && cdk deploy   # ogni progetto deployato va rideployato sul nuovo bootstrap
```




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


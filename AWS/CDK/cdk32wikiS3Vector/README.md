# AWS CDK 32 - Wiki con S3 Vectors (ricerca semantica senza LLM)

## 🚀 Panoramica

Una piccola wiki dove si caricano file di testo (documentazione, codice, configurazione) e si cerca **per significato**: alla domanda "esempio di Lambda che legge da una coda SQS" risponde con i file e i passaggi più pertinenti, con il numero delle righe, anche se non contengono quelle parole esatte. È pensata per indicizzare questo stesso repository, ma va bene per qualsiasi cartella di file di testo.

**Senza LLM**: non c'è nessun modello di chat. Serve solo un modello di *embedding*, Amazon Titan Text Embeddings V2, che trasforma ogni parte di file (e ogni domanda) in un vettore di 1024 numeri: testi con significato simile danno vettori vicini. Amazon **S3 Vectors** conserva i vettori e trova i più vicini alla domanda. Il risultato sono passaggi originali dei file, mai testo inventato, e una ricerca costa una frazione di millesimo di centesimo. Per avere anche una risposta scritta da un modello si veda l'esempio [cdk33bedrockServerless](../cdk33bedrockServerless/), che sulla stessa base aggiunge Nova Lite.

Cosa mostra l'esempio di S3 Vectors:
- **vector bucket e indice** creati con CDK (1024 dimensioni, distanza coseno)
- **metadati filtrabili e non filtrabili**: percorso, cartella, estensione e righe sono filtrabili, il testo della parte no (così può arrivare a 40 KB)
- **filtri nella ricerca**: "solo nella cartella `AWS/CDK`" con `$startsWith` sul percorso, "solo file `.py`" con `$in` sull'estensione, insieme con `$and`. I vector bucket creati dal 30 settembre 2026 hanno indici `ENHANCED`, che applicano il filtro *prima* della ricerca: i risultati sono sempre i più simili tra i file che lo rispettano
- **aggiornamento guidato dagli eventi S3**: un file caricato viene indicizzato, un file cancellato sparisce dall'indice, senza altri comandi
- **sincronizzazione incrementale** di una cartella: si caricano solo i file nuovi o modificati

Tutto a Francoforte (`eu-central-1`), con i tag standard del repository e i nomi fissi delle risorse.


## 🔧 Architettura

```
browser ── CloudFront ──┬── /*      bucket S3 del sito (privato, Origin Access Control)
                        └── /api/*  HTTP API Gateway ── Lambda Api ── Titan + S3 Vectors (ricerca con filtri)
pagina "File" o upload_folder.py ── bucket dei file  files/<percorso>
        ├── evento ObjectCreated ── Lambda Ingest ── parti per righe ── Titan ── S3 Vectors (scrittura)
        └── evento ObjectRemoved ── Lambda Ingest ── S3 Vectors (cancellazione)
```

```
├── app.py                              # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk, Francoforte
├── cdk32wiki_s3_vector/
│   └── cdk32wiki_s3_vector_stack.py    # 🏗️ bucket, S3 Vectors, Lambda, API Gateway, CloudFront, segreto
├── lambda/
│   ├── wiki.py                         # 🧩 parti per righe, embedding, vettori, filtri
│   ├── ingest.py                       # 📥 indicizzazione e cancellazione guidate dagli eventi S3
│   ├── api.py                          # ⚡ ricerca, caricamento, elenco, parti, cancellazione
│   └── requirements.txt                # 📦 boto3 del layer
├── upload_folder.py                    # 📂 sincronizza una cartella locale con la wiki
├── build_layer.sh                      # 📦 crea layer/ con boto3 recente
├── web/                                # 🌐 index.html (ricerca), files.html (file), common.js, style.css
└── tests/unit/                         # 🧪 test dello stack, delle Lambda e di upload_folder (senza AWS)
```

Dove sono i dati:
| Dato | Dove |
|------|------|
| File | bucket `alnao-dev-cdk-cdk32wikis3vector-files`, `files/<percorso>` |
| Stato dell'indicizzazione | stesso bucket, `status/<percorso>.json` (`uploading`, `processing`, `ready`, `error`, righe, parti) |
| Vettori | vector bucket `alnao-dev-cdk-cdk32wikis3vector-vectors`, indice `wiki`: un vettore per parte con chiave `<hash del percorso>#00000` |
| Metadati di ogni vettore | filtrabili: `path`, `folder` (primo livello), `extension`, `line_start`, `line_end`; non filtrabile: `text` |
| Chiave API | Secrets Manager, segreto `Cdk32WikiS3Vector-ApiKey` |

Come vengono preparati i file:
- solo file di testo: `.md .txt .py .js .ts .java .html .css .json .yaml .yml .toml .ini .cfg .sh .bat .sql .xml .csv .tf .robot .example`, più `Dockerfile`, `Makefile`, `README`, `LICENSE`; al massimo 1024 KB
- ogni file è diviso in **parti di circa 1500 caratteri che non spezzano le righe**, con 3 righe ripetute tra una parte e l'altra; ogni parte ricorda le sue righe di inizio e fine
- nell'embedding di ogni parte c'è anche il **percorso del file** (`File: AWS/CDK/cdk15sqs/lambda/consumer.py (righe 1-40)`), così si trovano i file anche per nome e cartella
- i risultati della ricerca sono raggruppati per file (al massimo 3 passaggi per file), dal più simile


Le risorse hanno nomi fissi al posto dei suffissi casuali di CDK, comprese quelle create internamente da CDK (svuotamento dei bucket al destroy, notifiche S3, copia del sito), e i tag standard del repository (`Name=aws-py-CDK.cdk32wikiS3Vector`, `Project=Development.aws.py-CDK.cdk32wikiS3Vector`, `ManagedBy=CDK`):

| Risorsa | Nome |
|---------|------|
| Stack CloudFormation | `Cdk32WikiS3VectorStack` |
| Bucket S3 | `alnao-dev-cdk-cdk32wikis3vector-files`, `alnao-dev-cdk-cdk32wikis3vector-site` |
| Vector bucket e indice | `alnao-dev-cdk-cdk32wikis3vector-vectors`, indice `wiki` |
| Lambda | `Cdk32WikiS3Vector-Api`, `-Ingest`, `-BucketNotifications`, `-AutoDeleteObjects`, `-BucketDeployment` |
| Log group (1 settimana) | `/Cdk32WikiS3Vector/Api`, `/Cdk32WikiS3Vector/Ingest`, ... uno per ogni Lambda |
| Ruoli IAM | `Cdk32WikiS3VectorStack-<Lambda>ServiceRole` |
| Policy IAM (inline nei ruoli) | `Cdk32WikiS3VectorStack-<Lambda>ServicePolicy` (la Lambda AutoDeleteObjects non ne ha) |
| Layer Lambda | `Cdk32WikiS3Vector-Libraries`, `Cdk32WikiS3Vector-AwsCli` |
| Segreto, HTTP API, OAC | `Cdk32WikiS3Vector-ApiKey`, `Cdk32WikiS3Vector-HttpApi`, `Cdk32WikiS3Vector-Site` |

Restano con un identificativo generato da AWS solo la distribuzione CloudFront (il dominio `xxxx.cloudfront.net`) e l'ID dell'API Gateway. I nomi dei bucket sono unici in tutto il mondo e quelli dei ruoli IAM in tutto l'account: lo stack si può installare una sola volta per account.

## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2, credenziali AWS e il bootstrap del repository ([AWS/CDK/bootstrap](../bootstrap/)).

```bash
cd PythonExamples/AWS/CDK/cdk32wikiS3Vector/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

./build_layer.sh                 # boto3 recente per le Lambda (client s3vectors)
pytest tests/unit                # test locali, senza AWS

../bootstrap/bootstrap.sh create # una volta per account: bootstrap con i nomi del repository
cdk deploy
```
`cdk deploy` stampa `SiteUrl` (il sito), `ApiKeyCommand` (il comando che legge la chiave da inserire in alto a destra nel sito) e `FilesBucket`.

**Caricare una cartella intera** con `upload_folder.py` (legge il bucket dagli output dello stack):
```bash
python upload_folder.py ../../.. --dry-run              # tutto il repository: mostra cosa farebbe
python upload_folder.py ../../..                        # carica i file nuovi o modificati
python upload_folder.py ../../../AWS --prefix AWS       # solo AWS/, salvata come AWS/...
python upload_folder.py ../../.. --delete               # toglie anche i file spariti dalla cartella
python upload_folder.py ../../.. --exclude "AI/*" --exclude "*.csv"
```
Lo script confronta l'MD5 di ogni file locale con l'ETag su S3, quindi rilanciarlo carica solo le differenze. Salta le cartelle nascoste e di servizio (`.git`, `node_modules`, `venv`, `cdk.out`, `layer`, `cache`, ...), i file nascosti (`.env`), quelli oltre 1024 KB e quelli che **sembrano contenere credenziali** (chiavi AWS `AKIA...`, `aws_secret_access_key`, chiavi private): la wiki è leggibile da chiunque abbia la chiave API, quindi un file con segreti non deve finirci. Il controllo è una rete di sicurezza, non una garanzia (e può saltare per prudenza file innocui, per esempio template CloudFormation con hash lunghi): prima del primo caricamento conviene sempre guardare l'elenco di `--dry-run`.

**Cleanup**: `cdk destroy` cancella tutto, compresi i file e l'indice vettoriale.


## 🧪 Uso

- **Cerca** (`index.html`): domanda, filtro sulla cartella (con i suggerimenti delle cartelle già indicizzate), filtro sul tipo di file e numero di passaggi da cercare (10, 20, 50, 100)
- **File** (`files.html`): carica un singolo file scegliendo la cartella di destinazione nella wiki, segue l'indicizzazione, elenca i file con il loro stato (filtrabile per percorso), mostra le parti con i numeri di riga, toglie un file, reindicizza tutto

| Metodo | Percorso | Descrizione |
|--------|----------|-------------|
| GET | `/api/health`, `/api/info` | stato del servizio; estensioni accettate e limiti (senza chiave) |
| POST | `/api/search` | `{"question": "...", "k": 20, "folder": "AWS/CDK", "extensions": [".py"]}` → file e passaggi, dal più simile |
| POST | `/api/uploads` | `{"path": "AWS/note.md"}` → POST prefirmato per caricare il file su S3 |
| GET | `/api/files` | file con il loro stato |
| GET | `/api/files/status?path=...` | stato di un file |
| GET | `/api/files/parts?path=...` | parti di un file con le righe |
| DELETE | `/api/files?path=...` | toglie il file (l'evento S3 cancella i vettori) |
| POST | `/api/reindex` | rimette in coda tutti i file |

Limiti: file fino a 1024 KB, fino a 100 passaggi per ricerca (una pagina di S3 Vectors), indicizzazione di un file entro 2 minuti.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a ottobre 2026, IVA esclusa; per S3 Vectors sono usati i prezzi pubblicati per US East. Scenario: questo repository indicizzato (circa 1000 file di testo, 5 MB, 5000 parti) e 50 ricerche al giorno.

| Voce | Calcolo | Al giorno | Al mese (30 gg) |
|------|---------|-----------|-----------------|
| Secrets Manager | 1 segreto × 0,40 $/mese | 0,01 $ | 0,40 $ |
| S3 Vectors | ~5000 vettori (~30 MB × 0,06 $/GB) e ~1500 ricerche (2,50 $/milione) | < 0,01 $ | 0,01 $ |
| Titan Embeddings V2 (ricerche) | 50 domande × ~20 token × 0,02 $/milione | < 0,01 $ | < 0,01 $ |
| S3 (file, stato, sito) | ~10 MB | < 0,01 $ | < 0,01 $ |
| Lambda, API Gateway, CloudFront | dentro il free tier | 0 $ | ~0,01 $ |
| CloudWatch Logs | pochi MB, conservati 1 settimana | < 0,01 $ | 0,01 $ |
| **Totale** | | **~0,015 $** | **~0,45 $** |

Una tantum, la prima indicizzazione dell'intero repository costa circa 0,06 $: circa 1,3 milioni di token di Titan (0,03 $), le scritture su S3 Vectors (0,20 $ per GB, con un minimo di 128 KB per chiamata: circa 0,025 $ per 1000 file) e le Lambda, dentro il free tier. Ogni sincronizzazione successiva costa solo per i file cambiati.

Il costo fisso è quasi tutto il segreto della chiave API: le ricerche, senza modello di chat, costano praticamente nulla.


## 🚀 Sviluppi Futuri
- 💬 **Risposta scritta** opzionale: i passaggi trovati come contesto per un modello di chat (come in cdk33bedrockServerless), solo quando serve
- 🔄 **Sincronizzazione automatica** dal repository: `upload_folder.py` lanciato da una GitHub Action a ogni push
- 🔗 **Link ai file** su GitHub con il numero di riga
- ⚖️ **Confronto** con Bedrock Knowledge Base su S3 Vectors: stessi file, chunking ed embedding gestiti da AWS


# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella misura massima possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


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


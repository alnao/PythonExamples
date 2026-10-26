# AWS CDK 34 - Bedrock Knowledge Base su S3 Vectors

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Lo stesso RAG (Retrieval-Augmented Generation) del [cdk33bedrockServerless](../cdk33bedrockServerless/), ma con la parte difficile affidata ad AWS: una **Amazon Bedrock Knowledge Base** legge i file, li divide in parti, calcola gli embedding e li scrive nell'indice **S3 Vectors**. Le Lambda chiedono soltanto i brani più simili alla domanda (`Retrieve`) e scrivono la risposta con Nova Lite. Tutto gira a Francoforte (`eu-central-1`), senza istanze accese, ed è descritto con **AWS CDK** in Python.

- **📄 Caricamento diretto su S3**: il browser chiede un POST prefirmato e carica il file nel bucket, che è la sorgente della Knowledge Base
- **🔄 Sincronizzazione automatica**: la Knowledge Base non segue il bucket da sola. Ogni file aggiunto o cancellato produce un evento S3 che va in una **coda SQS**; la Lambda Sync legge gli eventi a gruppi e avvia una sincronizzazione (incrementale) per tutto il gruppo
- **🧠 Knowledge Base gestita**: parser di default (testo di PDF, Word, Excel, HTML, CSV), parti da 300 token con il 20% di sovrapposizione, embedding Titan Text Embeddings V2 da 1024 dimensioni
- **🤖 Due modi di rispondere**: risposta scritta da Nova Lite con le fonti citate come `[1]`, `[2]`, oppure solo i brani trovati, senza modello di chat, come la wiki del [cdk32wikiS3Vector](../cdk32wikiS3Vector/)
- **🏷️ Costi con i tag**: le risposte passano da un *application inference profile* con i tag dello stack, così il costo di Nova Lite arriva al `Project` dell'esempio
- **🌐 Un solo dominio CloudFront** per il sito (bucket S3 privato) e per le API (`/api/*` verso HTTP API Gateway), con la **chiave API** di Secrets Manager nell'header `X-API-Key`

| Uso | Modello | Chiamato da |
|-----|---------|-------------|
| Embedding (file e domande) | Titan Text Embeddings V2, `amazon.titan-embed-text-v2:0` | la Knowledge Base |
| Risposte | Amazon Nova Lite, `eu.amazon.nova-lite-v1:0` | la Lambda Api, con il profilo `Cdk34BedrockKnowledgeBase-Chat` |

### Confronto con il cdk33

| | cdk33bedrockServerless (fatto a mano) | cdk34bedrockKnowledgeBase (gestito) |
|---|---|---|
| Lettura dei file | pypdf, python-docx, openpyxl, python-pptx in un layer | parser di default della Knowledge Base |
| Parti | 1000 caratteri con 200 di sovrapposizione, codice nostro | 300 token con il 20% di sovrapposizione, una riga di configurazione |
| Embedding e indice | Lambda Ingest da 3 GB, fino a 15 minuti per file | sincronizzazione della Knowledge Base |
| Aggiornamento | evento S3 → Lambda per ogni file | eventi S3 → SQS → una sincronizzazione per gruppo di file |
| Ricerca | `QueryVectors` su S3 Vectors | `Retrieve` della Knowledge Base |
| Risposta | Converse con Nova Lite (profilo con i tag) | uguale |
| Immagini | descritte da Nova Lite | non accettate (servirebbe il parser con un modello o Bedrock Data Automation) |
| PowerPoint | sì | no: il parser di default legge `.txt`, `.md`, `.html`, `.csv`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.pdf` |
| File e brani | file fino a 250 MB, fino a 1000 brani per domanda | file fino a 50 MB, fino a 100 brani per domanda |
| Parti visibili | sì, nella pagina admin | no: le parti restano dentro la Knowledge Base |
| Codice delle Lambda | ~650 righe, più il layer | ~440 righe, nessun layer |


## 🔧 Architettura

```
browser ── CloudFront ──┬── /*      bucket S3 del sito (privato, Origin Access Control)
                        └── /api/*  HTTP API Gateway ── Lambda Api ──┬── Knowledge Base: Retrieve (brani)
                                                                     ├── profilo Chat (con i tag) ── Nova Lite
                                                                     └── S3 (POST prefirmati, elenco, cancellazione)
browser ── POST prefirmato ── bucket documenti uploads/<doc_id>/<file>
                                   └── eventi ObjectCreated / ObjectRemoved ── coda SQS ── Lambda Sync
                                                                                    └── StartIngestionJob
Knowledge Base ── legge uploads/ ── parti ── Titan (embedding) ── indice S3 Vectors
```

```
├── app.py                          # 🚀 app CDK: tag standard, bootstrap alnao-dev-cdk, Francoforte
├── cdk34bedrock_knowledge_base/
│   ├── cdk34bedrock_knowledge_base_stack.py # 🏗️ bucket, S3 Vectors, Knowledge Base, coda, Lambda, API Gateway, CloudFront
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/
│   ├── api.py                      # ⚡ API (router, chiave, caricamenti, documenti, domande, sincronizzazioni)
│   ├── sync.py                     # 🔄 avvia la sincronizzazione per i messaggi della coda
│   └── kb.py                       # 🧩 S3, Knowledge Base (stato, Retrieve, sincronizzazioni), Converse
├── web/                            # 🌐 sito (index, admin, common.js, style.css)
├── tests/unit/                     # 🧪 test dello stack e delle Lambda (senza AWS)
└── cdk.json, requirements*.txt
```

Le Lambda non hanno un layer: il boto3 del runtime Python 3.13 ha già i client `bedrock-agent` e `bedrock-agent-runtime`.

Dove sono i dati:
| Dato | Dove |
|------|------|
| File originali | bucket `alnao-dev-cdk-cdk34bedrockknowledgebase-documents`, `uploads/<doc_id>/<nome file>` |
| Stato di ogni file | nella Knowledge Base (`ListKnowledgeBaseDocuments`): `INDEXED`, `FAILED` con il motivo, `IN_PROGRESS`, ...; `NOT_SYNCED` = file caricato e non ancora visto da una sincronizzazione |
| Parti ed embedding | vector bucket `alnao-dev-cdk-cdk34bedrockknowledgebase-vectors`, indice `docs`, scritti dalla Knowledge Base (`AMAZON_BEDROCK_TEXT` e `AMAZON_BEDROCK_METADATA` non filtrabili, altrimenti superano i 2 KB di metadati filtrabili per vettore) |
| Chiave API | Secrets Manager, segreto `Cdk34BedrockKnowledgeBase-ApiKey` |

**La coda di sincronizzazione**: per ogni sorgente può girare una sola sincronizzazione alla volta. La Lambda Sync riceve fino a 100 eventi insieme (aspetta al massimo 20 secondi per raccoglierli) e avvia una sincronizzazione: Bedrock confronta il bucket con l'indice, indicizza i file nuovi o cambiati e toglie quelli cancellati. Se ce n'è già una in corso, AWS risponde `ConflictException`, la Lambda fallisce e i messaggi tornano visibili dopo 2 minuti (il *visibility timeout* della coda) per un nuovo tentativo. Dopo 30 tentativi, circa un'ora, i messaggi finiscono nella coda `Cdk34BedrockKnowledgeBase-SyncFailed`: basta il pulsante "Sincronizza ora" della pagina admin per recuperare.


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate, accesso ai modelli Titan Text Embeddings V2 e Nova Lite in Bedrock.

```bash
cd PythonExamples/AWS/CDK/cdk34bedrockKnowledgeBase/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# test locali: sintesi dello stack e Lambda con AWS finto
pytest tests/unit

# una volta per account: bootstrap con i nomi e i tag del repository (vedi AWS/CDK/bootstrap)
#../bootstrap/bootstrap.sh create eu-central-1
cdk deploy
```

Al termine `cdk deploy` stampa:
- `SiteUrl`: l'indirizzo del sito (`https://xxxx.cloudfront.net`, la prima distribuzione impiega qualche minuto)
- `ApiKeyCommand`: il comando che legge la chiave API da inserire nel campo in alto a destra del sito
- `DocumentsBucket` e `KnowledgeBaseId`: il bucket dei documenti e l'ID della Knowledge Base (per provarla anche dalla console Bedrock)

**Tag**: tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk34bedrockKnowledgeBase`, `ManagedBy=CDK`), anche quelle di supporto create da CDK. Non hanno tag solo i tipi che CloudFormation non permette di taggare: sorgente della Knowledge Base, layer Lambda, policy IAM inline, policy di bucket e code, route e integrazioni di API Gateway, OAC, permessi Lambda. Il test `test_all_resources_tagged` controlla ogni risorsa del template e fallisce se ne compare una nuova senza tag.

**Costi di Bedrock con i tag**: una chiamata a Bedrock con l'ID del modello produce un costo senza tag, che in Cost Explorer non arriva a nessun `Project`. Le risposte usano quindi il profilo `Cdk34BedrockKnowledgeBase-Chat`, copiato dal profilo cross-region di Nova Lite e con i tag dello stack: la Lambda Api lo passa come `modelId` a Converse. La documentazione AWS garantisce i profili dell'applicazione solo per InvokeModel e Converse: per questo la risposta è scritta da Converse con i brani di `Retrieve`, e non con `RetrieveAndGenerate`. Gli **embedding restano senza tag**, perché li calcola la Knowledge Base con il modello di base; sono la voce più piccola (vedi i costi). Perché il tag compaia in Cost Explorer, `Project` deve essere attivato come *cost allocation tag* nella console Billing (una volta per account).

Le risorse hanno nomi fissi al posto dei suffissi casuali di CDK, comprese quelle create internamente da CDK (svuotamento dei bucket al destroy, notifiche S3, copia del sito):

| Risorsa | Nome |
|---------|------|
| Bucket S3 | `alnao-dev-cdk-cdk34bedrockknowledgebase-documents`, `alnao-dev-cdk-cdk34bedrockknowledgebase-site` |
| Vector bucket e indice | `alnao-dev-cdk-cdk34bedrockknowledgebase-vectors`, indice `docs` |
| Knowledge Base e sorgente | `Cdk34BedrockKnowledgeBase`, sorgente `Documents` |
| Profilo di inferenza | `Cdk34BedrockKnowledgeBase-Chat` |
| Code SQS | `Cdk34BedrockKnowledgeBase-Sync`, `Cdk34BedrockKnowledgeBase-SyncFailed` |
| Lambda | `Cdk34BedrockKnowledgeBase-Api`, `-Sync`, `-BucketNotifications`, `-AutoDeleteObjects`, `-BucketDeployment` |
| Log group (1 settimana) | `/Cdk34BedrockKnowledgeBase/Api`, `/Cdk34BedrockKnowledgeBase/Sync`, ... uno per ogni Lambda |
| Ruoli IAM | `Cdk34BedrockKnowledgeBaseStack-<Lambda>ServiceRole`, `Cdk34BedrockKnowledgeBaseStack-KnowledgeBaseServiceRole` |
| Policy IAM (inline nei ruoli) | `Cdk34BedrockKnowledgeBaseStack-<Lambda>ServicePolicy` |
| Layer Lambda | `Cdk34BedrockKnowledgeBase-AwsCli` (della copia del sito) |
| Segreto, HTTP API, OAC | `Cdk34BedrockKnowledgeBase-ApiKey`, `Cdk34BedrockKnowledgeBase-HttpApi`, `Cdk34BedrockKnowledgeBase-Site` |

Restano con un identificativo generato solo le risorse che non hanno un nome scelto dall'utente: la distribuzione CloudFront (il dominio `xxxx.cloudfront.net`), l'API Gateway, la Knowledge Base, la sorgente e il profilo (nei loro ID e ARN). I nomi dei bucket sono unici in tutto il mondo e quelli dei ruoli IAM in tutto l'account: lo stack si può installare una sola volta per account.

Il ruolo della Knowledge Base è assumibile solo da Bedrock per le Knowledge Base dell'account e ha le policy **inline**: la Knowledge Base controlla l'accesso all'indice già quando viene creata, e una policy separata potrebbe arrivare dopo.

**Cleanup**: `cdk destroy` cancella tutto: la sorgente ha `DataDeletionPolicy=DELETE`, quindi i vettori si cancellano con lei, poi la Knowledge Base, l'indice e i bucket con il loro contenuto. Il bootstrap resta, perché è condiviso con gli altri progetti CDK: quando nella region non ci sono più stack CDK si toglie con `../bootstrap/bootstrap.sh destroy eu-central-1`.


## 🧪 API

Le API sono sullo stesso dominio del sito, sotto `/api`; tranne `health` e `supported-formats` richiedono l'header `X-API-Key`.

| Metodo | Percorso | Descrizione |
|--------|----------|-------------|
| GET | `/api/health` | stato del servizio |
| GET | `/api/supported-formats` | formati accettati, dimensione massima, brani massimi |
| POST | `/api/uploads` | `{"filename": "...", "doc_id": "..."}` → POST prefirmato per caricare il file su S3 (massimo 50 MB, valido 15 minuti); cancella gli altri file dello stesso `doc_id` |
| GET | `/api/documents` | file con lo stato della Knowledge Base |
| GET | `/api/documents/{doc_id}/status` | stato di un documento |
| DELETE | `/api/documents/{doc_id}` | cancella i file del documento; la sincronizzazione che segue toglie le sue parti dall'indice |
| POST | `/api/query` | `{"question": "...", "k": 20, "mode": "answer"}` → risposta e fonti; con `"mode": "search"` solo i brani (`answer` vale `null`); `k` da 1 a 100 |
| GET | `/api/sync` | ultime 10 sincronizzazioni con i numeri di file esaminati, indicizzati, tolti, in errore |
| POST | `/api/sync` | avvia una sincronizzazione (`409` se ce n'è già una in corso) |

```bash
SITE=https://xxxx.cloudfront.net
KEY=$(aws secretsmanager get-secret-value --secret-id Cdk34BedrockKnowledgeBase-ApiKey --region eu-central-1 --query SecretString --output text)

# 1. POST prefirmato, 2. upload su S3 con i campi ricevuti, 3. stato (NOT_SYNCED -> IN_PROGRESS -> INDEXED)
curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"filename": "contratto.txt", "doc_id": "contratto"}' $SITE/api/uploads > upload.json
curl -s $(jq -r '.upload.fields | to_entries | map("-F \(.key)=\(.value)") | join(" ")' upload.json) -F "file=@contratto.txt" $(jq -r .upload.url upload.json)
curl -s -H "X-API-Key: $KEY" $SITE/api/documents/contratto/status

curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"question": "Qual è la durata del contratto?"}' $SITE/api/query
curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"question": "durata", "mode": "search", "k": 5}' $SITE/api/query
```

Limiti da conoscere:
- un file caricato diventa cercabile dopo la sincronizzazione: di solito meno di un minuto per pochi file (20 secondi di raccolta degli eventi, poi la sincronizzazione), di più se ne è già in corso un'altra
- file fino a 50 MB (limite della Knowledge Base); un PDF scansionato non produce testo, perché il parser di default non fa OCR
- al massimo 100 brani per domanda (limite di `Retrieve`); la pagina chiede conferma se una domanda può costare più di 0,01 $
- API Gateway chiude le richieste dopo 30 secondi: con Nova Lite e al massimo 100 brani da 300 token la risposta arriva in pochi secondi


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a ottobre 2026, IVA esclusa, gli stessi del cdk33. Verificare sempre sulle pagine dei prezzi AWS e di [Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/). La Knowledge Base non ha un costo proprio con S3 Vectors e il parser di default: si pagano gli embedding, l'indice e il modello di chat. Attenzione: con OpenSearch Serverless come indice ci sarebbe invece un costo fisso di centinaia di dollari al mese, anche senza traffico.

Scenario uguale a quello del cdk33: ogni giorno 5 documenti caricati (circa 100.000 caratteri) e 50 domande con 20 brani.

| Voce | Calcolo | Al giorno | Al mese (30 gg) |
|------|---------|-----------|-----------------|
| Lambda | poche centinaia di richieste brevi da 256 MB (dentro il free tier) | 0 $ | 0 $ |
| SQS | il servizio Lambda interroga la coda di continuo (long polling): centinaia di migliaia di richieste al mese anche a coda vuota, di solito dentro il milione gratuito | 0 $ | 0 $ (fino a ~0,30 $ senza free tier) |
| API Gateway HTTP API | ~10.000 richieste/mese × 1,20 $/milione | < 0,01 $ | 0,01 $ |
| CloudFront | dentro il free tier sempre gratuito | 0 $ | 0 $ |
| S3 (documenti, sito) | ~1 GB × 0,0245 $/GB-mese + richieste | < 0,01 $ | 0,03 $ |
| S3 Vectors | ~3.600 parti al mese (150 documenti): archiviazione, scritture e ~1.500 ricerche/mese | < 0,01 $ | 0,01 $ |
| Secrets Manager | 1 segreto × 0,40 $/mese | 0,01 $ | 0,40 $ |
| CloudWatch Logs | pochi MB di log, conservati 1 settimana | < 0,01 $ | 0,01 $ |
| Bedrock Titan Embeddings V2 | ~30.000 token/giorno (parti con sovrapposizione) × 0,20 $/milione, **senza tag** | < 0,01 $ | 0,18 $ |
| Bedrock Nova Lite (risposte) | 50 domande × (~6.300 token in, cioè 20 brani da 300 token, + ~300 out) | 0,03 $ | 0,88 $ |
| **Totale** | | **~0,05 $** | **~1,52 $** |

Note sui costi:
- senza traffico il costo fisso è di circa 0,45 $ al mese (segreto, file su S3, vettori archiviati)
- la modalità "Solo i brani" non usa Nova Lite: costa solo l'embedding della domanda, una frazione di millesimo di centesimo
- una sincronizzazione ricalcola gli embedding solo dei file nuovi o cambiati: "Sincronizza ora" su un bucket già allineato non costa nulla in Bedrock
- con 100 brani una domanda costa circa 0,003 $ (30.000 token in ingresso), contro 0,012 $ del cdk33 con 1000 brani


## 🚀 Sviluppi Futuri
- 🖼️ **Immagini e PDF scansionati** con il parser basato su un modello (Nova Lite) o con Bedrock Data Automation, da attivare solo se servono perché si pagano per pagina
- 🏷️ **Embedding con i tag**: verificare se la Knowledge Base accetta un profilo dell'applicazione come modello di embedding
- 🧪 **Confronto della qualità** tra cdk33 e cdk34 sugli stessi documenti e sulle stesse domande
- 🔀 **Reranking** dei brani con un modello di rerank di Bedrock prima della risposta


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


# AWS CDK 33 - Bedrock Serverless, Pocket RAG senza server

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Versione **serverless** del [Pocket RAG su EC2](../../Bedrock/): stesso sistema RAG (Retrieval-Augmented Generation) con Amazon Bedrock, ma senza istanze accese. Si paga solo quando si carica un documento o si fa una domanda. Tutto gira a Francoforte (`eu-central-1`) ed è descritto con **AWS CDK** in Python.

- **📄 Caricamento diretto su S3**: il browser chiede un POST prefirmato e carica il file nel bucket; l'evento S3 avvia la Lambda che lo indicizza
- **🧠 S3 Vectors** come database vettoriale: indice da 1024 dimensioni (Titan Text Embeddings V2) con distanza coseno, senza cluster da gestire
- **🤖 Converse API** di Bedrock per le risposte e per le immagini (Amazon Nova Lite), con le fonti citate come `[1]`, `[2]`
- **🌐 Un solo dominio CloudFront** per il sito (bucket S3 privato) e per le API (`/api/*` verso HTTP API Gateway): HTTPS e niente CORS
- **🔐 Chiave API** generata da Secrets Manager e richiesta nell'header `X-API-Key`
- **📋 Formati**: gli stessi della versione EC2 (testi, PDF, Word, Excel, PowerPoint, immagini), ma **senza OCR**: le pagine PDF senza testo vengono saltate

| Uso | Modello | ID Bedrock |
|-----|---------|------------|
| Embedding | Titan Text Embeddings V2 | `amazon.titan-embed-text-v2:0` |
| Risposte | Amazon Nova Lite | `eu.amazon.nova-lite-v1:0` |
| Immagini | Amazon Nova Lite (circa 0,0003 $ a immagine) | `eu.amazon.nova-lite-v1:0` |

I modelli si cambiano in `MODELS` nello stack: la policy IAM delle Lambda viene generata dagli stessi ID. Con `IMAGE_MODEL` vuoto le immagini non vengono accettate (qui non c'è Tesseract: l'OCR gratuito delle immagini c'è solo nella versione EC2).


## 🔧 Architettura

```
browser ── CloudFront ──┬── /*      bucket S3 del sito (privato, Origin Access Control)
                        └── /api/*  HTTP API Gateway ── Lambda Api ──┬── Bedrock (domande, profilo Chat)
                                                                     ├── S3 Vectors (ricerca)
                                                                     └── S3 (stato, POST prefirmati)
browser ── POST prefirmato ── bucket documenti uploads/<doc_id>/<file>
                                   └── evento ObjectCreated ── Lambda Ingest ──┬── Bedrock (profili Embedding e Image)
                                                                              └── S3 Vectors (scrittura)
```

```
├── app.py                          # 🚀 app CDK: tag standard e stack a Francoforte
├── cdk33bedrock_serverless/
│   ├── cdk33bedrock_serverless_stack.py # 🏗️ bucket, S3 Vectors, profili Bedrock, Lambda, API Gateway, CloudFront, segreto
│   └── tags.py                     # 🏷️ tag standard e apply_tags (usata da app.py e dai test)
├── lambda/
│   ├── api.py                      # ⚡ API (router, chiave, domande, documenti, reindex)
│   ├── ingest.py                   # 📥 indicizzazione dei file caricati
│   ├── rag.py                      # 🧩 Bedrock, S3 Vectors, estrazione del testo, chunking
│   └── requirements.txt            # 📦 librerie del layer
├── build_layer.sh                  # 📦 crea layer/ con le librerie per Lambda (Linux x86_64, Python 3.13)
├── web/                            # 🌐 sito (index, admin, common.js, style.css)
├── tests/unit/                     # 🧪 test dello stack e delle Lambda (senza AWS)
└── cdk.json, requirements*.txt
```

Dove sono i dati:
| Dato | Dove |
|------|------|
| File originali | bucket `alnao-dev-cdk-cdk33bedrockserverless-documents`, `uploads/<doc_id>/<nome file>` |
| Stato dell'indicizzazione | stesso bucket, `status/<doc_id>.json` (`uploading`, `processing`, `ready`, `error`, numero di parti) |
| Parti ed embedding | vector bucket `alnao-dev-cdk-cdk33bedrockserverless-vectors`, indice `docs`: un vettore per parte con chiave `<doc_id>#00000` e metadati `doc_id`, `filename`, `chunk`, `text` (`text` non filtrabile) |
| Chiave API | Secrets Manager, segreto `Cdk33BedrockServerless-ApiKey` |

Non c'è nessun indice locale da salvare: se serve ricalcolare tutto (per esempio dopo aver cambiato il modello di embedding), il pulsante "Ricostruisci indice" della pagina admin riscrive ogni file su se stesso e l'evento S3 lo fa reindicizzare.


## 🛠️ Deploy

Prerequisiti: Python 3.12+, Node.js e AWS CDK v2 (`npm install -g aws-cdk`), credenziali AWS configurate.

```bash
cd PythonExamples/AWS/CDK/cdk33bedrockServerless/
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# librerie delle Lambda (da rifare se cambia lambda/requirements.txt)
./build_layer.sh

# test locali: sintesi dello stack e Lambda con AWS finto
pytest tests/unit

# una volta per account: bootstrap con i nomi e i tag del repository (vedi AWS/CDK/bootstrap)
../bootstrap/bootstrap.sh create eu-central-1
cdk deploy
```

Al termine `cdk deploy` stampa:
- `SiteUrl`: l'indirizzo del sito (`https://xxxx.cloudfront.net`, la prima distribuzione impiega qualche minuto)
- `ApiKeyCommand`: il comando che legge la chiave API da inserire nel campo in alto a destra del sito
- `DocumentsBucket`: il bucket dei documenti

Tutte le risorse hanno i tag standard del repository (`Project=Development.aws.py-CDK.cdk33bedrockServerless`, `ManagedBy=CDK`), anche quelle di supporto create da CDK; non hanno tag solo i tipi che CloudFormation non permette di taggare (layer Lambda, policy IAM inline, route e integrazioni di API Gateway, OAC, permessi Lambda, policy dei bucket). Il test `test_all_resources_tagged` controlla ogni risorsa del template e fallisce se ne compare una nuova senza tag.

**Costi di Bedrock con i tag**: una chiamata a Bedrock con l'ID del modello (`eu.amazon.nova-lite-v1:0`) produce un costo senza tag, che in Cost Explorer non arriva a nessun `Project`, ed è la voce principale di questo esempio. Per questo lo stack crea tre *application inference profile* con i tag dello stack, uno per uso (`Embedding` copiato da Titan, `Chat` e `Image` copiati dal profilo cross-region di Nova Lite), e le Lambda ricevono i loro ARN in `EMBEDDING_MODEL`, `CHAT_MODEL` e `IMAGE_MODEL`: Converse e InvokeModel accettano l'ARN come `modelId`. I profili non costano nulla; nel CUR si vede anche la divisione tra embedding, domande e immagini. Perché il tag compaia in Cost Explorer `Project` deve essere attivato come *cost allocation tag* nella console Billing (una volta per account).

Le risorse hanno nomi fissi al posto dei suffissi casuali di CDK, comprese quelle create internamente da CDK (svuotamento dei bucket al destroy, notifiche S3, copia del sito):

| Risorsa | Nome |
|---------|------|
| Bucket S3 | `alnao-dev-cdk-cdk33bedrockserverless-documents`, `alnao-dev-cdk-cdk33bedrockserverless-site` |
| Vector bucket e indice | `alnao-dev-cdk-cdk33bedrockserverless-vectors`, indice `docs` |
| Lambda | `Cdk33BedrockServerless-Api`, `-Ingest`, `-BucketNotifications`, `-AutoDeleteObjects`, `-BucketDeployment` |
| Log group (1 settimana) | `/Cdk33BedrockServerless/Api`, `/Cdk33BedrockServerless/Ingest`, ... uno per ogni Lambda |
| Ruoli IAM | `Cdk33BedrockServerlessStack-<Lambda>ServiceRole` |
| Policy IAM (inline nei ruoli) | `Cdk33BedrockServerlessStack-<Lambda>ServicePolicy` (la Lambda AutoDeleteObjects non ne ha) |
| Layer Lambda | `Cdk33BedrockServerless-Libraries`, `Cdk33BedrockServerless-AwsCli` |
| Profili di inferenza Bedrock | `Cdk33BedrockServerless-Embedding`, `Cdk33BedrockServerless-Chat`, `Cdk33BedrockServerless-Image` |
| Segreto, HTTP API, OAC | `Cdk33BedrockServerless-ApiKey`, `Cdk33BedrockServerless-HttpApi`, `Cdk33BedrockServerless-Site` |

Restano con un identificativo generato solo le risorse che non hanno un nome scelto dall'utente: l'ID della distribuzione CloudFront (il dominio `xxxx.cloudfront.net`), quello dell'API Gateway e quello dei profili di inferenza (nel loro ARN). I nomi dei bucket sono unici in tutto il mondo e quelli dei ruoli IAM in tutto l'account: lo stack si può installare una sola volta per account.

**Cleanup**: `cdk destroy` cancella tutto, compresi i bucket con il loro contenuto e l'indice vettoriale. Il bootstrap resta, perché è condiviso con gli altri progetti CDK: quando nella region non ci sono più stack CDK si toglie con `../bootstrap/bootstrap.sh destroy eu-central-1`.


## 🧪 API

Le API sono sullo stesso dominio del sito, sotto `/api`; tranne `health` e `supported-formats` richiedono l'header `X-API-Key`.

| Metodo | Percorso | Descrizione |
|--------|----------|-------------|
| GET | `/api/health` | stato del servizio |
| GET | `/api/supported-formats` | formati accettati |
| POST | `/api/uploads` | `{"filename": "...", "doc_id": "..."}` → POST prefirmato per caricare il file su S3 (massimo 250 MB, valido 15 minuti) |
| GET | `/api/documents` | documenti con il loro stato |
| GET | `/api/documents/{doc_id}/status` | stato dell'indicizzazione |
| GET | `/api/documents/{doc_id}` | stato e parti del documento |
| DELETE | `/api/documents/{doc_id}` | fa dimenticare il documento (vettori, file e stato) |
| POST | `/api/query` | `{"question": "...", "k": 42}` → risposta, fonti usate, brani trovati (`found`) e usati (`used`); `k` da 1 a 1000 |
| POST | `/api/generate` | `{"prompt": "..."}` → risposta diretta del modello |
| POST | `/api/reindex` | rimette in coda tutti i file per l'indicizzazione |

```bash
SITE=https://xxxx.cloudfront.net
KEY=$(aws secretsmanager get-secret-value --secret-id <nome del segreto> --region eu-central-1 --query SecretString --output text)

# 1. POST prefirmato, 2. upload su S3 con i campi ricevuti, 3. stato
curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"filename": "contratto.txt", "doc_id": "contratto"}' $SITE/api/uploads > upload.json
curl -s $(jq -r '.upload.fields | to_entries | map("-F \(.key)=\(.value)") | join(" ")' upload.json) -F "file=@contratto.txt" $(jq -r .upload.url upload.json)
curl -s -H "X-API-Key: $KEY" $SITE/api/documents/contratto/status

curl -s -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"question": "Qual è la durata del contratto?"}' $SITE/api/query
```

Limiti da conoscere:
- API Gateway chiude le richieste dopo 30 secondi: le domande con Nova Lite rispondono in pochi secondi, ma un modello di chat molto più lento potrebbe non bastare
- file fino a 250 MB (`MAX_UPLOAD_MB` nello stack): la pagina controlla la dimensione prima di caricare, mostra l'avanzamento e, se S3 rifiuta il file, il motivo (per esempio `EntityTooLarge`)
- **conferma dei costi**: prima di caricare un file la pagina stima il costo degli embedding dal suo peso (per PDF e formati Office con un rapporto prudente tra testo e byte) e, oltre 0,01 $, chiede conferma; lo stesso per una domanda con 1000 brani (circa 0,012 $). "Ricostruisci indice" mostra sempre la stima, calcolata sui caratteri dei documenti già indicizzati
- l'indicizzazione di un file ha a disposizione 15 minuti, il massimo di Lambda, con 3008 MB di memoria (il massimo concesso di default agli account nuovi) e senza nuovi tentativi automatici: se il tempo sta per finire (lettura del PDF o embedding) il documento passa in stato `error` con il motivo, invece di restare `processing`
- un PDF grande ma scansionato produce poco o nessun testo, perché qui non c'è OCR
- una domanda cerca da 5 a 1000 brani (42 di default; S3 Vectors li restituisce a pagine da 100). I più simili entrano nel contesto del modello fino a 600.000 caratteri, circa 150.000 token (`CONTEXT_MAX_CHARS` nelle Lambda, Nova Lite ne accetta 300.000): gli altri vengono trovati ma non usati, e la pagina lo dice. Con molti brani la risposta richiede più secondi, sempre entro i 29 di API Gateway
- l'elenco dei documenti legge tutti i file di stato: va bene per qualche centinaio di documenti


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a ottobre 2026, IVA esclusa; per S3 Vectors sono usati i prezzi pubblicati per US East (Francoforte può essere leggermente più cara). Verificare sempre sulle pagine dei prezzi AWS e di [Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/); per Amazon Nova Lite con il profilo EU la stima usa 0,08 $ per milione di token in input e 0,31 $ in output. **Titan Text Embeddings V2 costa 0,20 $ per milione di token**: prezzo verificato sul conto del 13 ottobre 2026 (1,35 milioni di token addebitati 0,27 $), dieci volte quello usato nelle prime versioni di questo README.

Scenario uguale a quello della versione EC2: ogni giorno 5 documenti caricati (circa 100 parti), 2 immagini e 50 domande.

| Voce | Calcolo | Al giorno | Al mese (30 gg) |
|------|---------|-----------|-----------------|
| Lambda | ~200 GB-secondi e ~350 richieste al giorno (dentro il free tier: 0 $) | < 0,01 $ | 0,10 $ |
| API Gateway HTTP API | ~10.000 richieste/mese × 1,20 $/milione | < 0,01 $ | 0,01 $ |
| CloudFront | dentro il free tier sempre gratuito (1 TB, 10 milioni di richieste) | 0 $ | 0 $ |
| S3 (documenti, stato, sito) | ~1 GB × 0,0245 $/GB-mese + richieste | < 0,01 $ | 0,03 $ |
| S3 Vectors | ~3.000 vettori (~17 MB): archiviazione, scritture (minimo 128 KB a chiamata) e ~1.500 ricerche/mese | < 0,01 $ | 0,01 $ |
| Secrets Manager | 1 segreto × 0,40 $/mese | 0,01 $ | 0,40 $ |
| CloudWatch Logs | pochi MB di log, conservati 1 settimana | < 0,01 $ | 0,01 $ |
| Bedrock Titan Embeddings V2 | ~31.000 token/giorno × 0,20 $/milione | < 0,01 $ | 0,19 $ |
| Bedrock Nova Lite (risposte) | 50 domande × (~12.000 token in, cioè 42 brani, + ~300 out) | 0,05 $ | 1,58 $ |
| Bedrock Nova Lite (immagini) | 2 immagini × (~1.700 token in + ~500 out) | < 0,01 $ | 0,02 $ |
| **Totale** | | **~0,08 $** | **~2,35 $** |

Note sui costi:
- un file molto grande costa di più da indicizzare: 15 minuti della Lambda da 3 GB sono circa 0,045 $, più gli embedding: circa 0,06 $ per milione di caratteri di testo (0,20 $ per milione di token, parti sovrapposte comprese). Esempio reale: due documenti di qualche centinaio di pagine sono stati 1,35 milioni di token, cioè 0,27 $
- senza traffico il costo fisso è di circa 0,45 $ al mese (segreto, file su S3, vettori archiviati)
- la voce principale è Nova Lite per le domande, e dipende dai brani usati: circa 0,0002 $ a domanda con 5 brani, 0,001 $ con 42, 0,012 $ con il contesto pieno (1000 brani); poi il segreto (0,40 $ al mese). Le immagini con Nova Lite costano circa 0,0003 $ l'una
- con 1000 domande al giorno da 42 brani il totale sale a circa 1,10 $ al giorno (~33 $ al mese), quasi tutto Nova Lite; con 5 brani a domanda resta sotto 0,30 $ al giorno


## 🚀 Sviluppi Futuri
- ✅ **Versione gestita** con Bedrock Knowledge Base al posto di estrazione, chunking ed embedding fatti a mano: [cdk34bedrockKnowledgeBase](../cdk34bedrockKnowledgeBase/), con il confronto tra le due
- 🔍 **OCR** dei PDF scansionati con Amazon Textract (asincrono, attivato dalla Lambda Ingest)
- 👥 **Login** con Amazon Cognito al posto della chiave unica, con filtro per utente sui metadati dei vettori
- 💬 **Risposte in streaming** con Lambda Function URL e `converse_stream`, senza il limite dei 30 secondi
- 📊 **Allarme sui costi** di Bedrock con AWS Budgets




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


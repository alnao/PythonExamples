# AWS Bedrock RAG Example - Pocket RAG su EC2

> ⚠️ Nota importante: l'esecuzione di questi esempi nel cloud potrebbe causare costi indesiderati ⚠️

## 🚀 Panoramica

Questo esempio implementa un sistema **RAG (Retrieval-Augmented Generation)** su una istanza EC2 a Francoforte (`eu-central-1`) con **Amazon Bedrock**: si caricano documenti, il sistema li divide in parti, ne calcola gli embedding e risponde alle domande in italiano citando le fonti.
- **📄 Formati supportati**
  - **Testi**: `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.css`, `.js`, `.py`, `.java`, `.cpp`, `.c`, `.h`
  - **Documenti**: `.pdf` (testo con pypdf, OCR con Tesseract solo per le pagine senza testo), `.docx` (anche le tabelle), `.xlsx`, `.pptx`
  - **Immagini**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`: la descrizione (con il testo trascritto) viene generata da Amazon Nova Lite e indicizzata come un testo; in alternativa, gratis, solo il testo letto con l'OCR di Tesseract
- **🔍 Ricerca semantica** su ChromaDB con distanza coseno, parti di circa 1000 caratteri con 200 caratteri di sovrapposizione
- **🤖 Risposte** generate da Amazon Nova Lite con la **Converse API** di Bedrock (stesso formato per tutti i modelli), con le fonti citate come `[1]`, `[2]`
- **💾 Persistenza**: originali su S3, indice ChromaDB su disco con backup automatico su S3 e ricostruzione completa dai file (`/api/reindex`)
- **🔐 Sicurezza**: chiave API (header `X-API-Key`) su tutte le API, porta 80 aperta solo al proprio IP, nessuna porta SSH (si entra con Session Manager), policy IAM con i permessi minimi
- **🌐 Interfaccia web** in italiano: pagina per caricare e chiedere, pagina admin per vedere i documenti e farli *dimenticare*; prima di caricare un file grande o di ricostruire l'indice mostra il costo stimato degli embedding e chiede conferma

Esiste anche la versione **senza server** (Lambda, API Gateway, CloudFront, S3 Vectors) nella cartella [`AWS/CDK/cdk33bedrockServerless`](../CDK/cdk33bedrockServerless/): costa molto meno se usata poco, ma non ha l'OCR.

Modelli usati (configurabili nel file `.env`):

| Uso | Modello | ID Bedrock |
|-----|---------|------------|
| Embedding | Titan Text Embeddings V2 (1024 dimensioni) | `amazon.titan-embed-text-v2:0` |
| Risposte | Amazon Nova Lite | `eu.amazon.nova-lite-v1:0` (profilo cross-region EU) |
| Immagini | Amazon Nova Lite (circa 0,0003 $ a immagine) | `eu.amazon.nova-lite-v1:0` (profilo cross-region EU) |

Per non spendere nulla sulle immagini si lascia vuoto `IMAGE_MODEL` nel file `.env`: il backend legge il testo dell'immagine con Tesseract sull'istanza (gratis, ma senza descrizione del contenuto visivo; un'immagine senza testo viene rifiutata).

Note sull'accesso ai modelli:
- da ottobre 2025 i modelli serverless di Bedrock sono abilitati automaticamente su ogni account; l'accesso si controlla con le policy IAM e le SCP
- a Francoforte Nova Lite si usa con il profilo `eu.`, che instradano le richieste nelle region europee; la policy IAM autorizza sia il profilo sia il modello
- prima del deploy si può verificare che i modelli rispondano con `python check_model.py` (costa frazioni di centesimo)
- i modelli vengono ritirati periodicamente (Llama 3.2 3B, usato nelle prime versioni, oggi risponde "end of its life"): lo stato è nella [pagina del ciclo di vita dei modelli](https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle-legacy.html); in quel caso la pagina mostra l'errore di AWS e basta cambiare il modello in `.env` e `policy.json`


## 🔧 Architettura del Sistema

```
browser ── :80 Apache (solo dal tuo IP) ── 127.0.0.1:8000 uvicorn/FastAPI ──┬── Bedrock (Converse + Titan)
                                                                             ├── ChromaDB (disco EBS)
                                                                             └── S3 (originali + backup indice)
```

```
├── backend.py             # 🐍 FastAPI: API sotto /api e sito statico su /
├── requirements.txt       # 📦 dipendenze Python (usate anche dallo user data)
├── .env.example           # ⚙️ configurazione del backend (copiare in .env)
├── check_model.py         # 🔍 verifica che i modelli Bedrock rispondano
├── bedrock_rag_stack.sh   # 🚀 creazione, aggiornamento del codice e distruzione delle risorse con la AWS CLI
├── user_data.sh           # ⚙️ template dello user data dell'EC2 (pacchetto dal bucket, servizio systemd, Apache)
├── policy.json            # 🔐 template della policy IAM (segnaposto sostituiti dallo script)
├── web/
│   ├── index.html/js      # 🌐 carica documenti e fai domande
│   ├── admin.html/js      # 🛠️ documenti, parti, "dimentica", ricostruzione dell'indice
│   ├── common.js          # ⚡ chiave API, chiamate alle API, escape dell'HTML
│   └── style.css
├── chroma/                # 🗄️ indice vettoriale (creato all'avvio, non versionato)
└── venv/                  # 🐍 ambiente Python (non versionato)
```

Dove sono i dati:
| Dato | Dove | Note |
|------|------|------|
| File originali | S3 `uploads/<doc_id>/<nome file>` | caricare un file con un `doc_id` esistente sostituisce il documento |
| Parti, embedding e metadati | ChromaDB nella cartella `chroma/` dell'EC2 | dopo ogni modifica viene salvato su S3 in `index/chroma.tar.gz` e, se la cartella è vuota (istanza nuova), viene ripristinato all'avvio |
| Chiave API | SSM Parameter Store `/<progetto>/api-key` (SecureString) | generata dallo script, letta dal backend all'avvio |
| Codice dell'applicazione | S3 `app/pocket-rag.tar.gz` e cartella `/opt/pocket-rag` dell'EC2 | il pacchetto viene ricreato dallo script a ogni `create` e `update` |

Se si perde anche il backup, `POST /api/reindex` (pulsante "Ricostruisci indice" nella pagina admin) rilegge tutti i file da S3 e ricalcola gli embedding.


## 🛠️ Installazione e Deploy

- Opzione 1: **Deploy automatico con lo script** (AWS CLI, region di default Francoforte)
  ```bash
  git clone https://github.com/alnao/PythonExamples.git
  cd PythonExamples/AWS/Bedrock/
  chmod +x bedrock_rag_stack.sh

  # senza parametri chiede azione, nome del progetto, region e CIDR mostrando i default
  # (create, Bedrock, eu-central-1, il tuo IP pubblico), poi riepiloga e chiede conferma
  ./bedrock_rag_stack.sh
  # oppure tutto da riga di comando (la porta 80 viene aperta solo al tuo IP attuale)
  ./bedrock_rag_stack.sh create Bedrock eu-central-1
  ./bedrock_rag_stack.sh create Bedrock eu-central-1 203.0.113.0/24
  ```
  Il nome del progetto (default `Bedrock`) è il prefisso dei nomi delle risorse (bucket `bedrock-alnao-bucket`, ruolo `Bedrock-role`, ...) e il suffisso del tag `Name` (`aws-py-Bedrock`): con nomi diversi si possono avere più installazioni nello stesso account.

  Lo script crea, tutte con i tag standard del repository (`Name=aws-py-<progetto>`, `Project=Development.aws.py-Bedrock`, `ManagedBy=Sh`):
  - ✅ bucket S3 per i documenti, il backup dell'indice e il pacchetto del codice
  - ✅ parametro SSM SecureString con una chiave API casuale
  - ✅ policy IAM con i permessi minimi (dal template `policy.json`) e ruolo EC2, con in più `AmazonSSMManagedInstanceCore` per Session Manager
  - ✅ security group con la sola porta 80 (le regole aperte a tutti delle versioni precedenti vengono rimosse)
  - ✅ istanza EC2 `t3.small` Ubuntu 24.04 con IMDSv2 e disco gp3 da 20 GB, compresi disco e scheda di rete nei tag

  **Come arriva il codice sull'istanza**: niente `git clone`. Lo script impacchetta i file locali (`backend.py`, `requirements.txt`, `web/`) in `app/pocket-rag.tar.gz` sul bucket e mette nello user data un URL prefirmato valido un'ora, che l'istanza scarica con `curl`. Così si installa esattamente il codice che si ha in locale, anche senza averlo pubblicato su GitHub, e l'istanza non ha bisogno né di git né di permessi in più.

  Alla fine stampa l'indirizzo del sito, il comando per leggere la chiave API e quello per aprire una shell sull'istanza:
  ```bash
  aws ssm get-parameter --name /Bedrock/api-key --with-decryption --region eu-central-1 --query Parameter.Value --output text
  aws ssm start-session --target i-0123456789abcdef0 --region eu-central-1
  ```
  Lo user data impiega alcuni minuti a installare i pacchetti. Per seguirlo dalla shell dell'istanza:
  ```bash
  sudo tail -f /var/log/user-data.log
  sudo systemctl status pocket-rag
  sudo journalctl -u pocket-rag -f
  ```

  **Aggiornare il codice** dopo una modifica locale, senza ricreare l'istanza e senza SSH:
  ```bash
  ./bedrock_rag_stack.sh update Bedrock eu-central-1
  ```
  Lo script ricarica il pacchetto sul bucket e, con SSM Run Command, fa scaricare il nuovo codice all'istanza, aggiorna le dipendenze e riavvia il servizio; `.env`, indice e ambiente Python restano dove sono.

- Opzione 2: **Esecuzione in locale** (con le credenziali AWS del proprio profilo, i dati vanno comunque su S3 e Bedrock)
  ```bash
  python3 -m venv venv && source venv/bin/activate
  pip install -r requirements.txt
  cp .env.example .env        # impostare S3_BUCKET e API_KEY
  uvicorn backend:app --port 8000
  ```
  Il sito è su `http://localhost:8000`. Per l'OCR servono i pacchetti di sistema `tesseract-ocr`, `tesseract-ocr-ita` e `poppler-utils`; senza, le pagine PDF senza testo vengono saltate.

- **Cleanup**: rimozione di tutte le risorse
  ```bash
  ./bedrock_rag_stack.sh destroy Bedrock eu-central-1
  ```
  Il destroy cancella istanza, security group, bucket (documenti, backup e pacchetto del codice), parametro della chiave, ruolo, instance profile e policy. Per verificare che non sia rimasto nulla:
  ```bash
  aws ec2 describe-instances --filters "Name=tag:Project,Values=Development.aws.py-Bedrock" \
    --query "Reservations[].Instances[].{ID:InstanceId,State:State.Name}"
  aws s3 ls | grep bedrock-alnao-bucket
  aws iam list-roles --query "Roles[?contains(RoleName,'Bedrock')].RoleName"
  ```


## 🧪 API

Tutte le API sono sotto `/api`; tranne `health` e `supported-formats` richiedono l'header `X-API-Key`.

| Metodo | Percorso | Descrizione |
|--------|----------|-------------|
| GET | `/api/health` | stato del servizio |
| GET | `/api/supported-formats` | formati accettati |
| POST | `/api/ingest` | carica e indicizza un file (form: `file`, `doc_id` facoltativo) |
| POST | `/api/query` | domanda sui documenti: `{"question": "...", "k": 4}` |
| POST | `/api/generate` | domanda diretta al modello, senza documenti: `{"prompt": "..."}` |
| GET | `/api/documents` | documenti indicizzati |
| GET | `/api/documents/{doc_id}` | parti di un documento |
| DELETE | `/api/documents/{doc_id}` | fa dimenticare il documento (parti, embedding e file su S3) |
| POST | `/api/reindex` | ricostruisce l'indice da tutti i file su S3 |

```bash
KEY=$(aws ssm get-parameter --name /Bedrock/api-key --with-decryption --region eu-central-1 --query Parameter.Value --output text)
curl http://IP_PUBBLICO/api/health
curl -H "X-API-Key: $KEY" -F "file=@contratto.pdf" -F "doc_id=contratto-2026" http://IP_PUBBLICO/api/ingest
curl -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"question": "Qual è la durata del contratto?", "k": 4}' http://IP_PUBBLICO/api/query
curl -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"prompt": "Spiega il machine learning in parole semplici"}' http://IP_PUBBLICO/api/generate
curl -H "X-API-Key: $KEY" -X DELETE http://IP_PUBBLICO/api/documents/contratto-2026
```

Interfaccia web: `http://IP_PUBBLICO` per caricare documenti e fare domande, `http://IP_PUBBLICO/admin.html` per l'elenco dei documenti, le loro parti, il pulsante *dimentica* e la ricostruzione dell'indice. La chiave API si inserisce nel campo in alto a destra e resta salvata nel browser.


## 💰 Analisi dei Costi

Prezzi indicativi di Francoforte (`eu-central-1`) a ottobre 2026, IVA esclusa: verificare sempre sulle pagine dei prezzi AWS e di [Amazon Bedrock](https://aws.amazon.com/bedrock/pricing/). Per Amazon Nova Lite con il profilo EU la stima usa 0,08 $ per milione di token in input e 0,31 $ in output. **Titan Text Embeddings V2 costa 0,20 $ per milione di token**: prezzo verificato sul conto del 13 ottobre 2026 (1,35 milioni di token addebitati 0,27 $), dieci volte quello usato nelle prime versioni di questo README.

Scenario: istanza accesa 24 ore su 24; ogni giorno 5 documenti caricati (circa 100 parti), 2 immagini e 50 domande.

| Voce | Calcolo | Al giorno | Al mese (30 gg) |
|------|---------|-----------|-----------------|
| EC2 `t3.small` | 0,024 $/ora × 24 | 0,58 $ | 17,52 $ |
| Disco EBS gp3 20 GB | 0,0952 $/GB-mese | 0,06 $ | 1,90 $ |
| IPv4 pubblico | 0,005 $/ora × 24 | 0,12 $ | 3,65 $ |
| S3 (documenti e backup dell'indice, ~1 GB) | 0,0245 $/GB-mese + richieste | < 0,01 $ | 0,03 $ |
| SSM Parameter Store e Session Manager | parametro standard | 0 $ | 0 $ |
| Bedrock Titan Embeddings V2 | ~31.000 token/giorno × 0,20 $/milione | < 0,01 $ | 0,19 $ |
| Bedrock Nova Lite (risposte) | 50 domande × (~1.500 token in + ~300 out) | 0,01 $ | 0,32 $ |
| Bedrock Nova Lite (immagini) | 2 immagini × (~1.700 token in + ~500 out) | < 0,01 $ | 0,02 $ |
| Traffico in uscita | entro i 100 GB/mese gratuiti | 0 $ | 0 $ |
| **Totale** | | **~0,78 $** | **~23,62 $** |

Note sui costi:
- quasi tutto il costo è l'istanza accesa: fermandola quando non serve (`aws ec2 stop-instances`) si pagano solo il disco (~1,90 $/mese) e S3; l'IPv4 pubblico si paga solo mentre l'istanza è accesa
- con 1000 domande al giorno la parte Bedrock sale a circa 0,21 $/giorno (~6,40 $/mese), mentre l'istanza resta la stessa fino a quando regge il carico
- indicizzare costa circa 0,06 $ per milione di caratteri di testo (parti sovrapposte comprese): due documenti di qualche centinaio di pagine sono stati 1,35 milioni di token, cioè 0,27 $. La pagina stima il costo dal peso del file (per PDF e formati Office con un rapporto prudente tra testo e byte) e oltre 0,01 $ chiede conferma
- le immagini con Nova Lite costano circa 0,0003 $ l'una; con `IMAGE_MODEL` vuoto (solo OCR con Tesseract) la voce va a zero
- per cambiare modello si aggiornano sia `.env` sia `policy.json`, che autorizza solo i modelli usati
- la [versione serverless](../CDK/cdk33bedrockServerless/) con lo stesso scenario costa circa 0,08 $ al giorno (~2,35 $ al mese, con 42 brani per domanda invece di 4), perché non ha nulla acceso quando non si usa


## 🚀 Sviluppi Futuri
- 🔒 **HTTPS**: un certificato (Let's Encrypt con un dominio, oppure CloudFront davanti all'istanza) per non mandare la chiave API in chiaro
- 👥 **Utenti**: login con Amazon Cognito al posto della chiave unica, con documenti separati per utente
- 📊 **Monitoraggio**: metriche su CloudWatch (tempi di risposta, token consumati) e un allarme sul costo giornaliero di Bedrock
- 💬 **Conversazione**: memoria delle domande precedenti e risposte in streaming con `converse_stream`
- 🔄 **Reranking** dei risultati prima della generazione per migliorare le fonti scelte


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


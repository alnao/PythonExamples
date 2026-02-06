# IA RAD Annotazioni

Tutto in Python con due entrypoint (FastAPI e Flask) per ingestione e ricerca RAG, con UI web Flask per inserire annotazioni, fare ricerche e generare abstract sui chunk restituiti.
- ispirato al video [Come ho implemento l'AI in Typescript](https://www.youtube.com/watch?v=xDOUTqlnJuY)
- in futuro sarà evoluto per integratsi con il sistema [AlNao J-Annotazioni](https://github.com/alnao/JavaSpringBootExample) *coming soon*
- attenzione: usando un RAD locale, anche con piccoli modelli come il `codellama-7b-instruct.Q8_0`, risulta necessaria una grande quantità di risorse: usando Debian 13, CPU 12 CORE, servono 10Gb di ram e 10Gb di memoria swap (*non mi posso permettere una GPU con quello che costano!*)

## Creazione del progetto
Questo *progetto* è stato creato interamente usando l'IA GitHub copilot con i seguenti prompt
- Create a RAG in python using flask & fastapi into RAD_Annotazioni folder
    - read annotations from code or database or input
    - split annotation on chunks (example on break line or similar)
    - trasform every chunk in vectory with llamam model
    - save chanks and vetors on databases (different tabels with id unique)
    - use database DMBS with vector type and vestor searching system (SQLite+pgvector-like (Chroma/Faiss embedded)
    - service to search a word or input, trasform input into vestor and search similar vector into database
    - web-interface to create an annotation or upload annotations (in future automatic loading)
    - web-interface to insert input and check searching result
    - llama model on folder     model_path="/mnt/Virtuali/codellama-7b-instruct.Q8_0.gguf"
- with flask create an web-interface to create a single annotation and run search system using bootstrap5
- now I wanna create another Search, for example an new Serach input with prompt and engin have to trasform in vector and search vector into database, result table with result, create an new view
- on "Prompt Search" result, add an section where model analize every chank finded and write an abstract, in original language and an traduction in italian , when you run summary process, use only X chunks, X a parameter default 5, use chunks with more scores



## Architettura rapida
- Ingestion: testo suddiviso in chunk, vettorizzato via modello locale GGUF (llama.cpp) o OpenAI come fallback ibrido.
- Persistenza: ChromaDB in locale (SQLite) in `./data/vectordb` con metadati `annotation_id` e indice chunk.
- API/UI: [app_fastapi.py](app_fastapi.py) e [app_flask.py](app_flask.py); stessi endpoint `/annotations`, `/search`, `/health` più UI Flask (home e prompt search).
- Coda: hook asincroni per Kafka o SQS in [rag_annotations/queue_handlers/consumer.py](rag_annotations/queue_handlers/consumer.py). Non attivati di default.
- Core pipeline riusabile in [rag_annotations/pipeline.py](rag_annotations/pipeline.py).
- Prompt Search: pagina `/prompt-search` con selezione backend (local/openai/hybrid), scelta Top K, limite chunk da sintetizzare e tabella abstract (originale + traduzione italiana).

## Quickstart
1. Crea venv e installa: `pip install -r requirements.txt`
2. Configura `.env` (chiavi facoltative):
	```env
	RAG_LLM_BACKEND=local            # local | openai | hybrid
	RAG_MODEL_PATH=/mnt/Virtuali/codellama-7b-instruct.Q8_0.gguf
	RAG_OPENAI_API_KEY=sk-...
	RAG_KAFKA_BOOTSTRAP=localhost:9092
	RAG_KAFKA_TOPIC=annotations
	RAG_SQS_QUEUE_URL=...
	RAG_AWS_REGION=eu-west-1
	```
4. Avvia applicazione Flask: `python app_flask.py`
	- UI Home: inserisci annotazioni e fai search rapida.
	- UI Prompt Search: prompt→embedding con scelta backend, `top_k` e `summary_limit` (default 5) per generare abstract sui chunk migliori.

3. Alternativa avvia FastAPI: `uvicorn app_fastapi:app --reload --port 8000`
	- Prova ingest: `curl -X POST http://localhost:8000/annotations -H "Content-Type: application/json" -d '[{"text":"Prima annotazione"}]'`
	- Cerca: `curl "http://localhost:8000/search?query=annotazione"`

## Endpoints principali
- POST `/annotations`: lista di `{ "text": "...", "source": "opzionale" }`. Restituisce `ingested_chunks`.
- GET/POST `/search`: `query` e `top_k` (default 5). Restituisce chunk con punteggio di similarità.
- GET `/health`: semplice ping.

## UI Flask
- `/` Home: form per nuova annotazione e ricerca testuale semplice.
- `/prompt-search`: prompt semantico, selezione backend (local/openai/hybrid), `top_k`, `summary_limit` per generare abstract su chunk con score migliore; mostra chunk trovati e tabella abstract bilingue (originale + IT).

## Coda (bozza)
- Kafka: consumer asincrono con `aiokafka`, topic configurabile via `.env`. Vedi `build_consumer()` in [rag_annotations/queue_handlers/consumer.py](rag_annotations/queue_handlers/consumer.py).
- SQS: polling long-poll con batch delete. Richiede `RAG_SQS_QUEUE_URL` e `RAG_AWS_REGION`.

## Note
- Modello locale atteso in `RAG_MODEL_PATH` (default `/mnt/Virtuali/codellama-7b-instruct.Q8_0.gguf`).
    - Attenzione: usando un RAD locale, anche con piccoli modelli, risulta necessaria una grande quantità di risorse: usando Debian 13, CPU 12 CORE, servono 10Gb di ram e 10Gb di memoria swap (*non mi posso permettere una GPU con quello che costano!*)
    - feature rendere i modelli dinamici
- Database vettoriale locale su disco `data/vectordb`; cancellalo per reset.
    - aggiunto nel gitignore del progetto così non si versiona!
- Chunking configurabile con `RAG_CHUNK_SIZE` e `RAG_CHUNK_OVERLAP` in `.env`.
- Limite abstract: `summary_limit` controlla quanti chunk con score migliore vengono sintetizzati nella Prompt Search (default 5).





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


# BuildRAG: Applicazione RAG minimale con GUI Flask e Qwen

Questo progetto è un'applicazione minima basata su **Retrieval-Augmented Generation (RAG)** che utilizza un ecosistema interamente locale per interagire con i contenuti di un file PDF (`rules.pdf`). 
Fornisce un'elegante interfaccia grafica web in stile "ChatGPT" sviluppata in **Flask** direttamente in esecuzione dal file principale `app.py`.

> 💡 **Ispirazione & Origine**  
> Questo progetto prende profonda ispirazione dal tutorial HuggingFace e dal seguente video su YouTube:  
> [**Build a RAG app!** (https://www.youtube.com/watch?v=bPNmmDPyGzk)](https://www.youtube.com/watch?v=bPNmmDPyGzk)

## 🚀 Caratteristiche Principali
*   **Gestione PDF Locale:** Utilizza Langchain (`PyPDFLoader`) per estrarre e processare testi dal documento.
*   **Frammentazione Intelligente:** Tramite `RecursiveCharacterTextSplitter` il testo viene diviso in porzioni compatibili con i modelli.
*   **Vettorizzazione Veloce:** Usa `BAAI/bge-small-en-v1.5` combinato col motore di ricerca vettoriale `FAISS` (in-memory) per recuperare le informazioni rilevanti.
*   **LLM Ultra-leggero:** Generazione testi guidata dal modello Open Source ultraleggero e rapido `Qwen/Qwen2.5-0.5B-Instruct`.
*   **Interfaccia Web:** Integrazione in un singolo script `app.py` di un frontend in stile ChatGPT usando Flask e design responsivo.

---

## 🛠️ Installazione e Setup

1. **Creare un ambiente virtuale (opzionale ma consigliato):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Su Linux/Mac
   # .\.venv\Scripts\activate # Su Windows
   ```

2. **Installare le dipendenze richieste:**
   Il file `requirements.txt` contiene tutto il necessario (Langchain, Torch, Transformers, Flask, ecc.):
   ```bash
   pip install -r requirements.txt
   ```

3. **Struttura dei file necessari:**
   Assicurati che vi sia un documento chiamato `rules.pdf` nella root di questo progetto, per poter fornire il contesto alle domande. Eventualmente puoi inserire anche un `logo.png` per l'avatar del bot.

4. **Avviare l'Applicazione:**
   ```bash
   python app.py
   ```
   L'applicativo si avvierà in locale, solitamente su `http://127.0.0.1:5000/`.

---

## 📈 Come puoi migliorarlo (Next Steps)

Il progetto è volutamente semplice e "minimal". Una volta familiarizzato con il pipeline RAG attuale, puoi applicare diverse migliorie:

### 1. Migliorare l'Architettura del Software
*   **Separare le responsabilità:** Piuttosto che mantenere Frontend HTML e logica Python in un singolo file `app.py` di 200 righe, dividi i template in una cartella `templates/` e crea i servizi CSS/Immagini in `static/`.
*   **Streaming delle risposte:** Attualmente l'applicazione attende che l'LLM generi tutto il testo per rispondere. Implementando le *Server-Sent Events* nel backend Flask puoi fare in modo che il bot "digiti" in tempo reale.

### 2. Aumentare le Capacità del RAG
*   **Memoria di conversazione:** Usa la cronologia dei messaggi in LangChain (`ConversationBufferMemory`) in modo che il bot ricordi le domande precedenti e sia possibile effettuare "follow-up".
*   **Database Vettoriale Persistente:** Attualmente FAISS ricostruisce gli embeddings ad ogni riavvio. Passando ad un Vector DB su disco come **ChromaDB** o **Milvus**, eviterai l'attesa iniziale per la vettorizzazione dei documenti voluminosi.
*   **Supporto multi-formato e caricamento Web:** Implementa interfacce per elaborare e caricare documenti multipli (es. Word, web scraping o caricamento dinamico via drag & drop nella GUI). 

### 3. Modelli Meno Leggeri o API Esterne
*   **Upgrade dell'LLM:** Oltre `Qwen2.5-0.5B` esistono tantissimi modelli più capaci (come *Llama-3-8B-Instruct* o *Qwen 2.5-7B*). Se la tua VRAM lo permette, carica modelli più grandi per risposte più logiche ed approfondite. In alternativa puoi collegarti semplicemente all'API di OpenAI (`ChatOpenAI`) e risparmiare risorse locali.
*   **Migliorare l'Embedder:** Sperimentare con modelli per l'embedding multilingua se i tuoi PDF sono in italiano o lingue diverse dall'inglese (es. `intfloat/multilingual-e5-small`).


# IA
Questo esempio è stato creato con questi prompt
> all inside BuildRAG, never change others folders. Build a minimal RAG app from this guide:
        https://huggingface.co/learn/cookbook...
        PDF-only
        Extract and chunk roles.pdf text
        Use LangChain
        Use a very small Qwen Instruct
        Save pipeline as app.py . suggest which modules to install in rag_env to match the requirements of app.py .   

> LLMs answers must be short and concise. Design GUI for app.py.
        use Flask. use attached app layout image as inspiration. use logo.png.
        don't change the RAG pipeline itself - just add a GUI in app.py. RAD website like chatgpt look and feel.  


> mi scrivi un bel readme.md di questo progetto indicando che la sorgente è ispirata da "https://www.youtube.com/watch?v=bPNmmDPyGzk" e come posso migliorarlo  




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


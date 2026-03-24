# Guida: GraphRAG, GitHub Copilot e Ollama
Questo documento riassume le modalità di utilizzo del framework GraphRAG di Microsoft in combinazione con GitHub Copilot e la procedura per l'indicizzazione locale tramite Ollama.

This folder contains the examples code for **Retrieval Augmented Generation** from [ALucek Adam Łucek](https://github.com/ALucek/GraphRAG-Breakdown).
- [Knowledge Graph or Vector Database… Which is Better?](https://www.youtube.com/watch?v=6vG_amAshTk&list=PL31XFvSmiPKEMco1JXKtIBttlAOOxE8aO&index=2)


## Configurazione Local GraphRAG (Llama + Ollama)
Per trasformare un file .txt in un grafo di conoscenza senza usare API a pagamento, segui questa procedura.


Posizionare il file txt nella cartella `./part01_file02_test/input/`


Consigliato l'uso di un file in lingua inglese perchè la traduzione da italiano ad inglese potrebbe generare perdita di informazioni


**Requisiti**
- Server ollama installato e funzionante (vedere [AlNao Debian Handbook](https://github.com/alnao/alnao/blob/main/DEBIAN.md#Llama-e-Ollama) )
- Modelli scaricati: 
    - `ollama pull qwen2.5:7b` oppure `ollama pull llama3.2`
    - `ollama pull nomic-embed-text`
    - attenzione usare modelli più grandi potrebbe necessitare grandi quantità di spazio (llama 3.3 necessità di oltre 40Gb di spazio e più di 30Gb di RAM)
- Python 3.10+ con pacchetto graphrag installato.
    ```bash
    # Creazione ambiende python-venv
    python3 -m venv .venv  
    source .venv/bin/activate  
    # Installazione di graphrag
    pip install graphrag
    pip install pandas
    python3 -m pip install langchain-text-splitters
    ```
- Esecuzione di **graphrag**
    ```bash
    graphrag init --root ./part01_file02_test/input/
    python -m graphrag index --root ./part01_file02_test/
    ```
- Comandi Principali (con `python -m ` se necessario)
    - Inizializzazione:
        ```Bash
        graphrag init --root ./part01_file02_test/
        ```
    - Correzione del file `settings.yaml`: Per "ingannare" GraphRAG e fargli usare Ollama (che emula l'interfaccia OpenAI), modifica le sezioni LLM e Embedding come segue:
        ```YAML
        completion_models:
        default_completion_model:
            model_provider: openai
            model: qwen2.5:7b # or llama3.2
            auth_method: api_key 
            api_key: ollama # ${GRAPHRAG_API_KEY} 
            api_base: http://localhost:11434/v1
            retry:
            type: exponential_backoff

        embedding_models:
        default_embedding_model:
            model_provider: openai
            model: nomic-embed-text # ex text-embedding-3-large
            auth_method: api_key
            api_key: ollama # ${GRAPHRAG_API_KEY}
            api_base: http://localhost:11434/v1
            retry:
            type: exponential_backoff

        chunking:
            type: tokens
            size: 600 # ridurre il numero per velocizzare un po' il modello!
            overlap: 100
            encoding_model: o200k_base
        ```
    - Indicizzazione (Creazione del Grafo):
        ```Bash
        graphrag index --root ./part01_file02_test/
        ```
        - ⚠️🔶 Attenzione: l'esecuzione di questo comando potrebbe necessitare diverse ore di esecuzione su sistemi molto piccoli o con CPU/GPU limitate 🔶⚠️
    - Query (Interrogazione):
        ```Bash
        graphrag query --root ./part01_file02_test/ --method global "Quali sono i temi principali?"
        ```
        - *A me non funziona e non capisco il motivo!*
- Analisi del grafo con python dedicato, vedere ed eseguire il file
    ```bash
    python3 part01_file02_graph_generator.py 
    ```
- Il file `grafo_finale.html` visualizza il grafo generato dall'analisi della AI in formato "quasi" comprensibile!




## GraphRAG e GitHub Copilot
Attualmente, non esiste un'integrazione nativa "clicca e vai" tra i due strumenti, ma ci sono tre strade percorribili:
- Copilot Extensions: È possibile utilizzare le Copilot Extensions per creare un ponte. Funzionamento: Si può configurare un "Chat Participant" personalizzato che interroga il server GraphRAG e restituisce i risultati direttamente nella chat di VS Code tramite il comando @graphrag.
- Microsoft 365 vs GitHub Copilot
    - Microsoft 365 Copilot: Integra già algoritmi di tipo GraphRAG per analizzare le relazioni tra documenti, email e meeting aziendali. 
    - GitHub Copilot: Si basa principalmente su un RAG vettoriale standard. Per "istruirlo" su un grafo di codice, è necessario passare per estensioni di terze parti o caricare manualmente il contesto estratto dal grafo.
- Alternative Open Source: progetti come **code-graph-rag** permettono di mappare i repository. Questi possono essere collegati a Copilot o altri editor (come Cursor) tramite il protocollo MCP (Model Context Protocol).



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


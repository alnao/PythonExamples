# Nano Agent – Python Edition

Mini coding agent scritto in Python che utilizza **LiteLLM** come interfaccia unificata per interagire con diversi provider LLM. Riceve un prompt in linguaggio naturale, ragiona e invoca automaticamente dei tool (lettura, modifica, ricerca file) per portare a termine il compito richiesto.

Questo esempio è ispirato al *nano agent* di [ekolivero](https://github.com/ekolivero/nano-agent#).


## Provider supportati

| Provider | `LLM_PROVIDER` | Variabili richieste | Modello default |
|----------|-----------------|---------------------|-----------------|
| **Local GGUF** (llama.cpp / Ollama / LM Studio) | `local` | `LOCAL_BASE_URL`, `LOCAL_MODEL` | `local-model` |
| **OpenAI** | `openai` | `OPENAI_API_KEY`, `LLM_MODEL` | `gpt-4o` |
| **Anthropic** | `anthropic` | `ANTHROPIC_API_KEY`, `LLM_MODEL` | `claude-sonnet-4-20250514` |
| **Perplexity** | `perplexity` | `PERPLEXITY_API_KEY`, `LLM_MODEL` | `sonar-pro` |
| **GitHub Copilot** | `github_copilot` | nessuna (OAuth automatico) | `gpt-4` |



## Installazione

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Dipendenze

- `litellm>=1.40`
- `python-dotenv>=1.0`


## Configurazione

Copiare il file di esempio e personalizzare le variabili:

```bash
cp .env.example .env
```

Scegliere **uno** dei provider decommentando il blocco corrispondente nel file `.env`.

### Local GGUF

```env
LLM_PROVIDER=local
LOCAL_BASE_URL=http://localhost:8070/v1
LOCAL_MODEL=codellama
```

Avviare il server llama.cpp:

```bash
llama-server \
  -m /path/to/codellama-7b-instruct.Q8_0.gguf \
  --port 8070 -c 4096 -ngl 99
```

### OpenAI

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

### Anthropic

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-20250514
```

### Perplexity

```env
LLM_PROVIDER=perplexity
PERPLEXITY_API_KEY=pplx-...
LLM_MODEL=sonar-pro
```

### GitHub Copilot

```env
LLM_PROVIDER=github_copilot
LLM_MODEL=gpt-4
```

> Al primo avvio verrà richiesta l'autenticazione OAuth tramite https://github.com/login/device. È necessario un account GitHub con sottoscrizione Copilot attiva.

---

## Utilizzo

```bash
# Prompt semplice
python -m nano_agent "Trova tutti i file Python nella cartella"

# Verbose mode (mostra il ragionamento dell'agent)
python -m nano_agent -v "Leggi il file agent.py e spiegamelo"

# Modifica di file
python -m nano_agent -v "Nel file sum.py aggiungi una funzione che calcola la somma di tre numeri"
```

---

## Struttura del progetto

```
litellm_nano_agent/
├── .env.example           # Template variabili d'ambiente
├── .env                   # Configurazione locale (non versionato)
├── pyproject.toml         # Metadata del progetto
├── requirements.txt       # Dipendenze Python
└── nano_agent/
    ├── __init__.py
    ├── __main__.py        # Entry point: python -m nano_agent
    ├── main.py            # CLI (argparse) + routing dei provider
    ├── agent.py           # Agent loop con LiteLLM
    └── tools/
        ├── __init__.py    # Registry dei tool
        ├── create.py      # Tool: creazione di un file
        ├── read.py        # Tool: lettura file
        ├── edit.py        # Tool: modifica file
        ├── grep.py        # Tool: ricerca regex
        └── glob.py        # Tool: ricerca file per pattern
```


## Tool disponibili

L'agent può invocare autonomamente i seguenti tool durante l'esecuzione:

| Tool   | Descrizione |
|--------|-------------|
| `read` | Legge il contenuto di un file (con supporto per range di linee) |
| `edit` | Modifica un file sostituendo stringhe specifiche |
| `grep` | Cerca pattern regex ricorsivamente nei file |
| `glob` | Trova file che corrispondono a un pattern glob |



## Riferimenti

- [Documentazione LiteLLM](https://docs.litellm.ai/)
- [Provider GitHub Copilot](https://docs.litellm.ai/docs/providers/github_copilot)
- Questo esempio è ispirato al *nano agent* di [ekolivero](https://github.com/ekolivero/nano-agent#).




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


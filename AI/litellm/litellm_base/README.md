# LiteLLM Base - Chat Completion con GitHub Copilot

## Cos'è LiteLLM

LiteLLM è una libreria Python open-source che semplifica l'accesso a oltre 100 modelli di Large Language Models (LLM) tramite un'unica interfaccia compatibile con il formato OpenAI.

Funge da gateway unificato per provider come OpenAI, Anthropic, Google Gemini, AWS Bedrock e molti altri, normalizzando input, output ed errori. Puoi chiamare modelli diversi senza riscrivere il codice, passando semplicemente il nome del modello.

In questo esempio è usato GitHub-copilot ma può essere adattato a tutti i modelli supportati come descritto nella [documentazione LiteLLM](https://docs.litellm.ai/).

Questo esempio è vagamente ispirato al *nano agent* di [ekolivero](https://github.com/ekolivero/nano-agent#).



## Principali funzionalità

- **API unificata**: usa lo stesso formato per chat, embeddings, immagini e altro
- **Retry e fallback**: gestisce automaticamente ritentativi e switch tra provider in caso di errori
- **Proxy server**: per team, centralizza chiavi API, tracciamento costi e budget
- **Streaming e batching**: supporta risposte in tempo reale e richieste multiple

## Prerequisiti

- Python 3.x
- Un account GitHub con sottoscrizione **GitHub Copilot** attiva (Individual, Business o Enterprise)

## Come iniziare

1. Creare e attivare un ambiente virtuale:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Installare le dipendenze:

```bash
pip install -r requirements.txt
```

3. Eseguire lo script:

```bash
python3 chat-completion.py
```

## Autenticazione GitHub Copilot

Al primo avvio, LiteLLM richiede l'autenticazione tramite il flusso OAuth Device di GitHub:

```
Please visit https://github.com/login/device and enter code XXXX-XXXX to authenticate.
```

1. Aprire il link https://github.com/login/device nel browser
2. Inserire il codice mostrato nel terminale
3. Autorizzare l'applicazione entro 90 secondi

Una volta completata l'autenticazione, il token viene salvato in `~/.config/litellm/github_copilot/api-key.json` e riutilizzato automaticamente nelle esecuzioni successive.

> **Nota**: se appare l'errore *"Timed out waiting for user to authorize the device"*, significa che l'autorizzazione non è stata completata in tempo. Rieseguire lo script e completare il flusso più rapidamente.

## Struttura del progetto

| File | Descrizione |
|------|-------------|
| `chat-completion.py` | Script principale: invia un prompt a GPT-4 tramite GitHub Copilot |
| `requirements.txt` | Dipendenze Python (litellm) |

## Esempio di codice

```python
from litellm import completion

response = completion(
    model="github_copilot/gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful coding assistant"},
        {"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}
    ]
)
print(response)
```

## Riferimenti

- [Documentazione LiteLLM](https://docs.litellm.ai/)
- [Provider GitHub Copilot](https://docs.litellm.ai/docs/providers/github_copilot)




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


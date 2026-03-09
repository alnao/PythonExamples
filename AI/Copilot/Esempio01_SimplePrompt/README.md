# Copilot SDK - Esempio01 - Semplice prompt

Questo repository contiene un esempio pratico e commentato per iniziare a usare la **GitHub Copilot SDK** in Python. L'obiettivo è mostrare, nel modo più semplice possibile, come integrare le capacità di Copilot in un'applicazione Python: dalla selezione del modello, all'invio di prompt, fino all'uso di tool personalizzati.

---

## 📋 Prerequisiti

| Requisito | Note |
|---|---|
| Python 3.11+ | Necessario per `asyncio` moderno |
| GitHub Copilot CLI | Deve essere nel `PATH` — [scaricalo qui](https://github.com/github/copilot-sdk) |
| Abbonamento GitHub Copilot | Free, Pro, Business o Enterprise — oppure usa BYOK (vedi sotto) |
| Fine-Grained PAT | Token GitHub con permesso **Copilot Requests** abilitato |
---

## 🚀 Installazione

```bash
# 1. Installa la dipendenza
pip install github-copilot-sdk

# 2. Imposta il token di autenticazione
export COPILOT_GITHUB_TOKEN="github_pat_11XXXX..."
```

### Come ottenere il Fine-Grained PAT

1. Vai su **github.com** → foto profilo → **Settings**
2. **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
3. Clicca **Generate new token**
4. Nella sezione **Permissions** abilita **Copilot Requests** → Read
5. Clicca **Generate token** e copia il valore (visibile una volta sola!)

> ⚠️ I token classici (`ghp_...`) **non funzionano** con la SDK. Usa obbligatoriamente un Fine-Grained PAT (`github_pat_...`).

---

## ▶️ Esecuzione

```bash
python copilot_sdk_simple_prompt.py
```

Lo script avvia la chat semplice e chiede interattivamente:

1. **Il modello** da usare (menu a scelta numerica)
2. **Il tuo prompt** da inviare

```
╔══════════════════════════════════════════════════════╗
║     GitHub Copilot SDK — Esempi Python               ║
╚══════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────┐
│  Scegli il modello:                                 │
├─────────────────────────────────────────────────────┤
│  [1] OpenAI GPT-4.1          — general purpose, veloce      │
│  [2] OpenAI GPT-5.4          — più potente, più lento       │
│  [3] Anthropic Claude Sonnet 4.6 — ottimo per codice        │
│  [4] Google Gemini 3.1 Pro   — multimodale, Preview         │
└─────────────────────────────────────────────────────┘
Inserisci il numero del modello (default 1): 3
✅ Modello selezionato: claude-sonnet-4.6

💬 Inserisci il tuo prompt (invio per confermare):
👤 > Come funziona asyncio in Python?

🤖 Risposta da [claude-sonnet-4.6]:
    > 
```



## ⚠️ Note importanti sulla SDK

### `on_permission_request` è obbligatorio

La SDK, per sicurezza, richiede di dichiarare esplicitamente come gestire le richieste di permesso (esecuzione shell, accesso al filesystem, Git). Ogni `create_session` deve includere questo parametro:

```python
# Per sviluppo e test: approva tutto
session = await client.create_session({
    "model": "gpt-4.1",
    "on_permission_request": PermissionHandler.approve_all,
})
```

Per produzione è consigliabile usare un handler interattivo che chiede conferma all'utente per ogni operazione sensibile.

### La risposta è un `SessionEvent`, non una stringa

```python
response = await session.send_and_wait({"prompt": "..."})

# ❌ SBAGLIATO — AttributeError
print(response.text)

# ✅ CORRETTO
print(response.data.content)
```

### Modelli in Preview

GPT-5.4 e Gemini 3.1 Pro sono attualmente in anteprima su GitHub Copilot e potrebbero non essere disponibili su tutti i piani o consumare più crediti premium. In caso di errore, usa **GPT-4.1** che è il modello più stabile.

---

## 🔗 Risorse utili

- [GitHub Copilot SDK — repository ufficiale](https://github.com/github/copilot-sdk)
- [Documentazione GitHub Copilot](https://docs.github.com/en/copilot)
- [Fine-Grained Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Piani GitHub Copilot](https://github.com/features/copilot)




# &lt; AlNao /&gt;
Tutti i codici sorgente e le informazioni presenti in questo repository sono frutto di un attento e paziente lavoro di sviluppo da parte di AlNao, che si è impegnato a verificarne la correttezza nella massima misura possibile. Qualora parte del codice o dei contenuti sia stato tratto da fonti esterne, la relativa provenienza viene sempre citata, nel rispetto della trasparenza e della proprietà intellettuale. 


Alcuni contenuti e porzioni di codice presenti in questo repository sono stati realizzati anche grazie al supporto di strumenti di intelligenza artificiale, il cui contributo ha permesso di arricchire e velocizzare la produzione del materiale. Ogni informazione e frammento di codice è stato comunque attentamente verificato e validato, con l’obiettivo di garantire la massima qualità e affidabilità dei contenuti offerti. 


Per ulteriori dettagli, approfondimenti o richieste di chiarimento, si invita a consultare il sito [AlNao.it](https://www.alnao.it/).


## AI
Questo script è stato creato grazie all'aiuto di AI al quale sono stati inseriti questi prompt
- ciao, mi scrivi un bel esempio in python che usa SDK di "GitHub Copilot"
- ma mi dici cosa intendi per "Autenticati con GitHub Copilot"?
- ValueError: An on_permission_request handler is required when creating a session. For example, to allow all permissions, use {"on_permission_request": PermissionHandler.approve_all}.
- dove trovo il il_tuo_fine_grained_token ?
- File "/mnt/Dati4/Workspace/PythonExamples/AI/Copilot/Example01_SimpleCopilot.py", line 80, in demo_chat_semplice print(risposta.text if risposta else "(nessuna risposta)") AttributeError: 'SessionEvent' object has no attribute 'text'
- modifica la demo_chat_semplice perchè voglio che l'utente inserisca il prompt e voglio che scelta il modello tra quelli disponibili, per ora metti "GPT4.1", "GPT5.4", sonnet 4.6, gemini 3.1 pro
- così funziona ora mi scrivi un bel README.md , ipotizzando di spiegare che questo è un primo semplice esempio di uso della SDK di GitHub Copilot ?




## License
Made with ❤️ by <a href="https://www.alnao.it">AlNao</a>
&bull; 
Public projects 
<a href="https://www.gnu.org/licenses/gpl-3.0"  valign="middle"> <img src="https://img.shields.io/badge/License-GPL%20v3-blue?style=plastic" alt="GPL v3" valign="middle" /></a>
*Free Software!*


Il software è distribuito secondo i termini della GNU General Public License v3.0. L'uso, la modifica e la ridistribuzione sono consentiti, a condizione che ogni copia o lavoro derivato sia rilasciato con la stessa licenza. Il contenuto è fornito "così com'è", senza alcuna garanzia, esplicita o implicita.


The software is distributed under the terms of the GNU General Public License v3.0. Use, modification, and redistribution are permitted, provided that any copy or derivative work is released under the same license. The content is provided "as is", without any warranty, express or implied.


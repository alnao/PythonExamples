# Esempio 14 CeleryWorkerRedis

Esempio di architettura `web + worker + broker` con Flask, Celery e Redis in Docker Compose.

## Servizi

- `redis`: broker e backend di Celery.
- `web`: applicazione Flask che accoda job asincroni.
- `worker`: worker Celery che esegue i job.

## Avvio con Docker Compose

```bash
cd Docker/14CeleryWorkerRedis
docker compose up --build
```

L'app Flask sarà disponibile su `http://127.0.0.1:5001`.

## Esempi di chiamate

1. **Verifica che l'app sia su**

```bash
curl http://127.0.0.1:5001/
```

2. **Accoda un job**

```bash
curl -X POST http://127.0.0.1:5001/enqueue -H "Content-Type: application/json" -d '{"duration": 10}'
```

Risposta di esempio:

```json
{"task_id": "c0e3d8..."}
```

3. **Controlla lo stato/risultato**

```bash
curl http://127.0.0.1:5001/result/<task_id>
```






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


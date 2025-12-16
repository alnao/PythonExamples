# Esempio 11 IA Llama Raspberry3 

Esempio di progetto con motore Llama che viene seguito in una immagine docker, il modello è TinyLlama ma nel file di download ci sono altri modelli. 


Per altri modelli: 
- Visita: https://huggingface.co/models
- Seleziona il motore **Llama**
- Vedrai una lista di modelli. Entrando nel dettaglio nella vista files c'è la possibilà di scaricare il formato GGUF.
  - Esempio: tinyllama-1.1b-chat-v1.0.Q4_0.gguf
  - Esempio in italiano: https://huggingface.co/lucaferranti/tinyllama-it-GGUF


## Comandi
- Cleanup
  ```bash
  docker stop tinyllama-container 2>/dev/null || true
  docker rm tinyllama-container 2>/dev/null || true
  docker rmi tinyllama-pi 2>/dev/null || true
  ```
- Build con verbose
  ```bash
  docker build -t tinyllama-pi . --progress=plain
  ```
- Avvio immagine
  ```bash
  docker run --name tinyllama-container -p 8080:8080 -p 5000:5000 tinyllama-pi
  ```
  oppure se già avviato in precedenza
  ```bash
  docker start tinyllama-container
  ```
- Apri nel browser per accedere al frontend:
  ```
  http://localhost:5000  
  ```
- Monitoraggio
  ```bash
  docker logs -f tinyllama-container
  ```
- Test health check
  ```bash
  curl http://localhost:5000/api/health
  ```
- Test completamento tramite proxy Flask
  ```bash
  curl -X POST http://localhost:5000/api/completion \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Ciao, come stai?", "n_predict": 50}'
  ```
- Test diretto dell'API llama.cpp
  ```bash
  curl -X POST http://localhost:8080/completion \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Scrivi una breve storia", "n_predict": 100}'

  curl -X POST http://localhost:8080/completion -H "Content-Type: application/json" -d '{"prompt": "Scrivi una introduzione o una prefazione di un libro che parla di AWS CloudFormation", "n_predict": 500, "stream": true}'

  curl -X POST http://localhost:8080/completion -H "Content-Type: application/json" -d '{"prompt": "Scrivi una introduzione o una prefazione di un libro che parla di AWS CloudFormation", "n_predict": 500}'

  ```
- Test con parametri avanzati:
  ```bash
  curl -X POST http://localhost:8080/completion \
    -H "Content-Type: application/json" \
    -d '{
      "prompt": "Dimmi una curiosità scientifica",
      "n_predict": 80,
      "temperature": 0.7,
      "top_k": 40,
      "top_p": 0.9
    }'
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


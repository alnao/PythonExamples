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
  ```
  docker stop tinyllama-container 2>/dev/null || true
  docker rm tinyllama-container 2>/dev/null || true
  docker rmi tinyllama-pi 2>/dev/null || true
  ```
- Build con verbose
  ```
  docker build -t tinyllama-pi . --progress=plain
  ```
- Avvio immagine
  ```
  docker run --name tinyllama-container -p 8080:8080 -p 5000:5000 tinyllama-pi
  ```
  oppure se già avviato in precedenza
  ```
  docker start tinyllama-container
  ```
- Apri nel browser per accedere al frontend:
  ```
  http://localhost:5000  
  ```
- Monitoraggio
  ```
  docker logs -f tinyllama-container
  ```
- Test health check
  ```
  curl http://localhost:5000/api/health
  ```
- Test completamento tramite proxy Flask
  ```
  curl -X POST http://localhost:5000/api/completion \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Ciao, come stai?", "n_predict": 50}'
  ```
- Test diretto dell'API llama.cpp
  ```
  curl -X POST http://localhost:8080/completion \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Scrivi una breve storia", "n_predict": 100}'

  curl -X POST http://localhost:8080/completion -H "Content-Type: application/json" -d '{"prompt": "Scrivi una introduzione o una prefazione di un libro che parla di AWS CloudFormation", "n_predict": 500, "stream": true}'

  curl -X POST http://localhost:8080/completion -H "Content-Type: application/json" -d '{"prompt": "Scrivi una introduzione o una prefazione di un libro che parla di AWS CloudFormation", "n_predict": 500}'

  ```
- Test con parametri avanzati:
  ```
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



# AlNao.it
Nessun contenuto in questo repository è stato creato con IA o automaticamente, tutto il codice è stato scritto con molta pazienza da Alberto Nao. Se il codice è stato preso da altri siti/progetti è sempre indicata la fonte. Per maggior informazioni visitare il sito [AlNao.it](https://www.alnao.it/).

## License
Public projects 
<a href="https://it.wikipedia.org/wiki/GNU_General_Public_License"  valign="middle"><img src="https://img.shields.io/badge/License-GNU-blue" style="height:22px;"  valign="middle"></a> 
*Free Software!*




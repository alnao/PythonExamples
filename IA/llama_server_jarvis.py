"""
# llama_server_jarvis.py — Client per server Llama/llama.cpp

Breve descrizione
- Script Python per inviare prompt a un server Llama (es. `llama-server`/`llama.cpp`) in esecuzione localmente e per avviare una sessione interattiva.
- Supporta richieste normali e streaming, gestione di timeout e una semplice cronologia locale dei prompt/risposte.

Prerequisiti
- Python 3.x
- requests
  - Installazione: 
    - `apt-get install python3-requests` su sistemi Debian-based     
    - `pip install requests --break-system-packages` alternativa su altri sistemi
- Server Llama in esecuzione (es. `/mnt/Virtuali/llama.cpp/build/bin/llama-server`) che espone l'endpoint OpenAI-like (default `http://127.0.0.1:8085`).

Installazione rapida (esempio Debian)
```bash
# build llama.cpp (solo se necessario)
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build && cd build
cmake ..
cmake --build . --config Release
./bin/llama-server -m /mnt/Virtuali/codellama-7b-instruct.Q8_0.gguf --port 8090
```

Andare con un browser su
```
localhost:8090
```

Uso dello script
- Invio di un singolo prompt:
    ```bash
    python3 llama_server_jarvis.py --prompt "Ciao, mi crei una funzione AWS Lambda per scrivere in una tabella dynamo e dimmi i passaggi che devo fare?" --max-tokens 150 --temperature 0.5
    ```
- Modalità interattiva (default):
    ```bash
    python3 llama_server_jarvis.py
    ```
- Modalità interattiva con curl
    ```
    curl -X POST http://127.0.0.1:8090/v1/completions -H "Content-Type: application/json" -d '{"model": "llama","prompt": "ciao","max_tokens": 10  }'
    curl -X POST http://127.0.0.1:8090/v1/completions -H "Content-Type: application/json" -d '{"model": "llama","prompt": "Ciao, where id Padova?","max_tokens": 50  }'
    curl -X POST http://127.0.0.1:8090/v1/completions -H "Content-Type: application/json" -d '{"model": "llama","prompt": "Write to me a aws lambda function to save a record into dynamo table" ,"max_tokens": 350  }'
    ```

- Parametri utili:
  - `--api-url` (default `http://127.0.0.1:8090/v1/completions`)
  - `--max-tokens` (default `512`)
  - `--temperature` (default `0.7`)
  - `--stream` (flag per abilitare lo streaming)

Esempi curl verso `llama-server`
```bash
curl -X POST http://127.0.0.1:8090/v1/completions \
 -H "Content-Type: application/json" \
 -d '{"model":"mistral","prompt":"Ciao","max_tokens":50}'
```

Comportamento principale dello script
- send_prompt(): invia il prompt, gestisce streaming e non-streaming, stampa tempi e errori.
- interactive_mode(): ciclo REPL con cronologia locale (salvata in memoria durante l'esecuzione).
- main(): parsing argomenti, verifica raggiungibilità del server e invoca modalità interattiva o singolo prompt.

Note e consigli
- L'endpoint API e il formato della risposta dipendono dalla versione di `llama-server`/API in uso; adattare parsing se la struttura JSON è differente.
- Per streaming il server deve inviare eventi in formato SSE; in caso diverso lo streaming va adattato.
- Controllare risorse RAM/Swap prima di caricare modelli grandi (es. Llama 70B).
- Se il server non è raggiungibile, lo script chiede conferma prima di continuare.

Licenza / Riferimenti
- I comandi per scaricare modelli e link utili sono presenti nel file sorgente (es. Hugging Face, llama.cpp).
- questo esempio è vagamente ispirato a Jarvis dal video https://www.youtube.com/watch?v=gASkikWINOM
"""

#!/usr/bin/env python3
import requests
import json
import time
import argparse
import sys

SERVER_DEFAULT_URL = "http://127.0.0.1:8090/v1/completions"

def send_prompt(prompt, api_url=SERVER_DEFAULT_URL, max_tokens=512, 
                temperature=0.7, stop=None, stream=False):
    """
    Invia un prompt al server Llama locale e restituisce la risposta.
    
    Args:
        prompt: Il testo di input da inviare al modello
        api_url: URL dell'API del server Llama
        max_tokens: Numero massimo di token da generare
        temperature: Temperatura per il campionamento (più alta = più casuale)
        stop: Sequenze di stop che interrompono la generazione
        stream: Se True, la risposta viene restituita in streaming
    
    Returns:
        Il testo generato dal modello
    """
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mistral",  # Questo è solo un nome simbolico, il server usa il modello caricato
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream
    }
    
    if stop:
        data["stop"] = stop
    
    try:
        print("\nInvio richiesta al server Llama...")
        start_time = time.time()
        
        if stream:
            response = requests.post(api_url, headers=headers, json=data, stream=True)
            response.raise_for_status()
            
            collected_chunks = []
            print("\nRisposta:\n")
            for line in response.iter_lines():
                if line:
                    # Le righe iniziano con "data: "
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        data_str = line[6:]  # Rimuovi "data: "
                        try:
                            chunk = json.loads(data_str)
                            text_chunk = chunk['choices'][0]['text']
                            collected_chunks.append(text_chunk)
                            print(text_chunk, end="", flush=True)
                        except json.JSONDecodeError:
                            print(f"Errore nel decodificare: {data_str}")
            
            print("\n")
            result = "".join(collected_chunks).strip()
        else:
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()["choices"][0]["text"].strip()
            print("\nRisposta:\n")
            print(result)
        
        end_time = time.time()
        print(f"\nTempo di risposta: {end_time - start_time:.2f} secondi")
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"\nErrore nella comunicazione con il server: {e}")
        return None
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"\nErrore nell'elaborazione della risposta: {e}")
        if 'response' in locals():
            print(f"Stato HTTP: {response.status_code}")
            print(f"Risposta: {response.text}")
        return None

def interactive_mode(api_url, max_tokens, temperature, stream):
    """Avvia una sessione interattiva con il modello."""
    print("\n=== Modalità Interattiva con Llama ===")
    print("Digita 'exit' o 'quit' per uscire.")
    print("Premi Ctrl+C per interrompere in qualsiasi momento.")
    
    history = []
    
    try:
        while True:
            prompt = input("\nPrompt: ")
            if prompt.lower() in ["exit", "quit"]:
                print("Uscita dal programma.")
                break
            
            if not prompt.strip():
                continue
            
            # Opzionale: mantieni una cronologia dei prompt e delle risposte
            history.append({"prompt": prompt})
            
            response = send_prompt(
                prompt=prompt,
                api_url=api_url,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream
            )
            
            if response:
                history[-1]["response"] = response
                
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente. Uscita dal programma.")
    
    return history

def main():
    parser = argparse.ArgumentParser(description="Client per interagire con un server Llama locale")
    parser.add_argument("--api-url", default=SERVER_DEFAULT_URL,
                        help=f"URL dell'API del server Llama (default: {SERVER_DEFAULT_URL})")
    parser.add_argument("--max-tokens", type=int, default=512,
                        help="Numero massimo di token da generare (default: 512)")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="Temperatura per il campionamento (default: 0.7)")
    parser.add_argument("--prompt", help="Prompt da inviare (se non specificato, avvia la modalità interattiva)")
    parser.add_argument("--stream", action="store_true", help="Usa lo streaming per le risposte")
    
    args = parser.parse_args()
    
    # Controllo se il server è raggiungibile
    try:
        requests.get(args.api_url.replace("/completions", ""))
        print(f"Server disponibile all'indirizzo {args.api_url}")
    except requests.exceptions.RequestException:
        print(f"Impossibile connettersi al server all'indirizzo {args.api_url}")
        choice = input("Vuoi continuare comunque? (s/n): ")
        if choice.lower() != 's':
            sys.exit(1)
    
    if args.prompt:
        send_prompt(
            prompt=args.prompt,
            api_url=args.api_url,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            stream=args.stream
        )
    else:
        interactive_mode(
            api_url=args.api_url,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            stream=args.stream
        )

if __name__ == "__main__":
    main()
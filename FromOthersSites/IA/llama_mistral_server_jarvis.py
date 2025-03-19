# questo esempio è vagamente ispirato a Jarvis dal video https://www.youtube.com/watch?v=gASkikWINOM

"""
apt install -y build-essential cmake git python3 python3-pip
apt install -y libopenblas-dev
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release
cd ..
mkdir -p models
cd models
wget https://huggingface.co/TheBloke/Llama-2-7B-GGUF/resolve/main/llama-2-7b.Q4_K_M.gguf
/mnt/Virtuali/llama.cpp/build/bin/llama-simple -m /mnt/Virtuali/llama-2-7b.Q4_K_M.gguf

# wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q2_K.gguf
    questo scaricherà il modello Mistral 7B Instruct v0.2 con quantizzazione Q2_K dal repository di TheBloke su Hugging Face. Questa versione è molto compressa (circa 2.83GB) ed è ottimizzata per l'esecuzione su CPU con risorse limitate.
/mnt/Virtuali/llama.cpp/build/bin/llama-server -m /mnt/Virtuali/llama-2-7b.Q4_K_M.gguf --host 127.0.0.1 --port 8085 --n-gpu-layers 0
ps aux | grep llama-server
top -c -p $(pgrep llama-server)
htop -p $(pgrep llama-server)
NO /mnt/Virtuali/llama.cpp/build/bin/llama-server -m /mnt/Virtuali/llama-2-7b.Q4_K_M.gguf --host 127.0.0.1 --port 8085 --ctx-size 1024 --threads 4 --n-predict 256 --n-gpu-layers 0
/mnt/Virtuali/llama.cpp/build/bin/llama-server -m /mnt/Virtuali/mistral-7b-instruct-v0.2.Q2_K.gguf --host 127.0.0.1 --port 8085 --ctx-size 1024 --threads 4 --n-predict 256 --n-gpu-layers 0
> http://127.0.0.1:8085/


pip install shell-gpt --break-system-packages
sgpt --api-url http://127.0.0.1:8080/v1 --api-key "non-necessaria" config
nano ~/.config/shell_gpt/.sgptrc 
    OPENAI_API_KEY=your_api_key
    API_BASE_URL=http://localhost:8085/v1
    DEFAULT_MODEL=llama3.2:latest

curl -X POST http://127.0.0.1:8085/v1/completions -H "Content-Type: application/json" -d '{"model": "llama","prompt": "ciao","max_tokens": 10  }'

curl -X POST http://127.0.0.1:8085/v1/completions -H "Content-Type: application/json" -d '{"model": "llama","prompt": "Ciao, where id Padova?","max_tokens": 50  }'

sgpt "where is Padova?"
    

"""

#!/usr/bin/env python3
import requests
import json
import time
import argparse
import sys

def send_prompt(prompt, api_url="http://127.0.0.1:8085/v1/completions", max_tokens=512, 
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
    parser.add_argument("--api-url", default="http://127.0.0.1:8085/v1/completions",
                        help="URL dell'API del server Llama (default: http://127.0.0.1:8085/v1/completions)")
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
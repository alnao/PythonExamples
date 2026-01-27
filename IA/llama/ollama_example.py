"""
Ollama è un tool/server per eseguire modelli LLM localmente sul tuo computer:
- Cosa è: Un'applicazione che fa girare modelli LLM in locale
- Funzione: Gestisce il caricamento, l'ottimizzazione e l'esecuzione dei modelli
- Compatibilità: Supporta Llama, Mistral, Phi, Gemma e molti altri modelli
- API: Fornisce un'interfaccia HTTP REST per interagire con i modelli
- Piattaforme: macOS, Linux, Windows
- Analogia: Ollama è come il "sistema operativo" che fa funzionare il cervello

Llama è una famiglia di modelli LLM (Large Language Models) creati da Meta (Facebook):
- Cosa è: È il modello di intelligenza artificiale vero e proprio
- Versioni: Llama 1, Llama 2, Llama 3, Llama 3.1, Llama 3.2, Llama 3.3
- Varianti: Disponibili in diverse dimensioni (7B, 13B, 70B, 405B parametri)
- Formato: File di pesi del modello (.pth, .safetensors, .gguf)
- Licenza: Open source (con alcune restrizioni commerciali)
- Llama Models:
    ├── Llama 3.3 70B  (più recente, molto potente)
    ├── Llama 3.1 8B   (veloce, leggero)
    ├── Llama 2 13B    (versione precedente)
    └── Code Llama     (specializzato per codice)

Installazione su debian 13
- note: this file sould NOT be named llama.py because of conflict with llama_cpp package
- python3-ollama oppure pip install llama-cpp-python --break-system-packages
- curl -fsSL https://ollama.com/install.sh | sh
    https://ollama.com/download
- ollama --help

Uso di ollama con modelli Llama
- scarica il modello Llama 3.3 (42GB) o Llama    
    - ollama pull llama3.3
        ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE 
        il comando ollama pull llama3.3 scarica il modello Llama 3.3 che occupa circa 42GB di spazio su disco.
            Assicurati di avere spazio sufficiente sul tuo disco prima di eseguire questo comando
        ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE 
        Il modello per partire ha bisogno di almeno 40Gb di RAM/SWAP disponibili altrimenti si ottiene l'errore:
            ollama._types.ResponseError: model requires more system memory (40.3 GiB) than is available (23.6 GiB) (status code: 500)
        ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE ATTENZIONE 
    - ollama run llama3.3
    - ollama rm llama3.3
- scarica il modello Llama 3.2 3B (2GB)    
    - ollama pull llama3.2:3b
        ATTENZIONE : questo modello richiede 2Gb di disco e "solo" tra i 2Gb e i 2Gb/8Gb per eseguire il modello
    - ollama list
    - ollama run llama3.2:3b
    - ollama rm llama3.2:3b
- scarica il modello Code Llama (13GB)
    - ollama pull codellama
        ATTENZIONE : questo modello richiede circa 4Gb di disco e "solo" tra i 2Gb e i 8Gb per eseguire il modello
    - ollama run codellama  

"""

import ollama

def chat_loop(model='codellama'):
    messages = []
    print("Chat avviata. Scrivi 'exit' per uscire.\n")
    while True:
        user_input = input("Tu: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        messages.append({"role": "user", "content": user_input})

        response = ollama.chat(
            model=model,
            messages=messages
        )

        assistant_msg = response["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_msg})

        print(f"AI: {assistant_msg}\n")

if __name__ == "__main__":
    chat_loop(model="codellama")  # oppure "llama3.2:3b", "llama3.3"


"""
# vecchia versione con un solo prompt fisso
def process_file_local(input_file, output_file):
    # Leggi file
    #with open(input_file, 'r') as f:
    #    content = f.read()
    
    # Processa con modello locale
    response = ollama.chat(
        model='codellama', #oppure llama3.2:3b oppure llama3.3
        messages=[{
            'role': 'user',
            #'content': f'Migliora questo codice:\n{content}'
            #'content': f'Parlami di Venezia'
            'content': f'Scrivi una classe python di un gioco a scelte multiple tipo librogame'
        }]
    )
    
    # Scrivi risultato
    with open(output_file, 'w') as f:
        f.write(response['message']['content'])
if __name__ == "__main__": 
    process_file_local("", "output_llama_cpp.txt")
"""
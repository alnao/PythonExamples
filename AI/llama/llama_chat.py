"""
# Chat LLM locale con llama-cpp-python

Script Python per avviare una chat locale con modelli GGUF (es. Mistral/CodeLlama) usando `llama-cpp-python`, con:
- prompt di sistema
- memoria del contesto (turni limitati)
- streaming della risposta
- stop tokens per interrompere correttamente
- libramente ispirato al video "PYTHON E LLM - GUIDA INTRODUTTIVA COMPLETA 2024" https://www.youtube.com/watch?v=m-Kl3F_tUTU

Requisiti
- Python 3.x
- `llama-cpp-python`

Installazione su Debian 13:
```bash
pip install llama-cpp-python --break-system-packages
```
Modelli (GGUF) Esempi (da Hugging Face, TheBloke): Scarica un modello GGUF e imposta il percorso in model_path.
- mistral-7b-instruct-v0.2.Q2_K.gguf
    - https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/tree/main
    - wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q2_K.gguf
    - Scaricherà il modello Mistral 7B Instruct v0.2 con quantizzazione Q2_K dal repository di TheBloke su Hugging Face. Questa versione è molto compressa (circa 2.83GB) ed è ottimizzata per l'esecuzione su CPU con risorse limitate.
- codellama-7b-instruct.Q8_0.gguf
    - https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/tree/main
    - wget https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q8_0.gguf
    - CodeLlama-7b (Base): È un modello di completamento. Se gli dai un pezzo di codice, lui prova a scriverne il seguito. Non sa chattare. Se provi a parlarci, lui "allucina", ripete le tue frasi o genera testo senza senso (i "discorsi strani" e il loop di cui parli) perché non capisce il concetto di "Domanda -> Risposta".
    - CodeLlama-7b-Instruct: È la versione addestrata specificamente per seguire istruzioni e chattare. Soluzione: Devi scaricare la versione Instruct. Cerca su HuggingFace il file che contiene "instruct" nel nome, ad esempio: codellama-7b-instruct.Q8_0.gguf.

Referenze
- huggingface https://huggingface.co/models
- documentation https://github.com/abetlen/llama-cpp-python/pkgs/container/llama-cpp-python
- examples https://llama-cpp-python.readthedocs.io/en/latest/


Note:
- Usare modelli Instruct per una chat coerente. Se il modello è “base”, le risposte possono essere incoerenti.
- Adegua n_ctx e max_turns alle risorse della macchina.

"""
import os
from llama_cpp import Llama

MAX_TURNS=20
N_CTX=2048

def start_chat_llm(
    model_path,
    chat_format="llama-2",
    system_prompt="Sei un assistente utile e conciso.",
    max_turns=MAX_TURNS,
):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    llm = Llama(
        model_path=model_path,
        verbose=False,
        n_ctx=N_CTX,
        chat_format=chat_format,
    )
    #llm = LlamaCpp(model_path=model_path,temperature=1,max_tokens=20000,top_p=1,verbose=True)  # Verbose is required to pass to the callback manager
    chat_history = [{"role": "system", "content": system_prompt}]
    while True:
        user_query = input(">>> ").strip()
        if not user_query:
            continue
        if user_query.lower() in {"exit", "quit"}:
            break

        chat_history.append({"role": "user", "content": user_query})
        # Keep last N turns (each turn = user+assistant). System stays at index 0.
        if max_turns and len(chat_history) > 1 + (max_turns * 2):
            chat_history = [chat_history[0]] + chat_history[-(max_turns * 2):]

        stream = llm.create_chat_completion(
            messages=chat_history,
            stream=True,
            temperature=0.7,
            stop=["</s>", "<|eot_id|>", "<|end_of_text|>"]
        )
        lm_response = ""
        for piece in stream:
            if "content" in piece["choices"][0]["delta"].keys():
                response_piece = piece["choices"][0]["delta"]["content"]
                lm_response += response_piece
                print(response_piece, end="", flush=False) #Mettere True per vedere in tempo reale
            if piece["choices"][0]["finish_reason"] is not None:
                break
        print()  # Add a newline after the assistant's response
        chat_history.append({"role": "assistant", "content": lm_response})

if __name__ == "__main__":
    #model_path="/mnt/Virtuali/mistral-7b-instruct-v0.2.Q2_K.gguf" # mistral-7b-instruct-v0.2.Q2_K.gguf
    #model_path="/mnt/Virtuali/llama-2-7b.Q4_K_M.gguf"
    model_path="/mnt/Virtuali/codellama-7b-instruct.Q8_0.gguf"
    start_chat_llm(
        model_path,
        chat_format="llama-2",
        system_prompt="Sei un assistente che risponde in modo chiaro e breve.",
        max_turns=MAX_TURNS,
    )



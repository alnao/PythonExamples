# see https://www.youtube.com/watch?v=m-Kl3F_tUTU
# pip install llama-cpp-python --break-system-package
# search and download mistral-7b-instruct-v0.2.q2_k.gguf from https://huggingface.co/models
    # https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/tree/main
    # https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q2_K.gguf

# wget https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q2_K.gguf
#    questo scaricherà il modello Mistral 7B Instruct v0.2 con quantizzazione Q2_K dal repository di TheBloke su Hugging Face. Questa versione è molto compressa (circa 2.83GB) ed è ottimizzata per l'esecuzione su CPU con risorse limitate.


from llama_cpp import Llama
#see documentation https://github.com/abetlen/llama-cpp-python/pkgs/container/llama-cpp-python
#see example https://llama-cpp-python.readthedocs.io/en/latest/

def start_chat_llm(model_path):
    llm = Llama (model_path=model_path, verbose=True , n_ctx=2048)#, verbose=True, n_ctx=2048000)
    #llm = LlamaCpp(model_path=model_path,temperature=1,max_tokens=20000,top_p=1,verbose=True)  # Verbose is required to pass to the callback manager
    chat_history=[]
    while True:
        user_query= input(">>> ")
        print()
        chat_history.append({"role":"user","content":user_query})
        stream = llm.create_chat_completion(messages=chat_history, stream=True, temperature=1.0)
        lm_response = ""
        for piece in stream:
            if "content" in piece["choices"][0]["delta"].keys():
                response_piece=piece["choices"][0]["delta"]["content"]
                lm_response += response_piece
                print (response_piece, end="",flush=True)
        chat_history.append( {"role":"assistant","content":lm_response})

if __name__ == "__main__":
    model_path="/mnt/Virtuali/mistral-7b-instruct-v0.2.Q2_K.gguf" # mistral-7b-instruct-v0.2.Q2_K.gguf
    start_chat_llm(model_path)

#how write a AWS lambda to connect to RDS database
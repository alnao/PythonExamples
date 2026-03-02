from transformers import pipeline

#see https://www.youtube.com/watch?v=YWUvD6qe56g
# docker build -t qwenchatbot .
# docker run -it --gpus=all qwenchatbot
# docker run -it qwenchatbot


import torch

from sty import fg

def ask_question(pipe, question ,first_time):
    res=pipe(question,max_new_tokens=128)
    print(res)
    res=res[0]['generated_text'] # [-1]["content"]
    if not first_time:
        res=res[-1]["content"]
    if res.find ("\n") != -1:
        res = res.split("\n")[0]    
    print(fg.yellow + res + fg.rs)
    

def start():
    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    pipe = pipeline('text-generation', model='Qwen/Qwen2-1.5B', device_map=device)

    message = [
        { "role":"system","content":"Chatbot:" }
        ,
        { "role":"user","content":"User:" }
    ]

    ask_question(pipe, "Start convertation?", True)
    while True:
        prompt = input ("\nQuestion:")
        message[1]["content"] = prompt
        if prompt == "exit":
            break
        ask_question(pipe, message , False)


if __name__ == '__main__':
    # Load the model
    start()
# Copyright (c) Sebastian Raschka under Apache License 2.0 (see LICENSE.txt).
# Source for "Build a Large Language Model From Scratch"
#   - https://www.manning.com/books/build-a-large-language-model-from-scratch
# Code: https://github.com/rasbt/LLMs-from-scratch

""" Notes by AlNao:
- Ispired from "Listing 5.1 Utility functions for text to token ID conversion" section of document
    See https://github.com/rasbt/LLMs-from-scratch/blob/main/ch05/01_main-chapter-code/README.md    
- This script run the GPT model with the same configuration as in the previous chapter, but with a shorter context length.
    The output text is different from the previous chapter, which shows that the model is not deterministic and
    that the output can vary depending on the context length and the random seed.
- My output text is always:
    Every effort moves you Samoa parad Defensive MacBook Referospace preparation Einstein ShepherdMot
- Clearly, the model isn't yet producing coherent text because it hasn't undergone training. 
    To define what makes text “coherent” or “high quality,” we have to implement a numerical method to evaluate the generated content.
    This approach will enable us to monitor and enhance the model's performance throughout its training process.

To run 
- Use a virtual environment (venv) and install the required libraries
    source .venv/bin/activate (on main project directory - PythonExamples)
    pip install tensorflow-cpu torch tiktoken
- Run the script
    python ./AI/BuildLargeLanguageModel/ch5_file2_generator_inconsistency.py
    note: edit "from" statement if script is run from a different directory (add AI.BuildLargeLanguageModel. before ch5_file1_previus_chapters)

The "ch5_file2_generator_inconsistency.py" contains 
    - text_to_token_ids(text, tokenizer)
    - token_ids_to_text(token_ids, tokenizer)
    Funzione ch5_file2_main(start_context):
    - imposta seed (torch.manual_seed(123)),
    - crea GPTModel con context length 256,
    - genera 10 token dal prompt,
    - stampa il testo risultante.

Questo script fa questo.
- Carica un modello GPT non addestrato con una lunghezza di contesto di 256 token.
- Genera testo a partire da un prompt di input e mostra l'incoerenza del
    testo generato, evidenziando la necessità di un processo di addestramento per migliorare la qualità del testo prodotto.
Scopo: mostrare che un modello non addestrato produce testo poco coerente.
"""


"""
TO RUN: 
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    # only if GPU
    # pip install tensorflow
    # only if CPU
    pip install tensorflow-cpu torch tiktoken

    python ch5_file2_generator_inconsistency.py
"""





from pydoc import text

import tiktoken
import torch
from ch5_file1_previus_chapters import generate_text_simple
from ch5_file1_previus_chapters import GPTModel

GPT_CONFIG_124M = {#context length from 1,024 to 256 tokens.
    "vocab_size": 50257,
    "context_length": 256,
    "emb_dim": 768,
    "n_heads": 12,
    "n_layers": 12,
    "drop_rate": 0.1,
    "qkv_bias": False
}

def text_to_token_ids(text, tokenizer):
    encoded = tokenizer.encode(text, allowed_special={'<|endoftext|>'})
    encoded_tensor = torch.tensor(encoded).unsqueeze(0)
    return encoded_tensor
def token_ids_to_text(token_ids, tokenizer):
    flat = token_ids.squeeze(0)
    return tokenizer.decode(flat.tolist()) #.unsqueeze(0) adds the batch dimension

def ch5_file2_main(start_context):
    torch.manual_seed(123)
    model = GPTModel(GPT_CONFIG_124M)

    tokenizer = tiktoken.get_encoding("gpt2")
    token_ids = generate_text_simple(
        model=model,
        idx=text_to_token_ids(start_context, tokenizer),
        max_new_tokens=10,
        context_size=GPT_CONFIG_124M["context_length"]
    )   
    print("Output text:\n", token_ids_to_text(token_ids, tokenizer))

if __name__ == "__main__":
    start_context = "Every effort moves you"
    ch5_file2_main(start_context)

# and the output text is:
#  Every effort moves you Samoa parad Defensive MacBook Referospace preparation Einstein ShepherdMot
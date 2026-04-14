# Copyright (c) Sebastian Raschka under Apache License 2.0 (see LICENSE.txt).
# Source for "Build a Large Language Model From Scratch"
#   - https://www.manning.com/books/build-a-large-language-model-from-scratch
# Code: https://github.com/rasbt/LLMs-from-scratch

""" Notes by AlNao:
- Ispired from "Listing 5.1 Utility functions for text to token ID conversion" section of document
    See     https://github.com/rasbt/LLMs-from-scratch/blob/main/ch5_file5_generate.py
    Chapter 5 **Pretraining on Unlabeled Data** [Video](https://www.youtube.com/watch?v=Zar2TJv-sE0)
- This script demonstrates the process of training a GPT model on a text dataset, evaluating its performance, and generating sample text during training.
    - The script includes functions for calculating loss on batches and dataloaders, evaluating the model, generating sample text, and the main training loop.
    - The main function initializes the model and tokenizer, sets training parameters, and starts the training process.
    - The training loop includes forward and backward passes, optimizer steps, token counting, periodic evaluation, and sample generation at the end of each epoch.
    - The script uses a small dataset (the-verdict.txt) and a GPT-124M model for demonstration purposes.
To run
- Use a virtual environment (venv) and install the required libraries
    source .venv/bin/activate (on main project directory - PythonExamples)
    pip install tensorflow-cpu torch tiktoken matplotlib  
- Run the script
    python ./AI/BuildLargeLanguageModel/ch5_file5_generate.py
        note: edit "from" statement if script is run from a different directory (add AI.BuildLargeLanguageModel. before ch5_file)

Components of "ch5_file5_generate.py":
- generate(...): funzione per generare testo con opzioni di temperatura e top_k sampling.
- main(...): scarica i pesi di GPT-2, inizializza il modello, e genera testo a partire da un prompt.
    - importante : file model.ckpt.data-00000-of-00001 è di 498 Mb, quindi assicurati di avere spazio sufficiente e una connessione stabile per il download.

- Output text:
    PROMPT = "Every effort moves you"
    Every effort moves you toward finding an ideal life. You don't have to accept your problems by trying to remedy them, because that would be foolish

    PROMPT = "Venice is a city"
    Venice is a city which is well known for its small but growing wealth and is well known by its proximity to the capital of Rome. The city
"""

import argparse
import json
import numpy as np
import os

import requests
import tensorflow as tf
import tiktoken
import torch
from tqdm import tqdm

#from ch5_file1_previus_chapters import generate_text_simple
from ch5_file1_previus_chapters import GPTModel
#from ch5_file1_previus_chapters import create_dataloader_v1
from ch5_file2_generator_inconsistency import text_to_token_ids
from ch5_file2_generator_inconsistency import token_ids_to_text
from ch5_file4_download_gpt2_params import download_and_load_gpt2
from ch5_file4_download_gpt2_params import load_weights_into_gpt 

PROMPT = "Venice is a city" # "Every effort moves you"


def generate(model, idx, max_new_tokens, context_size, temperature=0.0, top_k=None, eos_id=None):

    # For-loop is the same as before: Get logits, and only focus on last time step
    for _ in range(max_new_tokens):
        idx_cond = idx[:, -context_size:]
        with torch.no_grad():
            logits = model(idx_cond)
        logits = logits[:, -1, :]

        # New: Filter logits with top_k sampling
        if top_k is not None:
            # Keep only top_k values
            top_logits, _ = torch.topk(logits, top_k)
            min_val = top_logits[:, -1]
            logits = torch.where(logits < min_val, torch.tensor(float("-inf")).to(logits.device), logits)

        # New: Apply temperature scaling
        if temperature > 0.0:
            logits = logits / temperature

            # New (not in book): numerical stability tip to get equivalent results on mps device
            # subtract rowwise max before softmax
            logits = logits - logits.max(dim=-1, keepdim=True).values

            # Apply softmax to get probabilities
            probs = torch.softmax(logits, dim=-1)  # (batch_size, context_len)

            # Sample from the distribution
            idx_next = torch.multinomial(probs, num_samples=1)  # (batch_size, 1)

        # Otherwise same as before: get idx of the vocab entry with the highest logits value
        else:
            idx_next = torch.argmax(logits, dim=-1, keepdim=True)  # (batch_size, 1)

        if idx_next == eos_id:  # Stop generating early if end-of-sequence token is encountered and eos_id is specified
            break

        # Same as before: append sampled index to the running sequence
        idx = torch.cat((idx, idx_next), dim=1)  # (batch_size, num_tokens+1)

    return idx


def main(gpt_config, input_prompt, model_size, device):

    settings, params = download_and_load_gpt2(model_size=model_size, models_dir="gpt2")

    gpt = GPTModel(gpt_config)
    load_weights_into_gpt(gpt, params)
    gpt.to(device)
    gpt.eval()

    tokenizer = tiktoken.get_encoding("gpt2")
    torch.manual_seed(123)

    token_ids = generate(
        model=gpt,
        idx=text_to_token_ids(input_prompt, tokenizer).to(device),
        max_new_tokens=25,
        context_size=gpt_config["context_length"],
        top_k=50,
        temperature=1.0
    )

    print("Output text:\n", token_ids_to_text(token_ids, tokenizer))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description="Generate text with a pretrained GPT-2 model.")
    parser.add_argument(
        "--prompt",
        default=PROMPT,
        help="Prompt text used to seed the generation."
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Device for running inference, e.g., cpu, cuda, mps, or auto."
    )

    args = parser.parse_args()


    torch.manual_seed(123)

    CHOOSE_MODEL = "gpt2-small (124M)"
    INPUT_PROMPT = args.prompt
    DEVICE = torch.device(args.device)

    print("PyTorch:", torch.__version__)
    print("Device:", DEVICE)


    BASE_CONFIG = {
        "vocab_size": 50257,     # Vocabulary size
        "context_length": 1024,  # Context length
        "drop_rate": 0.0,        # Dropout rate
        "qkv_bias": True         # Query-key-value bias
    }

    model_configs = {
        "gpt2-small (124M)": {"emb_dim": 768, "n_layers": 12, "n_heads": 12},
        "gpt2-medium (355M)": {"emb_dim": 1024, "n_layers": 24, "n_heads": 16},
        "gpt2-large (774M)": {"emb_dim": 1280, "n_layers": 36, "n_heads": 20},
        "gpt2-xl (1558M)": {"emb_dim": 1600, "n_layers": 48, "n_heads": 25},
    }

    model_size = CHOOSE_MODEL.split(" ")[-1].lstrip("(").rstrip(")")

    BASE_CONFIG.update(model_configs[CHOOSE_MODEL])

    main(BASE_CONFIG, INPUT_PROMPT, model_size, DEVICE)
# Copyright (c) Sebastian Raschka under Apache License 2.0 (see LICENSE.txt).
# Source for "Build a Large Language Model From Scratch"
#   - https://www.manning.com/books/build-a-large-language-model-from-scratch
# Code: https://github.com/rasbt/LLMs-from-scratch
# Original code: # https://github.com/rasbt/LLMs-from-scratch/blob/main/ch05/01_main-chapter-code/gpt_train.py

""" Notes by AlNao:

To run 
- Use a virtual environment (venv) and install the required libraries
    source .venv/bin/activate (on main project directory - PythonExamples)
    pip install tensorflow-cpu torch tiktoken
- install pyplot
    pip install matplotlib

- Run the script
    python ./AI/BuildLargeLanguageModel/ch5_file3_training_evaluate_model.py
    note: edit "from" statement if script is run from a different directory (add AI.BuildLargeLanguageModel. before ch5_file1_previus_chapters)

Components "ch5_file3_training_evaluate_model.py": training e valutazione
    - calc_loss_batch(...): cross-entropy tra logits e target per un batch.
    - calc_loss_loader(...): media loss su num_batches di un dataloader.
    - evaluate_model(...): loss train/val in no_grad() e eval().
    - generate_and_print_sample(...): genera un sample testuale durante il training.
    - train_model_simple(...): loop di training per epoche con:
        - forward/backward/optimizer step,
        - conteggio token visti,
        - valutazione periodica ogni eval_freq,
        - sample a fine epoca.
    Nel main:
        - seleziona device (cuda o cpu),
        - inizializza modello/tokenizer,
        - imposta parametri training,
        - avvia training.

Questo script fa questo
- Carica un testo (the-verdict.txt) e lo divide in train/val.
- Crea dataloader per train/val con batch_size=2 e context_length=256.
- Addestra un modello GPT-124M per 3 epoche, valutando ogni 50 step e stampando un sample generato dopo ogni epoca.
- Stampa le perde di training e validazione durante il processo.
Scopo: mostrare un processo di training completo con valutazione e generazione di sample, 
    evidenziando come la perdita si evolve e come il testo generato migliora con l'addestramento.
"""
import matplotlib.pyplot as plt
import os
import requests
import torch
import tiktoken


from ch5_file1_previus_chapters import generate_text_simple
from ch5_file1_previus_chapters import GPTModel
from ch5_file1_previus_chapters import create_dataloader_v1
from ch5_file2_generator_inconsistency import text_to_token_ids
from ch5_file2_generator_inconsistency import token_ids_to_text

GPT_CONFIG_124M = {#context length from 1,024 to 256 tokens.
    "vocab_size": 50257,
    "context_length": 256,
    "emb_dim": 768,
    "n_heads": 12,
    "n_layers": 12,
    "drop_rate": 0.1,
    "qkv_bias": False
}

def load_or_download_text(
    data_path="the-verdict.txt",
    url="https://raw.githubusercontent.com/rasbt/LLMs-from-scratch/main/ch02/01_main-chapter-code/the-verdict.txt",
):
    if not os.path.exists(data_path):
        print(f"Downloading dataset to: {data_path}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(data_path, "w", encoding="utf-8") as f:
            f.write(response.text)

    with open(data_path, "r", encoding="utf-8") as f:
        return f.read()



def calc_loss_batch(input_batch, target_batch, model, device):
    input_batch, target_batch = input_batch.to(device), target_batch.to(device)
    logits = model(input_batch)
    loss = torch.nn.functional.cross_entropy(logits.flatten(0, 1), target_batch.flatten())
    return loss


def calc_loss_loader(data_loader, model, device, num_batches=None):
    total_loss = 0.
    if len(data_loader) == 0:
        return float("nan")
    elif num_batches is None:
        num_batches = len(data_loader)
    else:
        num_batches = min(num_batches, len(data_loader))
    for i, (input_batch, target_batch) in enumerate(data_loader):
        if i < num_batches:
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            total_loss += loss.item()
        else:
            break
    return total_loss / num_batches


def evaluate_model(model, train_loader, val_loader, device, eval_iter):
    model.eval()
    with torch.no_grad():
        train_loss = calc_loss_loader(train_loader, model, device, num_batches=eval_iter)
        val_loss = calc_loss_loader(val_loader, model, device, num_batches=eval_iter)
    model.train()
    return train_loss, val_loss


def generate_and_print_sample(model, tokenizer, device, start_context):
    model.eval()
    context_size = model.pos_emb.weight.shape[0]
    encoded = text_to_token_ids(start_context, tokenizer).to(device)
    with torch.no_grad():
        token_ids = generate_text_simple(
            model=model, idx=encoded,
            max_new_tokens=50, context_size=context_size
        )
        decoded_text = token_ids_to_text(token_ids, tokenizer)
        print(decoded_text.replace("\n", " "))  # Compact print format
    model.train()


def train_model_simple(model, train_loader, val_loader, optimizer, device, num_epochs,
                       eval_freq, eval_iter, start_context, tokenizer):
    # Initialize lists to track losses and tokens seen
    train_losses, val_losses, track_tokens_seen = [], [], []
    tokens_seen = 0
    global_step = -1

    # Main training loop
    for epoch in range(num_epochs):
        model.train()  # Set model to training mode

        for input_batch, target_batch in train_loader:
            optimizer.zero_grad()  # Reset loss gradients from previous batch iteration
            loss = calc_loss_batch(input_batch, target_batch, model, device)
            loss.backward()  # Calculate loss gradients
            optimizer.step()  # Update model weights using loss gradients
            tokens_seen += input_batch.numel()
            global_step += 1

            # Optional evaluation step
            if global_step % eval_freq == 0:
                train_loss, val_loss = evaluate_model(
                    model, train_loader, val_loader, device, eval_iter)
                train_losses.append(train_loss)
                val_losses.append(val_loss)
                track_tokens_seen.append(tokens_seen)
                print(f"Ep {epoch+1} (Step {global_step:06d}): "
                      f"Train loss {train_loss:.3f}, Val loss {val_loss:.3f}")

        # Print a sample text after each epoch
        generate_and_print_sample(
            model, tokenizer, device, start_context
        )

    return train_losses, val_losses, track_tokens_seen



if __name__ == "__main__":
    # Example usage
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    torch.manual_seed(123)

    # Initialize model and tokenizer
    model = GPTModel(GPT_CONFIG_124M).to(device)
    tokenizer = tiktoken.get_encoding("gpt2")

    # Load text and build real dataloaders
    raw_text = load_or_download_text()
    split_idx = int(0.9 * len(raw_text))
    train_text = raw_text[:split_idx]
    val_text = raw_text[split_idx:]

    train_loader = create_dataloader_v1(
        train_text,
        batch_size=2,
        max_length=GPT_CONFIG_124M["context_length"],
        stride=GPT_CONFIG_124M["context_length"],
        shuffle=True,
        drop_last=True,
        num_workers=0,
    )
    val_loader = create_dataloader_v1(
        val_text,
        batch_size=2,
        max_length=GPT_CONFIG_124M["context_length"],
        stride=GPT_CONFIG_124M["context_length"],
        shuffle=False,
        drop_last=False,
        num_workers=0,
    )

    print(f"Train batches: {len(train_loader)}, Val batches: {len(val_loader)}")
    if len(train_loader) == 0 or len(val_loader) == 0:
        raise RuntimeError("Dataloader vuoto. Riduci max_length o usa un testo più lungo.")

    # Training parameters
    num_epochs = 3
    eval_freq = 50
    eval_iter = 5
    start_context = "Every effort moves you"

    optimizer = torch.optim.AdamW(model.parameters(), lr=4e-4, weight_decay=0.1)

    # Train the model
    train_losses, val_losses, track_tokens_seen = train_model_simple(
        model, train_loader, val_loader, optimizer, device,
        num_epochs, eval_freq, eval_iter, start_context, tokenizer
    )

    print("Training completed.")
"""
Questo script è preso dal video 
    "Build an LLM from Scratch 5: Pretraining on Unlabeled Data" di Sebastian Raschka
    https://www.youtube.com/watch?v=Zar2TJv-sE0 - part 1
che si ispira al libro "Build a Large Language Model From Scratch" di Sebastian Raschka
    https://www.manning.com/books/build-a-large-language-model-from-scratch

Si tratta di un esempio di come addestrare un modello GPT su un dataset di testo, 
    valutare le sue prestazioni e generare testo campione durante l'addestramento.
Il codice include funzioni per calcolare la perdita su batch e dataloader, valutare

# Part 5.0 - Configure GPT-124M model and test tokenization and detokenization
# Part 5.1 - Test tokenization and detokenization
# Part 5.1.1 - Test text generation with the untrained model
# Part 5.1.2 - Calculate text generation loss: cross-entropy loss (saltato perchè un bordello e fa tanti esempi e non è facile da capire, meglio vedere il video di Sebastian Raschka)
# Part 5.1.3 - Calculate traning and validation set losses
# Part 5.2 - Training an LLM 
# Part 5.2.1 - Plot training and validation losses


"""


""" 
# Part 5.0.0: check libraries versions
from importlib.metadata import version
pkgs=["matplotlib", "numpy", "torch", "tiktoken", "tensorflow", "transformers"]
for pkg in pkgs:
    try:
        print(f"{pkg} version: {version(pkg)}")
    except Exception as e:
        print(f"Error getting version for {pkg}: {e}")
"""
CONST_FILE_PATH = "the-verdict.txt" # "shakespeare_input.txt"
CONST_URL = "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"

print ("-------------------------- 5.0.1")
# -----------------------------------------------------------------------
# Part 5.0 - Configure GPT-124M model and test tokenization and detokenization
from ch5_file1_previus_chapters import GPTModel

GPT_CONFIG_124M = {
    "vocab_size": 50257,     # Vocabulary size
    "context_length": 255 ,  # Context length (number of tokens in the input sequence) - 1024 if more RAM and GPU
    "emb_dim": 768,          # Embedding dimension (size of the token embeddings)
    "n_layers": 12,         # Number of transformer layers (blocks)
    "n_heads": 12,          # Number of attention heads in each transformer layer
    "drop_rate": 0.1,        # Dropout rate (set to 0.0 for inference)
    "qkv_bias": False         # Whether to include bias
}

import torch
torch.manual_seed(123)
model=GPTModel(GPT_CONFIG_124M)
#print(model)
model.eval()
# model.train()

print ("-------------------------- 5.1.0")
# -----------------------------------------------------------------------
# Part 5.1 - Test tokenization and detokenization
from ch5_file2_generator_inconsistency import text_to_token_ids
import tiktoken
def test_to_token_ids(test,tokenizer):
    encoded = tokenizer.encode(test, allowed_special={"<!endoftext|>"})
    encoded_tensor = torch.tensor(encoded).unsqueeze(0)  # Add batch dimension
    return  encoded_tensor

start_context = "Every effort moves you"
print ("Start context:", start_context)
tokenizer = tiktoken.get_encoding("gpt2")

token_ids = test_to_token_ids(start_context, tokenizer)
print("Token IDs:", token_ids)
# Token IDs: tensor([[6109, 3626, 6100,  345]])

def token_ids_to_text(token_ids, tokenizer):
    token_ids_list = token_ids.squeeze(0).tolist()  # Remove batch dimension and convert to list
    text = tokenizer.decode(token_ids_list)
    return text

token_ids = test_to_token_ids(start_context, tokenizer)
print("Decoded text:", token_ids_to_text(token_ids, tokenizer))
# Decoded text: Every effort moves you

print ("-------------------------- 5.1.1")
# -----------------------------------------------------------------------
# Part 5.1.1 - Test text generation with the untrained model
from ch5_file1_previus_chapters import generate_text_simple
token_ids = generate_text_simple(
    model=model, 
    idx=text_to_token_ids(start_context, tokenizer), 
    max_new_tokens=10, 
    context_size=GPT_CONFIG_124M["context_length"]
)
print("Generated token IDs:", token_ids)
print("Generated text:", token_ids_to_text(token_ids, tokenizer))
# Generated text: Every effort moves youbrainer halluc logo chancellor Todayoked celebrate21 sep Real

print ("-------------------------- 5.1.1 Alnao - compare vectors of token IDs")
# -----------------------------------------------------------------------
# Example to compare vectosr of token IDs
def example_writed_by_alnao(input_context,max_new_tokens):
    print("Input context:", input_context)
    print("Input context token IDs:", text_to_token_ids(input_context, tokenizer))
    token_ids = generate_text_simple(
        model=model, 
        idx=text_to_token_ids(input_context, tokenizer), 
        max_new_tokens=max_new_tokens, 
        context_size=GPT_CONFIG_124M["context_length"]
    )
    print("Generated token IDs:", token_ids)
    print("Generated text:", token_ids_to_text(token_ids, tokenizer))

example_writed_by_alnao("Venice is a ", 3)
"""
Input context: Venice is a 
Input context token IDs: tensor([[37522,   501,   318,   257,   220]])
Generated token IDs: tensor([[37522,   501,   318,   257,   220,  8643, 20818, 42919]])
Generated text: Venice is a ANT Naval pamphlet
"""
example_writed_by_alnao("Venice is a city in Italy", 1)
""" 
Input context: Venice is a city in Italy
Input context token IDs: tensor([[37522,   501,   318,   257,  1748,   287,  8031]])
"""

# -----------------------------------------------------------------------
# Part 5.1.2 - Calculate text generation loss: cross-entropy loss between the generated token IDs and the input token IDs
# Implement a way we can measure this quality of the text more numerically 
# so calculate TEXT GENERATION LOSS: cross-entropy and perplexity
# saltato perchè un bordello e fa tanti esempi e non è facile da capire, meglio vedere il video di Sebastian Raschka

print ("-------------------------- 5.1.3")
# -----------------------------------------------------------------------
# Part 5.1.3 - Calculate traning and validation set losses
import os
import urllib.request
file_path = CONST_FILE_PATH
if not os.path.exists(file_path):
    urllib.request.urlretrieve(CONST_URL, file_path)
with open(file_path, "r") as f:
    shakespeare_text = f.read()
print(f"shakespeare Dataset length: {len(shakespeare_text)} characters")
shakespeare_tokens=tokenizer.encode(shakespeare_text)
print(f"shakespeare Dataset length: {len(shakespeare_tokens)} tokens")

# Dataset length: 1115394 characters
from ch5_file1_previus_chapters import create_dataloader_v1
train_radio = 0.9
split_idx = int(len(shakespeare_tokens) * train_radio)
train_tokens = shakespeare_tokens[:split_idx]
val_tokens = shakespeare_tokens[split_idx:] 
train_loader = create_dataloader_v1(
    train_tokens,  
    batch_size=2,
    max_length=GPT_CONFIG_124M["context_length"],
    drop_last=True,
    shuffle=True,
    num_workers=0    
)
val_loader = create_dataloader_v1(
    val_tokens, 
    batch_size=2,
    max_length=GPT_CONFIG_124M["context_length"],
    stride=GPT_CONFIG_124M["context_length"],  # No overlap between sequences in the validation set
    drop_last=False,
    shuffle=False,
    num_workers=0    
)
print(f"Train loader batches: {len(train_loader)}, Val loader batches: {len(val_loader)}")
for x,y in train_loader:
    pass
print("Input batch shape:", x.shape , "Target batch shape:", y.shape)
    
train_tokens =0
for input_batch, target_batch in train_loader:
    train_tokens+=input_batch.numel()
val_tokens=0
for input_batch, target_batch in val_loader:
    val_tokens+=input_batch.numel()
print(f"Train tokens: {train_tokens}, Val tokens: {val_tokens}")

cuda_available = torch.cuda.is_available()
print(f"CUDA available: {cuda_available}")
device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")
model.to(device)
optimizer=torch.optim.AdamW(model.parameters(), lr=1e-4)


print ("-------------------------- 5.2 Training an LLM")
# -----------------------------------------------------------------------
# Part 5.2 Training an LLM
from ch5_file3_training_evaluate_model import train_model_simple
num_epochs = 1 #ex 10 
eval_freq=1 #ex 5
eval_iter=1 #ex 5
start_context = "Every effort moves you"
print("Starting training... ")
train_losses, val_losses , token_seen = train_model_simple(
    model,
    train_loader,
    val_loader,
    optimizer,
    device,
    num_epochs,
    eval_freq, 
    eval_iter, 
    start_context, 
    tokenizer
)

print("Training completed.")

print ("-------------------------- 5.2.1 Plot training and validation losses")
# -----------------------------------------------------------------------
# Part 5.2.1 Plot training and validation losses
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

def plot_losses(epochs, token, train_losses, val_losses):
    plt.figure(figsize=(10,5))
    plt.plot(epochs, train_losses, label='Train Loss')
    plt.plot(epochs, val_losses, label='Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.title('Training and Validation Loss over Epochs')
    plt.legend()
    plt.grid()
    plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.savefig("training_validation_loss.png")
    plt.show()


# riprendere video
# https://www.youtube.com/watch?v=Zar2TJv-sE0
# dal 1:34:00 in poi
# per vedere come addestrare un modello GPT su un dataset di testo,
# valutare le sue prestazioni e generare testo campione durante l'addestramento.

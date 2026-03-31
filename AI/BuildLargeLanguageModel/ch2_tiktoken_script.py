# Copyright (c) Sebastian Raschka under Apache License 2.0 (see LICENSE.txt).
# Source for "Build a Large Language Model From Scratch"
#   - https://www.manning.com/books/build-a-large-language-model-from-scratch
# Code: https://github.com/rasbt/LLMs-from-scratch

import tiktoken
from importlib.metadata import version

from tqdm import main

""" Notes by AlNao:
    Simple script ispired by book: "Build a Large Language Model (From Scratch)" by Sebastian Raschka
    Chapter 2: Working with text data - 2.5 Byte pair encoding
        see https://github.com/rasbt/LLMs-from-scratch

Let's look at a more sophisticated tokenization scheme based on a concept called byte
    pair encoding (BPE). The BPE tokenizer was used to train LLMs such as GPT-2, GPT-3,
    and the original model used in ChatGPT.

To run 
- Use a virtual environment (venv) and install the required libraries
    source .venv/bin/activate (on main project directory - PythonExamples)
    pip install tiktoken
- Run the script
    python ./AI/BuildLargeLanguageModel/ch2_tiktoken_script.py    

"""

def main():
    print("tiktoken version:", version("tiktoken"))
    text = (
        "Hello, do you like tea? <|endoftext|> In the sunlit terraces"
        "of someunknownPlace."
    )
    tokenizer=tiktoken.get_encoding("gpt2")
    integers = tokenizer.encode(text, allowed_special={"<|endoftext|>"})
    print(integers)
    strings = tokenizer.decode(integers)
    print(strings)

if __name__ == "__main__":
    main()
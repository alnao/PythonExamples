import tiktoken
from importlib.metadata import version

"""
Simple script ispired by book: "Build a Large Language Model (From Scratch)" by Sebastian Raschka
Chapter 2: Working with text data - 2.5 Byte pair encoding

see https://github.com/rasbt/LLMs-from-scratch

Let’s look at a more sophisticated tokenization scheme based on a concept called byte
pair encoding (BPE). The BPE tokenizer was used to train LLMs such as GPT-2, GPT-3,
and the original model used in ChatGPT.

"""

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
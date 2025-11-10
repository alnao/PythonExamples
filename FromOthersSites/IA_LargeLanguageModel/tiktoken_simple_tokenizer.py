import re
import urllib.request

"""
Simple script ispired by book: "Build a Large Language Model (From Scratch)" by Sebastian Raschka
Chapter 2: Working with text data - 2.4 Adding special context tokens

see https://github.com/rasbt/LLMs-from-scratch

Let’s discuss how we split input text into individual tokens, a required preprocessing step for creating embeddings for an LLM.
Let’s convert these tokens from a Python string to an integer representation to produce the token IDs
These special tokens can include markers for unknown words and document boundaries, for example. In
particular, we will modify the vocabulary and tokenizer, SimpleTokenizerV2, to support two new tokens, <|unk|> and <|endoftext|>
"""


class SimpleTokenizerV2:
	def __init__(self, vocab):
		# Token speciali
		self.unk_token = "<|unk|>"
		self.eot_token = "<|endoftext|>"
		self.vocab = vocab #{self.unk_token: 0, self.eot_token: 1}
		self.inverse_vocab = {0: self.unk_token, 1: self.eot_token}
	def build_vocab(self, tokens):
		"""Costruisce il vocabolario includendo i token speciali."""
		unique_tokens = sorted(set(tokens))
		# Si parte da 2 per lasciare spazio ai token speciali
		for idx, token in enumerate(unique_tokens, start=2):
			self.vocab[token] = idx
			self.inverse_vocab[idx] = token
	def encode(self, text):
		"""Converte il testo in token ID, gestendo parole sconosciute."""
		tokens = text.split()
		token_ids = []
		for token in tokens:
			token_ids.append(self.vocab.get(token, self.vocab[self.unk_token]))
		# Aggiunge il token di fine testo
		token_ids.append(self.vocab[self.eot_token])
		return token_ids
	def decode(self, token_ids):
		"""Converte i token ID in testo, ignorando il token di fine testo."""
		tokens = [
			self.inverse_vocab.get(tid, self.unk_token)
			for tid in token_ids
			if tid != self.vocab[self.eot_token]
		]
		return " ".join(tokens)
	
url = ("https://raw.githubusercontent.com/rasbt/"
"LLMs-from-scratch/main/ch02/01_main-chapter-code/"
"the-verdict.txt")
file_path = "the-verdict.txt"
urllib.request.urlretrieve(url, file_path)
with open("the-verdict.txt", "r", encoding="utf-8") as f:
	raw_text = f.read()
print("Total number of character:", len(raw_text))

text = "Hello, world. Is this-- a test?"
result = re.split(r'([,.:;?_!"()\']|--|\s)', text)
result = [item.strip() for item in result if item.strip()]
print(result)
preprocessed = re.split(r'([,.:;?_!"()\']|--|\s)', raw_text)
preprocessed = [item.strip() for item in preprocessed if item.strip()]
print(len(preprocessed))
all_tokens = sorted(list(set(preprocessed)))
all_tokens.extend(["<|endoftext|>", "<|unk|>"])
vocab = {token:integer for integer,token in enumerate(all_tokens)}

text1 = "Hello, do you like tea?"
text2 = "In the sunlit terraces of the palace. I'm Alberto, nice to meet you! Hello!"
text = " <|endoftext|> ".join((text1, text2))
print(text)
tokenizer = SimpleTokenizerV2(vocab)
print(tokenizer.encode(text))
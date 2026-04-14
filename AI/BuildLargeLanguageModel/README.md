# Build a Large Language Model (From Scratch)

This folder contains the code for developing, pretraining, and finetuning a GPT-like LLM and is the official code repository for the book Build a Large Language Model (From Scratch).

See [Official GitHub Page](https://github.com/rasbt/LLMs-from-scratch/tree/main), ISBN 9781633437166.
- Chapter 5 **Pretraining on Unlabeled Data** [Video](https://www.youtube.com/watch?v=Zar2TJv-sE0)

# Files
- `ch2_tiktoken_script.py`: Script che mostra la tokenizzazione BPE con la libreria tiktoken. Esegue una semplice codifica e decodifica di testo per illustrare il funzionamento dei tokenizer usati nei LLM.
- `ch2_tiktoken_simple_tokenizer.py`: Implementa un tokenizer semplice con gestione di token speciali come <|unk|> e <|endoftext|>. Mostra come costruire un vocabolario e convertire testo in ID di token.
- `ch5_file1_previus_chapters.py`: Raccoglie tutto il codice fondamentale dei capitoli 2-4, inclusi dataset, modelli e funzioni di generazione. Serve come base per i capitoli successivi e può essere eseguito come script standalone.
- `ch5_file2_generator_inconsistency.py`: Dimostra che un modello GPT non addestrato genera testo incoerente. Mostra l'importanza dell'addestramento per ottenere output di qualità.
- `ch5_file3_training_evaluate_model.py`: Script completo per addestrare e valutare un modello GPT su un dataset di testo. Include funzioni per calcolare la loss, valutare il modello e generare campioni durante il training.
- `ch5_file4_download_gpt2_params.py`: Script utility per scaricare i parametri pre-addestrati di GPT-2 dai checkpoint TensorFlow e caricarli in un modello PyTorch. Utile per inizializzare modelli con pesi reali.
- `ch5_file5_generate.py`: Esegue la generazione di testo usando un modello GPT-2 pre-addestrato. Permette di impostare prompt, device e parametri di sampling per testare la generazione autoregressiva.
- `ch5_file6_text_generation.py`: Esegue l'addestramento di un modello, script fatto seguendo il video [
Build an LLM from Scratch 5: Pretraining on Unlabeled Data](https://www.youtube.com/watch?v=Zar2TJv-sE0)

- next todo GPT 2 Llama https://github.com/rasbt/LLMs-from-scratch/blob/main/ch05/07_gpt_to_llama/README.md


# Copyright
- Copyright (c) Sebastian Raschka under Apache License 2.0
- Qui riportati da AlNao con alcune modifiche e annotazioni!

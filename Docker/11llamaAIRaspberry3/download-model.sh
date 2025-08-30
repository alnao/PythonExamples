#!/bin/bash
MODEL_DIR="/llama.cpp/models"
MODEL_NAME="tinyllama-gguf"

mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

if [ ! -f "${MODEL_NAME}.gguf" ]; then
  echo "➡️ Scaricamento del modello TinyLLaMA quantizzato..."
  
  # Prova diversi URL in ordine di preferenza
  URLS=(
    #600Mb TinyLlama
    "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_0.gguf"
    # 6.7 Gb 
    #"https://huggingface.co/DavidAU/Llama-3.2-8X3B-MOE-Dark-Champion-Instruct-uncensored-abliterated-18.4B-GGUF/resolve/main/L3.2-8X3B-MOE-Dark-Champion-Inst-18.4B-uncen-ablit_D_AU-Q2_k.gguf?download=true"
    # 14Gb Mistral 
    #"https://huggingface.co/MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3.fp16.gguf?download=true"
    # large mxbai
    # "https://huggingface.co/mixedbread-ai/mxbai-embed-large-v1/resolve/main/gguf/mxbai-embed-large-v1-f16.gguf?download=true"
  )
  
  DOWNLOADED=false
  for url in "${URLS[@]}"; do
    echo "🔄 Tentativo download da: $url"
    
    if curl -L --insecure -o "${MODEL_NAME}.gguf" "$url"; then
      # Verifica dimensione
      if [ -f "${MODEL_NAME}.gguf" ]; then
        FILE_SIZE=$(stat -c%s "${MODEL_NAME}.gguf")
        echo "📁 Dimensione file: $FILE_SIZE bytes"
        
        if [ $FILE_SIZE -gt 1000000 ]; then  # Almeno 1MB
          echo "✅ Modello scaricato con successo"
          DOWNLOADED=true
          break
        else
          echo "❌ File troppo piccolo, tentativo successivo..."
          rm -f "${MODEL_NAME}.gguf"
        fi
      fi
    else
      echo "❌ Errore nel download, tentativo successivo..."
    fi
  done
  
  if [ "$DOWNLOADED" = false ]; then
    echo "❌ Impossibile scaricare il modello da tutti gli URL"
    exit 1
  fi
else
  echo "✅ Modello già presente."
fi
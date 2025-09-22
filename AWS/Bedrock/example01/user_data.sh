#!/bin/bash
cd /home/ec2-user
# Clona la tua repo (modifica con l’URL della tua repo!)
git clone https://github.com/alnao/your-pocket-rag-repo.git app
cd app

# Installa Python e dipendenze
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-devel git gcc

python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn[standard] boto3 pydantic-settings python-multipart chromadb tiktoken

# Avvia il servizio FastAPI (modifica il path/main se necessario)
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &

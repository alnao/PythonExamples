#!/bin/bash
# User data dell'EC2 (Ubuntu 24.04): installa il Pocket RAG come servizio systemd dietro Apache.
# I segnaposto __REGION__, __BUCKET_NAME__, __API_KEY_PARAMETER__ e __APP_URL__ vengono
# sostituiti da bedrock_rag_stack.sh prima del lancio dell'istanza. __APP_URL__ e' un URL
# prefirmato (valido un'ora) del pacchetto con il codice locale caricato sul bucket.
set -euxo pipefail
exec > >(tee -a /var/log/user-data.log) 2>&1
echo "User data start on $(date)"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3-venv apache2 tesseract-ocr tesseract-ocr-ita poppler-utils

# Codice dal pacchetto sul bucket (backend.py, requirements.txt, web/)
APP_DIR=/opt/pocket-rag
mkdir -p $APP_DIR
curl -fsSL "__APP_URL__" -o /tmp/pocket-rag.tar.gz
tar xzf /tmp/pocket-rag.tar.gz -C $APP_DIR
rm -f /tmp/pocket-rag.tar.gz

python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install --upgrade pip
$APP_DIR/venv/bin/pip install -r $APP_DIR/requirements.txt

cat > $APP_DIR/.env <<EOF
AWS_REGION=__REGION__
S3_BUCKET=__BUCKET_NAME__
API_KEY_PARAMETER=__API_KEY_PARAMETER__
EOF
chown -R ubuntu:ubuntu $APP_DIR

# Backend come servizio: riparte da solo dopo un errore o un riavvio dell'istanza
cat > /etc/systemd/system/pocket-rag.service <<EOF
[Unit]
Description=Pocket RAG (FastAPI + Bedrock)
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn backend:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now pocket-rag

# Apache sulla porta 80 inoltra tutto a uvicorn (sito e API)
a2enmod proxy proxy_http
cat > /etc/apache2/sites-available/pocket-rag.conf <<EOF
<VirtualHost *:80>
    ProxyPreserveHost On
    ProxyTimeout 600
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
EOF
a2dissite 000-default
a2ensite pocket-rag
systemctl reload apache2

echo "User data completed on $(date)"

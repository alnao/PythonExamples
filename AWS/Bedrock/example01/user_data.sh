#!/bin/bash
cd /home/ec2-user
echo "User data script start on $(date)" > /home/ec2-user/user_data.log

# Installa git, apache e aggiorna il sistema
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-devel git gcc httpd

# Avvia e abilita Apache
sudo systemctl start httpd
sudo systemctl enable httpd

# Clona la tua repo
git clone https://github.com/alnao/PythonExamples.git app
cd app/AWS/Bedrock/example01

# Copia la pagina HTML dal repository
sudo cp index.html /var/www/html/

# Installa Python e dipendenze
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn[standard] boto3 pydantic-settings python-multipart chromadb tiktoken

# Avvia il servizio FastAPI (modifica il path/main se necessario)
nohup venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &

echo "User data script executed successfully on $(date)" >> /home/ec2-user/user_data.log

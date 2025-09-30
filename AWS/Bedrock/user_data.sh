#!/bin/bash
cd /home/ubuntu
echo "User data script start on $(date)" > /home/ubuntu/user_data.log

# Installa git, apache e aggiorna il sistema
#sudo yum update -y
#sudo yum install -y python3.11 python3.11-devel git gcc httpd
sudo apt-get update -y
sudo apt-get install -y python3.10 python3.10-venv python3.10-dev git gcc apache2
sudo apt-get install -y build-essential python3-dev
sudo apt-get install -y libssl-dev libffi-dev python3-pip
sudo apt-get install -y libxml2-dev libxslt1-dev zlib1g
sudo apt-get install -y libjpeg-dev libpng-dev
sudo apt-get install -y libpq-dev
sudo apt-get install -y libblas-dev liblapack-dev libatlas-base-dev gfor
sudo apt-get install -y libtbb2 libtbb-dev
sudo apt-get install -y libreadline-dev libbz2-dev libsqlite3-dev wget
sudo apt-get install -y curl llvm libncurses5-dev libncursesw5-dev
sudo apt-get install -y xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
sudo apt-get install -y libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff5-dev tcl8-dev
sudo apt-get install -y libmpdec-dev libgdbm-dev libncursesw5-dev libreadline-dev
sudo apt-get install -y libssl-dev libffi-dev libsqlite3-dev libbz2-dev libexpat1-dev
sudo apt-get install -y liblzma-dev zlib1g-dev libgdbm-compat-dev
sudo apt-get install -y libblas-dev liblapack-dev libatlas-base-dev gfortran
sudo apt-get install -y libtbb2 libtbb-dev
sudo apt-get install -y libpq-dev
sudo apt-get install -y tesseract-ocr poppler-utils

# Avvia e abilita Apache
sudo systemctl start apache2
sudo systemctl enable apache2

# Clona la tua repo
git clone https://github.com/alnao/PythonExamples.git app
cd app/AWS/Bedrock/web

# Copia la pagina HTML dal repository
sudo cp index.html /var/www/html/
sudo cp index.js /var/www/html/

cd ..
# Installa Python e dipendenze
python3.10 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn[standard] boto3 pydantic-settings python-multipart chromadb tiktoken
pip install PyPDF2 pillow python-docx openpyxl python-pptx
pip install "langchain<0.1.0"
pip install "boto3<2.0.0"
pip install chromadb==0.3.22 #pip install "chromadb<0.4.0" #NO pip install hnswlib #https://stackoverflow.com/questions/73969269/error-could-not-build-wheels-for-hnswlib-which-is-required-to-install-pyprojec
pip install "fastapi<1.0.0"     # Per evitare problemi di compatibilità con versioni future
pip install "uvicorn<1.0.0"     # Per evitare problemi di compatibilità con versioni future
pip install "pydantic>=2.7.0"
pip install "tiktoken<0.4.0"    # Per evitare problemi di compatibilità con versioni future
pip install "python-multipart<1.0.0"  # Per evitare problemi di compatibilità con versioni future
sudo chmod 777 venv/ -R
pip install pytesseract pdf2image pillow
#nota questi devono essere dopo, non so il motivo
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ita poppler-utils

#crea cartella chroma
mkdir -p ./chroma
sudo chown -R ubuntu:ubuntu ./chroma
sudo chmod -R u+rw ./chroma

# Avvia il servizio FastAPI (modifica il path/main se necessario)
nohup venv/bin/uvicorn backend:app --host 0.0.0.0 --port 8000 > fastapi.log 2>&1 &

echo "User data script executed successfully on $(date)" >> /home/ubuntu/user_data.log

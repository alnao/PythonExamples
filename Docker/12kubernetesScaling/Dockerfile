FROM python:3.10-slim

# Install curl, wget e dipendenze di sistema
RUN apt-get update 
RUN apt-get install -y curl wget gcc python3-dev procps nmon htop glances && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Crea una directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY cpu.py .

# Installa le dipendenze Python
RUN pip install --no-cache-dir fastapi uvicorn psutil

# Espone la porta dell’API
EXPOSE 8000

# Comando di avvio
CMD ["python", "cpu.py"]

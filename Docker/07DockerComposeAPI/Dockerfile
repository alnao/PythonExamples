# Usa un'immagine Python ufficiale
FROM python:3.9-slim

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file necessari
COPY requirements.txt .

# Installa le dipendenze
RUN pip install --no-cache-dir -r requirements.txt --break-system-packages

# Copia il resto dell'applicazione
COPY . .

# Espone la porta su cui gira l'app Flask
EXPOSE 5000

# Avvia l'applicazione
CMD ["python", "app/routes.py"]
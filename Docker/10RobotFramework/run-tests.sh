#!/bin/bash

# Crea la cartella output se non esiste
mkdir -p output

# Pulisce i file precedenti (opzionale)
rm -f output/*

# Verifica che le librerie esistano
if [ ! -f "robotLib/KafkaLibrary.py" ] || [ ! -f "robotLib/DynamoLibrary.py" ]; then
    echo "❌ Errore: Librerie non trovate in robotLib/"
    exit 1
fi

# Verifica che __init__.py esista
if [ ! -f "robotLib/__init__.py" ]; then
    echo "⚠️  Creando __init__.py mancante..."
    touch robotLib/__init__.py
fi

# Esegue i test con timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🚀 Avvio test Robot Framework..."
echo "📁 Output salvato in: ./output/"

robot --outputdir robotoutput \
      --loglevel INFO \
      --pythonpath . \
      esempio10.robot

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test completati con successo!"
    echo "📄 Apri output/log_${TIMESTAMP}.html per vedere i risultati dettagliati"
else
    echo "❌ Test falliti con codice di uscita: $EXIT_CODE"
    echo "📄 Controlla output/log_${TIMESTAMP}.html per i dettagli"
fi

exit $EXIT_CODE
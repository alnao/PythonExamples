#!/bin/bash

# Create output directory if it doesn't exist
mkdir -p robotoutput

# Clean previous files (optional)
rm -f robotoutput/*

# Execute tests with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "> Starting Robot Framework tests..."
echo "> Output saved in: ./robotoutput/"

# Esegue i test
robot \
    --outputdir robotoutput \
    --loglevel INFO \
    --pythonpath . \
    --report report_${TIMESTAMP}.html \
    --log log_${TIMESTAMP}.html \
    --output output_${TIMESTAMP}.xml \
    test.robot

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "> Test completati con successo!"
    echo "> Report: robotoutput/report_${TIMESTAMP}.html"
    echo "> Log: robotoutput/log_${TIMESTAMP}.html"
else
    echo "> Test falliti con codice di uscita: $EXIT_CODE"
    echo "> Controlla i file di output per i dettagli"
fi

# Apri automaticamente il report (opzionale - rimuovi se non desiderato)
if command -v xdg-open > /dev/null; then
    xdg-open robotoutput/report_${TIMESTAMP}.html
elif command -v open > /dev/null; then
    open robotoutput/report_${TIMESTAMP}.html
fi

exit $EXIT_CODE
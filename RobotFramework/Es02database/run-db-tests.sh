#!/bin/bash

# Avvia i container del database
echo "> Avvio container database..."
docker-compose up -d

# Attende che il database sia pronto
echo "> Attendo che il database sia pronto..."
sleep 10


pip install -r requirements.txt

# Crea la cartella output
mkdir -p robotoutput
rm -f robotoutput/*

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "> Avvio test database con Robot Framework..."

# Esegue i test
robot \
    --outputdir robotoutput \
    --loglevel INFO \
    --pythonpath . \
    --report db_report_${TIMESTAMP}.html \
    --log db_log_${TIMESTAMP}.html \
    --output db_output_${TIMESTAMP}.xml \
    database_tests.robot

EXIT_CODE=$?

# Ferma i container
echo "> Fermando container database..."
docker-compose down

if [ $EXIT_CODE -eq 0 ]; then
    echo "> Test database completati con successo!"
    echo "> Report: robotoutput/db_report_${TIMESTAMP}.html"
else
    echo "> Test database falliti con codice: $EXIT_CODE"
fi

exit $EXIT_CODE
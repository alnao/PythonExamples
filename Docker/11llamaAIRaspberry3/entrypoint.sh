#!/bin/bash
set -e

echo "🔍 Debug: Ricerca server..."
# Cerca il server con entrambi i nomi possibili
SERVER_PATH=""
for path in "/llama.cpp/build/bin/llama-server" "/llama.cpp/build/bin/server"; do
    if [ -f "$path" ] && [ -x "$path" ]; then
        SERVER_PATH="$path"
        break
    fi
done

if [ -z "$SERVER_PATH" ]; then
    echo "❌ Server non trovato. Ricerca completa..."
    find /llama.cpp -name "*server*" -type f -executable 2>/dev/null || true
    exit 1
fi

echo "✅ Server trovato: $SERVER_PATH"

# Scarica modello
echo "📥 Scaricamento modello..."
/download-model.sh

MODEL_PATH="/llama.cpp/models/tinyllama-gguf.gguf"

# Verifica modello
if [ ! -f "$MODEL_PATH" ]; then
    echo "❌ Modello non trovato: $MODEL_PATH"
    ls -la /llama.cpp/models/
    exit 1
fi

echo "✅ Modello trovato: $MODEL_PATH"

# Avvia server
echo "🚀 Avvio server llama.cpp..."
$SERVER_PATH -m "$MODEL_PATH" --port 8080 --host 0.0.0.0 --ctx-size 512 --threads 4 &
SERVER_PID=$!

# Aspetta avvio
sleep 10

# Verifica che il server sia in ascolto
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "❌ Server non risponde, provo ancora..."
    sleep 5
    if ! curl -s http://localhost:8080/health > /dev/null; then
        echo "❌ Server definitivamente non risponde"
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
fi

echo "✅ Server llama.cpp avviato"

# Avvia UI Flask
echo "🌐 Avvio interfaccia web..."
export FLASK_APP=/ui/app.py
cd /ui
python3 -m flask run --host=0.0.0.0 --port=5000 &
FLASK_PID=$!

# Gestione cleanup
cleanup() {
    echo "🛑 Stopping services..."
    kill $SERVER_PID $FLASK_PID 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

echo "🎉 Servizi avviati!"
echo "📡 API: http://localhost:8080"
echo "🌐 Web UI: http://localhost:5000"

# Aspetta processi
wait $SERVER_PID $FLASK_PID
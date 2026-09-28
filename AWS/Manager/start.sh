#!/usr/bin/env bash
# Avvia app.py: funziona da qualsiasi cartella perche' si sposta in quella dello script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# usa il virtualenv condiviso alla radice del repository, se esiste
VENV_PYTHON="$SCRIPT_DIR/../../.venv/bin/python"
if [ -x "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="python3"
fi

exec "$PYTHON" app.py "$@"

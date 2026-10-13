#!/bin/bash
# Crea la cartella layer/ con boto3 per le Lambda (Python 3.13),
# da eseguire prima di "cdk deploy" e dopo ogni modifica di lambda/requirements.txt.
set -euo pipefail
cd "$(dirname "$0")"
PIP=${PIP:-pip}
rm -rf layer
mkdir -p layer/python
$PIP install -r lambda/requirements.txt --target layer/python \
    --implementation cp --python-version 3.13 --only-binary=:all: \
    --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64
# file non necessari a runtime
find layer/python -type d -name "__pycache__" -prune -exec rm -rf {} +
du -sh layer

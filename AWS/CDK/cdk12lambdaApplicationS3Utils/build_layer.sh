#!/bin/bash
# Crea la cartella layer/ con le librerie Python delle Lambda (openpyxl, paramiko) come wheel Linux ARM64 per
# Python 3.13 (le Lambda girano su Graviton): da eseguire prima di "cdk deploy" e dopo ogni modifica di
# lambda/requirements.txt. Non serve Docker: pip scarica le wheel gia' compilate per la piattaforma giusta.
set -euo pipefail
cd "$(dirname "$0")"
PIP=${PIP:-pip}
rm -rf layer
mkdir -p layer/python
$PIP install -r lambda/requirements.txt --target layer/python \
    --implementation cp --python-version 3.13 --only-binary=:all: \
    --platform manylinux2014_aarch64 --platform manylinux_2_17_aarch64 --platform manylinux_2_28_aarch64
# file non necessari a runtime
find layer/python -type d -name "__pycache__" -prune -exec rm -rf {} +
du -sh layer

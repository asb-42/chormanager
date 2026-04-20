#!/bin/bash
# ChorManager Starter Script
# Automatisch Virtual Environment und Dependencies einrichten

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Virtual Environment erstellen falls nicht vorhanden
if [ ! -d ".venv" ]; then
    echo "Erstelle Virtual Environment..."
    python3 -m venv .venv
    echo "Installiere Dependencies..."
    source .venv/bin/pip install -r requirements.txt
fi

# Virtual Environment aktivieren
source .venv/bin/activate

# Anwendung starten
python -m chormanager "$@"

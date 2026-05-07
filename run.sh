#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Erstelle Virtual Environment..."
    python3 -m venv .venv
fi

if [ ! -f ".venv/lib/python3*/site-packages/PyQt6/__init__.py" ] 2>/dev/null; then
    echo "Installiere Dependencies..."
    .venv/bin/pip install -r requirements.txt
fi

source .venv/bin/activate
python -m chormanager "$@"

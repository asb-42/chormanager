#!/bin/bash
# ----------------------------------------------------------------------------
# ChorManager Launcher (cross-platform, robust)
# ----------------------------------------------------------------------------
# Erkennt automatisch eine geeignete Python-Version (>= 3.9), legt bei Bedarf
# ein Virtual Environment an, installiert Dependencies und startet die App.
# ----------------------------------------------------------------------------
set -u
# Wir nutzen KEIN "set -e", weil einzelne, optionale Schritte (z. B. pip
# upgrade) nicht den gesamten Start abbrechen sollen.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- 1. Python-Detection ---------------------------------------------------
# Reihenfolge der Kandidaten: bevorzugt neuere Versionen, dann 3.9 als Minimum.
PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        # Prüfe Mindestversion (3.9)
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" 2>/dev/null; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[FEHLER] Kein passender Python-Interpreter gefunden."
    echo "         Benötigt wird Python >= 3.9."
    echo "         Installiere z. B. mit:  sudo apt install python3 python3-venv"
    exit 1
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
echo "Verwende Python $PY_VERSION ($PYTHON_BIN)"

# --- 2. venv anlegen/prüfen ------------------------------------------------
if [ ! -d ".venv" ]; then
    echo "Erstelle Virtual Environment in .venv ..."
    if ! "$PYTHON_BIN" -m venv .venv; then
        echo "[FEHLER] Konnte venv nicht erstellen."
        echo "         Unter Debian/Ubuntu:  sudo apt install python3-venv"
        exit 1
    fi
fi

# Pfade innerhalb des venv
VENV_PY=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

# Auf manchen Systemen heißen die Binaries leicht anders (FreeBSD, Alpine, ...).
if [ ! -x "$VENV_PY" ]; then
    VENV_PY="$(find .venv -maxdepth 2 -type f \( -name 'python3*' -o -name 'python' \) -executable 2>/dev/null | head -n 1)"
    if [ -z "$VENV_PY" ]; then
        echo "[FEHLER] Konnte Python-Binary im venv nicht finden."
        ls -la .venv/bin/ 2>/dev/null || true
        exit 1
    fi
fi
if [ ! -x "$VENV_PIP" ]; then
    VENV_PIP="$(find .venv -maxdepth 2 -type f -name 'pip*' -executable 2>/dev/null | head -n 1)"
fi

# --- 3. Dependencies installieren -----------------------------------------
# Wir prüfen, ob die wichtigsten Pakete bereits importierbar sind. Das ist
# deutlich robuster als ein Pfad-Glob.
NEED_INSTALL=0
if [ ! -x "$VENV_PIP" ]; then
    NEED_INSTALL=1
else
    if ! "$VENV_PY" -c "import PyQt6, yaml, reportlab" >/dev/null 2>&1; then
        NEED_INSTALL=1
    fi
fi

if [ "$NEED_INSTALL" -eq 1 ]; then
    echo "Installiere Dependencies ..."
    if [ ! -x "$VENV_PIP" ]; then
        echo "[FEHLER] pip im venv nicht gefunden. Versuche ensurepip ..."
        "$VENV_PY" -m ensurepip --upgrade || {
            echo "[FEHLER] ensurepip fehlgeschlagen."
            exit 1
        }
        VENV_PIP=".venv/bin/pip"
    fi

    # pip selbst aktualisieren (ignoriere Fehler, falls offline)
    "$VENV_PIP" install --upgrade pip >/dev/null 2>&1 || true

    if ! "$VENV_PIP" install -r requirements.txt; then
        echo "[FEHLER] Installation der Dependencies fehlgeschlagen."
        exit 1
    fi
fi

# --- 4. App starten --------------------------------------------------------
echo "Starte ChorManager ..."
exec "$VENV_PY" -m chormanager "$@"

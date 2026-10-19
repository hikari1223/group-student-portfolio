#!/usr/bin/env bash
# ============================================================
#  Group Student Portfolio - one-time setup for macOS or Linux
#
#  Run this the first time you open the project on a new computer:
#
#      chmod +x setup.sh
#      ./setup.sh
# ============================================================

set -e

echo
echo "  Setting up the Group Student Portfolio..."
echo

# --- 1. Check that Python 3 is installed --------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    echo "  [X] Python 3 was not found on this computer."
    echo
    echo "      Install Python 3.10 or newer and run this script again."
    echo
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo "  [1/4] Found $PYVER"

# --- 2. Create the virtual environment ----------------------------------
if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
    echo "  [2/4] Virtual environment already exists - skipping"
else
    echo "  [2/4] Creating the virtual environment..."
    python3 -m venv venv
fi

# --- 3. Install the packages --------------------------------------------
echo "  [3/4] Installing the packages Django needs..."
./venv/bin/python -m pip install --quiet --upgrade pip
./venv/bin/python -m pip install --quiet -r requirements.txt

# --- 4. Check that the project is healthy --------------------------------
echo "  [4/4] Checking the project..."
./venv/bin/python manage.py check
echo
echo "  All good. The project is ready."
echo
echo "  ----------------------------------------------------------"
echo "   Start the site:   ./venv/bin/python manage.py runserver"
echo "   Then open:        http://127.0.0.1:8000"
echo "  ----------------------------------------------------------"
echo

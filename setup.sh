#!/bin/bash

set -e

echo "LinkedIn Profile API - Setup"
echo "============================="
echo

echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"
echo

echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Created venv"
else
    echo "venv already exists"
fi

echo

echo "Activating virtual environment..."
source venv/bin/activate

echo

echo "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo

echo "Setting up credentials..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from template"
    echo "NOTE: You need to edit .env with your LinkedIn credentials"
else
    echo ".env already exists"
fi

chmod +x extract_credentials.py test_api.py

echo
echo "============================="
echo "Setup complete"
echo "============================="
echo
echo "Next steps:"
echo "1. python3 extract_credentials.py"
echo "2. python3 app.py"
echo
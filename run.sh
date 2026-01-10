#!/bin/bash

# The Daily Cut - Run Script

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Load environment variables if .env exists
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Get local IP for mobile access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

# Run the app
echo ""
echo "========================================"
echo "   The Daily Cut is running!"
echo "========================================"
echo ""
echo "  Desktop:  http://localhost:5001"
echo "  iPhone:   http://${LOCAL_IP}:5001"
echo ""
echo "  Tip: On iPhone, add to Home Screen"
echo "       for an app-like experience!"
echo ""
echo "  Press Ctrl+C to stop"
echo "========================================"
echo ""
python app.py

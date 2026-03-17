#!/bin/bash

# Start the web interface for 0J0 de T0GA - Sistema de Vigilancia Inteligente

echo "🚀 Starting 0J0 de T0GA..."
echo ""

cd "$(dirname "$0")"

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv"
    echo "Then: ./venv/bin/pip install -r requirements.txt"
    exit 1
fi

echo "📱 Web interface will be available at:"
echo "   Local:   http://localhost:5000"
echo "   Network: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "💡 Press Ctrl+C to stop"
echo ""

# Start the server using venv Python
cd src
../venv/bin/python web_server.py

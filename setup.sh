#!/bin/bash

# Setup script for 0J0 de T0GA - Sistema de Vigilancia Inteligente
# Creates virtual environment and installs dependencies

set -e

echo "🚀 Setting up 0J0 de T0GA..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Use venv Python directly
echo "✨ Using virtual environment..."
VENV_PYTHON="./venv/bin/python"
VENV_PIP="./venv/bin/pip"

# Upgrade pip
echo "⬆️  Upgrading pip..."
$VENV_PIP install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
$VENV_PIP install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the web interface:"
echo "  ./start.sh"
echo ""

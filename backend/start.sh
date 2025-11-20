#!/bin/bash

# Dragon Wings AI Image Generator - Backend Startup Script

set -e

echo "🐉 Dragon Wings AI Image Generator - Backend"
echo "=============================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python version: $PYTHON_VERSION"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
    echo ""
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo "✅ Dependencies installed"
echo ""

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env - please edit with your settings"
    echo ""
fi

# Create output directory
mkdir -p generated_images

echo "🚀 Starting FastAPI server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📚 API docs (Swagger): http://localhost:8000/docs"
echo ""
echo "ℹ️  Note: Model will download (~4GB) on first image generation"
echo "   This may take several minutes depending on your internet speed"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

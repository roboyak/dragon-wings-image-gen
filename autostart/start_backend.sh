#!/bin/bash
# Dragon Wings Image Generator - Backend Startup Script
# Starts FastAPI backend with Stable Diffusion

set -e

BACKEND_ROOT="/opt/dragon/apps/image_gen/current/code/backend"
VENV_PATH="/opt/dragon/apps/image_gen/backend/venv"
SHARED_DIR="/opt/dragon/apps/image_gen/shared"
LOG_DIR="/opt/dragon/logs"

echo "🐉 Starting Image Gen Backend..."

# Set environment variables for model/data locations
export HF_HOME="$SHARED_DIR/data/huggingface"
export LORA_DIR="$SHARED_DIR/data/loras"
export OUTPUT_DIR="$SHARED_DIR/data/generated_images"

# Load .env configuration
if [ -f "$SHARED_DIR/.env" ]; then
    set -a
    source "$SHARED_DIR/.env"
    set +a
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# Activate venv and start uvicorn
cd "$BACKEND_ROOT"
source "$VENV_PATH/bin/activate"

# Start FastAPI with uvicorn
nohup python3 -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  >> "$LOG_DIR/image_gen_backend.log" 2>&1 &

# Save PID
echo $! > "$LOG_DIR/image_gen_backend.pid"

echo "✅ Backend started (PID: $(cat $LOG_DIR/image_gen_backend.pid)) on port 8000"

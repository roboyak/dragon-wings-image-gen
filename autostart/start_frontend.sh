#!/bin/bash
# Dragon Wings Image Generator - Frontend Startup Script
# Starts Rails frontend

set -e

FRONTEND_ROOT="/opt/dragon/apps/image_gen/current/code/frontend"
SHARED_DIR="/opt/dragon/apps/image_gen/shared"
LOG_DIR="/opt/dragon/logs"

echo "🐉 Starting Image Gen Frontend..."

# Load RVM
if [ -f ~/.rvm/scripts/rvm ]; then
    source ~/.rvm/scripts/rvm
    rvm use 3.1.6
fi

# Set environment variables
export RAILS_ENV=production
export RAILS_SERVE_STATIC_FILES=true
export DATABASE_URL="postgresql://localhost/dragon_wings_image_gen_production"
export IMAGE_GEN_BACKEND_URL="http://localhost:8000"

# Wait for backend to be ready
echo "⏳ Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ Backend ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend not responding after 30 seconds"
        exit 1
    fi
    sleep 1
done

# PostgreSQL paths (Homebrew on Apple Silicon)
PSQL="/opt/homebrew/bin/psql"
CREATEDB="/opt/homebrew/bin/createdb"
BREW="/opt/homebrew/bin/brew"

# Link shared database.yml if it exists
if [ -f "$SHARED_DIR/database.yml" ]; then
    ln -sf "$SHARED_DIR/database.yml" "$FRONTEND_ROOT/config/database.yml"
fi

# Navigate to Rails root
cd "$FRONTEND_ROOT"

# Create database if it doesn't exist (idempotent via Rails)
echo "🔍 Creating database if needed..."
bundle exec rails db:create RAILS_ENV=production 2>/dev/null || echo "   Database already exists"

# Run database migrations
echo "Running database migrations..."
bundle exec rails db:migrate RAILS_ENV=production

# Precompile assets for production
echo "Precompiling assets..."
bundle exec rails assets:precompile RAILS_ENV=production

# Start Puma
echo "Starting Rails server..."
nohup bundle exec puma \
  -e production \
  -p 3000 \
  -C config/puma.rb \
  >> "$LOG_DIR/image_gen_frontend.log" 2>&1 &

# Save PID
echo $! > "$LOG_DIR/image_gen_frontend.pid"

echo "✅ Frontend started (PID: $(cat $LOG_DIR/image_gen_frontend.pid)) on port 3000"

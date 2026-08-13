#!/usr/bin/env bash
# run_prod.sh - Production runner for LinguaSight on macOS/Linux

set -e

echo "=== LinguaSight Production Server ==="
echo ""

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-2}"

# Validate environment
if [ ! -f .env ]; then
    echo "WARNING: .env file not found. Using default configuration."
fi

# Check if frontend is built
if [ ! -d "frontend/dist" ]; then
    echo "Frontend not built. Building now..."
    cd frontend
    npm run build
    cd ..
fi

echo "Starting production server with gunicorn..."
echo "Server: http://localhost:$PORT"
echo ""

gunicorn app.main:app \
    --workers $WORKERS \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "$HOST:$PORT" \
    --timeout 120 \
    --keep-alive 5 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log

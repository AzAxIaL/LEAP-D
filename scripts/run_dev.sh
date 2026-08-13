#!/usr/bin/env bash
# run_dev.sh - Development runner for LinguaSight on macOS/Linux

set -e

echo "=== LinguaSight Development Runner ==="
echo ""

# Load environment variables from .env
if [ -f .env ]; then
    echo "Loading environment from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo "All servers stopped."
}

trap cleanup EXIT

# Start backend
echo "Starting backend server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend starting on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""

# Wait for backend to start
sleep 2

# Start frontend
echo "Starting frontend dev server..."
cd frontend
VITE_API_URL="${VITE_API_URL:-http://localhost:8000}" npm run dev &
FRONTEND_PID=$!
cd ..
echo "Frontend starting on http://localhost:3000"
echo ""

echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for processes
wait

#!/usr/bin/env bash
# setup.sh - Setup script for LinguaSight on macOS/Linux

set -e

echo "=== LinguaSight Setup Script ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
REQUIRED_VERSION="3.11"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo -e "${RED}Error: Python 3.11+ required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Check Node.js version
echo "Checking Node.js version..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js not found${NC}"
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2)
REQUIRED_NODE="18"

if [[ "$(printf '%s\n' "$REQUIRED_NODE" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_NODE" ]]; then
    echo -e "${RED}Error: Node.js 18+ required (found $NODE_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"

# Check FFmpeg
echo "Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}Warning: FFmpeg not found. Install with:${NC}"
    echo "  macOS: brew install ffmpeg"
    echo "  Linux: sudo apt install ffmpeg"
else
    echo -e "${GREEN}✓ FFmpeg found${NC}"
fi

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Node.js dependencies
echo ""
echo "Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head

# Create data directories
echo "Creating data directories..."
mkdir -p data/audio data/processed data/voiceprints data/artifacts data/reports logs

echo ""
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "To start the application:"
echo "  Backend:  source venv/bin/activate && uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or use: ./scripts/run_dev.sh"

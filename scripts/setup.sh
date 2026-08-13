#!/usr/bin/env bash
# setup.sh - Setup script for LEAP-D on macOS/Linux
# Longitudinal ESL Assessment of Proficiency and Disfluency

set -e

echo "=== LEAP-D Setup Script ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
if python3 --version | grep -qE "Python 3\.1[1-9]|Python 3\.[2-9][0-9]"; then
    echo -e "${GREEN}✓ Python found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python 3.11+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

# Check uv
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}✗ uv not found. Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
else
    UV_VERSION=$(uv --version)
    echo -e "${GREEN}✓ uv found: $UV_VERSION${NC}"
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}✗ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
if node --version | grep -qE "v1[8-9]|v[2-9][0-9]"; then
    echo -e "${GREEN}✓ Node.js found: $NODE_VERSION${NC}"
else
    echo -e "${RED}✗ Node.js 18+ required. Found: $NODE_VERSION${NC}"
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠ FFmpeg not found. Audio processing will be limited.${NC}"
    echo -e "${CYAN}  Install via: brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)${NC}"
else
    FFMPEG_VERSION=$(ffmpeg -version | head -n 1)
    echo -e "${GREEN}✓ FFmpeg found: $FFMPEG_VERSION${NC}"
fi

# Create virtual environment with uv
echo -e "${YELLOW}[2/6] Creating virtual environment with uv...${NC}"
uv venv .venv

# Activate virtual environment
echo -e "${YELLOW}[3/6] Activating virtual environment...${NC}"
source .venv/bin/activate

# Install backend dependencies
echo -e "${YELLOW}[4/6] Installing backend dependencies...${NC}"
uv pip install -e ".[asr,diarization,dev]"

# Install frontend dependencies
echo -e "${YELLOW}[5/6] Installing frontend dependencies...${NC}"
cd frontend
npm install
cd ..

# Initialize database
echo -e "${YELLOW}[6/6] Initializing database...${NC}"
alembic upgrade head

# Copy environment file
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from .env.example${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

echo -e "\n${GREEN}=== Setup Complete! ===${NC}"
echo -e "\n${CYAN}To run LEAP-D:${NC}"
echo -e "  Backend:  source .venv/bin/activate && uvicorn backend.app.main:app --reload"
echo -e "  Frontend: cd frontend && npm run dev"
echo -e "\nThen open http://localhost:5173 in your browser.${NC}"

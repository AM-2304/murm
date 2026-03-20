#!/usr/bin/env bash
# MURM Local Setup Script
# Run this once after cloning the repository.
# Usage: bash setup_local.sh

set -e  # Stop immediately if any command fails

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

echo ""
echo -e "${BOLD}MURM Local Setup${RESET}"
echo "************************************"

# Check Python version
echo ""
echo -e "${BOLD}Step 1: Checking Python version...${RESET}"
PYTHON=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED="3.11"
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
    echo -e "${GREEN}  Python $PYTHON found${RESET}"
else
    echo -e "${RED}  Python 3.11 or higher is required. You have $PYTHON${RESET}"
    echo "  Download from: https://python.org/downloads"
    exit 1
fi

# Check for .env file
echo ""
echo -e "${BOLD}Step 2: Checking configuration...${RESET}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}  No .env file found. Creating from example...${RESET}"
    cp .env.example .env
    echo ""
    echo -e "${RED}  ACTION REQUIRED:${RESET}"
    echo "  Open the .env file and replace 'your_api_key_here' with your actual API key."
    echo ""
    echo "  Provider options:"
    echo "    Groq:                console.groq.com"
    echo "    OpenAI:              platform.openai.com"
    echo "    Anthropic:           console.anthropic.com"
    echo ""
    echo "  Then run this script again."
    echo ""
    echo "  See .env.groq, .env.openai, or .env.anthropic for filled examples."
    exit 0
else
    echo -e "${GREEN}  .env file found${RESET}"
fi

# Check that the API key has been filled in
if grep -q "your_api_key_here" .env; then
    echo -e "${RED}  .env still contains placeholder values. Please fill in your API key.${RESET}"
    exit 1
fi

# Create virtual environment
echo ""
echo -e "${BOLD}Step 3: Creating Python virtual environment...${RESET}"
if [ ! -d "murm" ]; then
    python3 -m venv murm
    echo -e "${GREEN}  Virtual environment created at murm/${RESET}"
else
    echo -e "${GREEN}  Virtual environment already exists${RESET}"
fi

# Activate it
source murm/bin/activate
echo -e "${GREEN}  Virtual environment activated${RESET}"

# Install the package
echo ""
echo -e "${BOLD}Step 4: Installing MURM and dependencies...${RESET}"
echo "  (This downloads about 500MB of libraries on first install)"
pip install -e . --quiet
echo -e "${GREEN}  Installation complete${RESET}"

# Run tests
echo ""
echo -e "${BOLD}Step 5: Running test suite (no API key needed)...${RESET}"
python -m pytest tests/test_core.py -q
echo -e "${GREEN}  All tests passed${RESET}"

# Create data directories
echo ""
echo -e "${BOLD}Step 6: Creating data directories...${RESET}"
mkdir -p data/projects data/simulations data/chroma
echo -e "${GREEN}  data/ directories ready${RESET}"

# Frontend setup
echo ""
echo -e "${BOLD}Step 7: Frontend setup (optional)...${RESET}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}  Node.js $NODE_VERSION found${RESET}"
    echo "  Installing frontend dependencies..."
    cd frontend && npm install --silent && cd ..
    echo -e "${GREEN}  Frontend ready${RESET}"
else
    echo -e "${YELLOW}  Node.js not found — skipping frontend install${RESET}"
    echo "  You can still use the CLI and API without the frontend."
    echo "  To install Node.js: https://nodejs.org (download LTS version)"
fi

# ---- Done ----
echo ""
echo "************************************"
echo -e "${GREEN}${BOLD}Setup complete.${RESET}"
echo ""
echo "To start MURM:"
echo ""
echo "  Option A — API server only (use with curl or Postman):"
echo "    source .venv/bin/activate"
echo "    murm serve"
echo "    Then open: http://localhost:8000/docs"
echo ""
echo "  Option B — API server + frontend (full UI):"
echo "    Terminal 1: source .venv/bin/activate && murm serve"
echo "    Terminal 2: cd frontend && npm run dev"
echo "    Then open: http://localhost:3000"
echo ""
echo "  Option C — Command line, no server needed:"
echo "    source .venv/bin/activate"
echo "    murm run --seed-text 'paste your document here' \\"
echo "                   --question 'What happens next?' \\"
echo "                   --agents 20 --rounds 15 --output report.md"
echo ""
echo "  Cost estimate before running:"
echo "    murm estimate --agents 20 --rounds 15"
echo ""
echo "************************************"

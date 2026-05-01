#!/bin/bash
# Starts the backend, frontend, and Ollama LLM together.
# Press Ctrl+C to stop everything.

set -e
cd "$(dirname "$0")"

OLLAMA_PID=""

# ── Virtual environment ───────────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment (python3.12)..."
    python3.12 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt -q
fi

# ── Frontend dependencies ─────────────────────────────────────────────────────
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd frontend && npm install --silent)
fi

# ── Ollama ────────────────────────────────────────────────────────────────────
if command -v ollama &>/dev/null; then
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo "  Ollama already running."
    else
        echo "  Starting Ollama..."
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        # Wait up to 8s for it to be ready
        for i in $(seq 1 8); do
            sleep 1
            curl -s http://localhost:11434/api/tags &>/dev/null && break
        done
    fi

    # Pull llama3 if not already downloaded
    if ! ollama list 2>/dev/null | grep -q "llama3"; then
        echo "  Pulling llama3 model (first-time only, may take a few minutes)..."
        ollama pull llama3
    fi
else
    echo "  Ollama not installed — AI features will use template fallback."
    echo "  Install from https://ollama.com to enable LLM parsing and generation."
fi

# ── Cleanup on Ctrl+C ────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$BACKEND_PID" 2>/dev/null
    kill "$FRONTEND_PID" 2>/dev/null
    [ -n "$OLLAMA_PID" ] && kill "$OLLAMA_PID" 2>/dev/null
    wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

echo ""
echo "  Backend  →  http://localhost:8080"
echo "  Frontend →  http://localhost:5173"
[ -n "$OLLAMA_PID" ] && echo "  Ollama   →  http://localhost:11434"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

# ── Start servers ─────────────────────────────────────────────────────────────
python main.py &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"

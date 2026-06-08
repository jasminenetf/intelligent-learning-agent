#!/bin/bash
# Intelligent Learning Agent — one-click launcher
# Usage: bash scripts/start_app.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "============================================"
echo "  Intelligent Learning Agent — Starting..."
echo "============================================"

# Check venv
if [ ! -f "$ROOT/.venv/bin/activate" ]; then
    echo "ERROR: .venv not found"
    exit 1
fi

source "$ROOT/.venv/bin/activate"

# Kill existing
fuser -k 8010/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# Backend
echo "[1/2] Backend http://127.0.0.1:8010"
cd "$ROOT/backend"
python -m uvicorn app.demo_main:app --host 127.0.0.1 --port 8010 &
BACKEND_PID=$!
echo "       PID: $BACKEND_PID"

# Frontend
echo "[2/2] Frontend http://127.0.0.1:5173"
cd "$ROOT/frontend-demo"
python -m http.server 5173 &
FRONTEND_PID=$!
echo "       PID: $FRONTEND_PID"

sleep 3

if command -v curl &>/dev/null; then
    curl -fsS http://127.0.0.1:8010/health >/dev/null || {
        echo "ERROR: backend health check failed. See backend process $BACKEND_PID."
        exit 1
    }
fi

# Auto-open browser (WSL -> Windows)
if command -v powershell.exe &>/dev/null; then
    powershell.exe -NoProfile -Command "Start-Process 'http://127.0.0.1:5173'" >/dev/null 2>&1 && echo "Browser opened" || true
elif command -v xdg-open &>/dev/null; then
    xdg-open http://127.0.0.1:5173 2>/dev/null || true
elif command -v open &>/dev/null; then
    open http://127.0.0.1:5173 2>/dev/null || true
fi

echo ""
echo "============================================"
echo "  System ready"
echo "  http://127.0.0.1:5173"
echo "  Backend: http://127.0.0.1:8010"
echo "  Press Ctrl+C to stop"
echo "============================================"
echo ""

wait

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "============================================"
echo " E2E Browser Smoke Test"
echo "============================================"

# ── 1. Stop old services ──
echo "[1/6] Stopping old services..."
bash scripts/stop_app.sh 2>/dev/null || true
sleep 1

# ── 2. Start backend ──
echo "[2/6] Starting backend..."
cd backend
source .env 2>/dev/null || true
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
cd "$ROOT"
echo "  Backend PID: $BACKEND_PID"

# ── 3. Start frontend ──
echo "[3/6] Starting frontend..."
cd frontend-demo
python3 -m http.server 5173 &
FRONTEND_PID=$!
cd "$ROOT"
echo "  Frontend PID: $FRONTEND_PID"

# ── 4. Wait for services ──
echo "[4/6] Waiting for services..."
for i in $(seq 1 30); do
  if curl -s -o /dev/null http://127.0.0.1:8000/health 2>/dev/null; then
    echo "  Backend OK"
    break
  fi
  sleep 1
done

for i in $(seq 1 30); do
  if curl -s -o /dev/null -I http://127.0.0.1:5173 2>/dev/null; then
    echo "  Frontend OK"
    break
  fi
  sleep 1
done

# ── 5. Install Playwright ──
echo "[5/6] Installing Playwright..."
cd tests/e2e
npm install --silent 2>&1 | tail -1
npx playwright install chromium 2>&1 | tail -3
cd "$ROOT"

# ── 6. Run tests ──
echo "[6/6] Running E2E tests..."
cd tests/e2e
npx playwright test demo-auto-flow.spec.js 2>&1
TEST_RESULT=$?
cd "$ROOT"

echo ""
echo "============================================"
if [ $TEST_RESULT -eq 0 ]; then
  echo "✅ E2E TESTS PASSED"
else
  echo "❌ E2E TESTS FAILED (exit code: $TEST_RESULT)"
fi
echo "============================================"

# Cleanup
kill $BACKEND_PID 2>/dev/null || true
kill $FRONTEND_PID 2>/dev/null || true

echo "Report: tests/e2e/playwright-report/index.html"
exit $TEST_RESULT

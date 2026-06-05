#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "============================================"
echo " Claude Code Quality Gate"
echo "============================================"

PASS=0
FAIL=0

# ── 1. .env safety ──
echo ""
echo "[1/4] Checking .env safety..."
git check-ignore -v backend/.env || true
if git ls-files backend/.env 2>/dev/null | grep -q "backend/.env"; then
  echo "  ❌ FAIL: backend/.env is tracked by git!"
  FAIL=$((FAIL + 1))
else
  echo "  ✅ PASS: backend/.env is gitignored"
  PASS=$((PASS + 1))
fi

# ── 2. Python compile check ──
echo ""
echo "[2/4] Python compile check..."
if python3 -m compileall backend/app 2>&1 | tail -1; then
  echo "  ✅ PASS: Python compile OK"
  PASS=$((PASS + 1))
else
  echo "  ❌ FAIL: Python compile errors"
  FAIL=$((FAIL + 1))
fi

# ── 3. JS syntax check ──
echo ""
echo "[3/4] JS syntax check..."
if node --check frontend-demo/app.js 2>&1; then
  echo "  ✅ PASS: JS syntax OK"
  PASS=$((PASS + 1))
else
  echo "  ❌ FAIL: JS syntax errors"
  FAIL=$((FAIL + 1))
fi

# ── 4. Optional E2E ──
echo ""
echo "[4/4] Optional E2E..."
if [ -f scripts/e2e_browser_smoke.sh ]; then
  echo "  ℹ️  E2E script exists: bash scripts/e2e_browser_smoke.sh"
  echo "  (optional — not enforced in this phase)"
else
  echo "  ℹ️  E2E script not found yet"
fi

# ── Summary ──
echo ""
echo "============================================"
echo " Results: $PASS passed, $FAIL failed"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
  echo "❌ QUALITY GATE FAILED"
  exit 1
else
  echo "✅ QUALITY GATE PASSED"
  exit 0
fi

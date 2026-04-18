#!/usr/bin/env bash
# ops/check.sh — Run all code quality checks
# Usage: ./ops/check.sh [--fix]
set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKSPACE"

FIX="${1:-}"
ERRORS=0

# ── Ruff lint ────────────────────────────────────────────────────────────────
echo "🔍 [1/3] Ruff lint..."
if [[ "$FIX" == "--fix" ]]; then
    ruff check --fix . && echo "   ✅ Ruff lint passed (with auto-fix)" || { echo "   ❌ Ruff lint failed"; ERRORS=$((ERRORS+1)); }
else
    ruff check . && echo "   ✅ Ruff lint passed" || { echo "   ❌ Ruff lint failed (run with --fix to auto-fix)"; ERRORS=$((ERRORS+1)); }
fi

# ── Ruff format ──────────────────────────────────────────────────────────────
echo ""
echo "🎨 [2/3] Ruff format..."
if [[ "$FIX" == "--fix" ]]; then
    ruff format . && echo "   ✅ Ruff format applied"
else
    ruff format --check . && echo "   ✅ Ruff format clean" || { echo "   ❌ Formatting issues found (run with --fix to auto-format)"; ERRORS=$((ERRORS+1)); }
fi

# ── Mypy ─────────────────────────────────────────────────────────────────────
echo ""
echo "🔬 [3/3] Mypy type check (core/ only)..."
if command -v mypy &> /dev/null; then
    mypy core/ && echo "   ✅ Mypy passed" || { echo "   ❌ Mypy found type errors"; ERRORS=$((ERRORS+1)); }
else
    echo "   ⚠️  mypy not installed — skipping (pip install mypy)"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$ERRORS" -eq 0 ]]; then
    echo "✅  All checks passed"
else
    echo "❌  $ERRORS check(s) failed"
    exit 1
fi

#!/usr/bin/env bash
# ops/check.sh — Global monorepo quality gate
# Scans: open-claw-sandbox/ (Python) + infra/pipelines/ (Python) + infra/scripts/ (Shell)
# Usage: ./ops/check.sh [--fix]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

FIX="${1:-}"
ERRORS=0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Open Claw — Global Quality Gate"
echo "  Root: $REPO_ROOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── 1. Sandbox Python checks (delegates to sandbox's own check.sh) ────────────
echo "📦 [1/4] Sandbox checks (open-claw-sandbox/)..."
if [[ -x "open-claw-sandbox/ops/check.sh" ]]; then
    open-claw-sandbox/ops/check.sh ${FIX:+--fix} && echo "   ✅ Sandbox checks passed" || {
        echo "   ❌ Sandbox checks failed"
        ERRORS=$((ERRORS+1))
    }
else
    echo "   ⚠️  open-claw-sandbox/ops/check.sh not found — skipping"
fi

echo ""

# ── 2. infra/pipelines/ Python checks ────────────────────────────────────────
echo "🔍 [2/4] Ruff lint on infra/pipelines/..."
if command -v ruff &>/dev/null; then
    if [[ "$FIX" == "--fix" ]]; then
        ruff check --fix infra/pipelines/ && echo "   ✅ Ruff lint passed (with auto-fix)" || {
            echo "   ❌ Ruff lint failed"
            ERRORS=$((ERRORS+1))
        }
    else
        ruff check infra/pipelines/ && echo "   ✅ Ruff lint passed" || {
            echo "   ❌ Ruff lint failed (run with --fix to auto-fix)"
            ERRORS=$((ERRORS+1))
        }
    fi
else
    echo "   ⚠️  ruff not installed — skipping (pip install ruff)"
fi

echo ""

# ── 3. Shell script checks ────────────────────────────────────────────────────
echo "🐚 [3/4] Shell script check (shellcheck)..."
if command -v shellcheck &>/dev/null; then
    SHELL_ERRORS=0
    for script in infra/scripts/*.sh open-claw-sandbox/ops/*.sh; do
        [[ -f "$script" ]] || continue
        shellcheck "$script" && echo "   ✅ $script" || {
            echo "   ❌ $script failed shellcheck"
            SHELL_ERRORS=$((SHELL_ERRORS+1))
        }
    done
    if [[ "$SHELL_ERRORS" -gt 0 ]]; then
        ERRORS=$((ERRORS+1))
    fi
else
    echo "   ⚠️  shellcheck not installed — skipping (brew install shellcheck)"
fi

echo ""

# ── 4. .env check (no real secrets committed) ────────────────────────────────
echo "🔐 [4/4] Checking for accidental credential commits..."
if git grep -l 'API_KEY=\S\+\|SECRET=\S\+\|PASSWORD=\S\+' -- '*.yaml' '*.yml' '*.toml' '*.py' '*.sh' 2>/dev/null | grep -v '.env.example'; then
    echo "   ❌ Possible credentials found in tracked files!"
    ERRORS=$((ERRORS+1))
else
    echo "   ✅ No credential patterns found in tracked files"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$ERRORS" -eq 0 ]]; then
    echo "✅  All global checks passed"
else
    echo "❌  $ERRORS check(s) failed"
    exit 1
fi

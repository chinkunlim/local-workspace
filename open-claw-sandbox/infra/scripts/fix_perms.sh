#!/usr/bin/env bash
#
# fix_perms.sh — Global Self-Healing Permission Fixer
# ===================================================
# Ensures all shell scripts in the workspace have executable permissions.
# This prevents CI/CD pipeline failures and automated daemon launch issues.

echo "🔧 執行環境自癒：修復腳本執行權限..."

# Get the workspace root
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Find all .sh files and make them executable
find "${WORKSPACE_DIR}" -type f -name "*.sh" -exec chmod +x {} +

echo "✅ 權限修復完成。所有 .sh 腳本皆具備執行權限。"

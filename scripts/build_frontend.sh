#!/usr/bin/env bash
# 프론트엔드 빌드 스크립트
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")/frontend"

echo "=== Frontend Build ==="
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo "Building..."
npx vite build

echo ""
echo "Build complete: $FRONTEND_DIR/dist/"
ls -lh "$FRONTEND_DIR/dist/" 2>/dev/null || dir "$FRONTEND_DIR/dist/"

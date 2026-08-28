#!/usr/bin/env bash
# Render build script (native runtime alternative to Docker)
set -e

echo "==> Installing Python dependencies..."
pip install .

echo "==> Building frontend..."
cd frontend
npm ci --ignore-scripts
npm run build
cd ..

echo "==> Build complete."

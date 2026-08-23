#!/usr/bin/env bash
# Start backend (API) and frontend (Vite dev server) in parallel.
# Usage: bash start.sh
# Stop:  Ctrl+C (kills both processes)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# JWT secret — required for auth; use a default for local dev
export TCG_JWT_SECRET="${TCG_JWT_SECRET:-dev-secret-change-in-production}"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACK_PID $FRONT_PID 2>/dev/null
  wait $BACK_PID $FRONT_PID 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM

# Seed exchange rates (USD/BRL) — needed for currency conversion
echo "Seeding exchange rates (last 90 days)..."
cd "$SCRIPT_DIR"
python -m src.cli.main update-exchange-rate --backfill-days 90 || echo "Warning: exchange rate seeding failed (network issue?). Continuing..."

# Backend — FastAPI on port 8000
echo "Starting backend on http://localhost:8000 ..."
python -m src.cli.main serve --host 0.0.0.0 --port 8000 &
BACK_PID=$!

# Frontend — Vite dev server on port 5173
echo "Starting frontend on http://localhost:5173 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONT_PID=$!

echo ""
echo "Backend  -> http://localhost:8000"
echo "Frontend -> http://localhost:5173"
echo "Press Ctrl+C to stop both."

wait

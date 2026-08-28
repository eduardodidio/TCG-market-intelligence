#!/usr/bin/env bash
# Render start script
set -e

# Seed exchange rates (best-effort, non-blocking)
echo "==> Seeding exchange rates..."
python -m src.cli.main update-exchange-rate --backfill-days 30 || echo "Warning: exchange rate seeding failed. Continuing..."

# Seed admin user (best-effort)
echo "==> Seeding users..."
python -m src.cli.main seed-users || echo "Warning: user seeding failed. Continuing..."

# Start API server
echo "==> Starting TEDHC Market API on port ${PORT:-8000}..."
exec uvicorn src.api.app:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"

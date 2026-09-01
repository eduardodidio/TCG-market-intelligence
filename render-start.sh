#!/usr/bin/env bash
# Render entrypoint: restore DB from R2 via Litestream, then start app with replication
set -e

if [ -n "$LITESTREAM_REPLICA_BUCKET" ]; then
  echo "==> Restoring database from R2 (if backup exists)..."
  litestream restore -if-replica-exists -config /app/litestream.yml /data/tcg_market.db || echo "Warning: Litestream restore failed or no backup found. Starting fresh."

  echo "==> Starting with Litestream replication..."
  exec litestream replicate -exec "sh /app/render-start-app.sh" -config /app/litestream.yml
else
  echo "==> No LITESTREAM_REPLICA_BUCKET set, starting without replication..."
  exec sh /app/render-start-app.sh
fi

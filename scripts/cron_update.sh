#!/usr/bin/env bash
# =============================================================================
# cron_update.sh — Trigger daily price collection via the TCG Market API
# =============================================================================
#
# This script calls the /api/v1/collect/update endpoint, logs the result,
# and exits with an appropriate status code for use in cron jobs or
# scheduled tasks.
#
# ENVIRONMENT VARIABLES:
#   TCG_API_KEY   (required) — API key for authentication
#   TCG_API_URL   (optional) — Base URL of the API (default: http://localhost:8000)
#   TCG_LOG_DIR   (optional) — Directory to write log files (default: logs/cron)
#
# USAGE:
#   TCG_API_KEY=your_key bash scripts/cron_update.sh
#
# SCHEDULING:
#
# Linux/Mac — run daily at 03:00:
#   0 3 * * * TCG_API_KEY=your_key /path/to/scripts/cron_update.sh
#
# Windows (Git Bash + Task Scheduler):
#   Action: "C:\Program Files\Git\bin\bash.exe"
#   Arguments: -c "TCG_API_KEY=your_key /c/Workspace/TCG-market-intelligence/scripts/cron_update.sh"
#   Trigger: Daily at 03:00
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
: "${TCG_API_KEY:?ERROR: TCG_API_KEY must be set}"
TCG_API_URL="${TCG_API_URL:-http://localhost:8000}"
TCG_LOG_DIR="${TCG_LOG_DIR:-logs/cron}"

# Resolve log dir relative to project root if not absolute
if [[ "${TCG_LOG_DIR}" != /* ]]; then
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
    TCG_LOG_DIR="${PROJECT_ROOT}/${TCG_LOG_DIR}"
fi

# ---------------------------------------------------------------------------
# Temp file for response body — cleaned up on exit
# ---------------------------------------------------------------------------
TMPFILE="$(mktemp)"
trap 'rm -f "${TMPFILE}"' EXIT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() {
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[${timestamp}] $*"
}

# Ensure log directory exists
mkdir -p "${TCG_LOG_DIR}"

LOG_FILE="${TCG_LOG_DIR}/cron_update_$(date '+%Y-%m-%d').log"

# ---------------------------------------------------------------------------
# Call POST /api/v1/collect/update
# ---------------------------------------------------------------------------
log "Starting price update via ${TCG_API_URL}/api/v1/collect/update" | tee -a "${LOG_FILE}"

HTTP_STATUS=$(curl -s -o "${TMPFILE}" -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: ${TCG_API_KEY}" \
    -d '{}' \
    "${TCG_API_URL}/api/v1/collect/update" \
    2>&1) || {
    log "ERROR: curl failed to connect to ${TCG_API_URL}" | tee -a "${LOG_FILE}"
    exit 2
}

RESPONSE_BODY="$(cat "${TMPFILE}")"

log "Update response — HTTP ${HTTP_STATUS}: ${RESPONSE_BODY}" | tee -a "${LOG_FILE}"

# ---------------------------------------------------------------------------
# Call GET /api/v1/collect/health (optional health check after update)
# ---------------------------------------------------------------------------
HEALTH_STATUS=$(curl -s -o "${TMPFILE}" -w "%{http_code}" \
    -H "Accept: application/json" \
    "${TCG_API_URL}/api/v1/collect/health" \
    2>&1) || true

if [ -n "${HEALTH_STATUS}" ] && [ "${HEALTH_STATUS}" != "000" ]; then
    HEALTH_BODY="$(cat "${TMPFILE}")"
    log "Health check — HTTP ${HEALTH_STATUS}: ${HEALTH_BODY}" | tee -a "${LOG_FILE}"
else
    log "Health check — skipped (endpoint unreachable)" | tee -a "${LOG_FILE}"
fi

# ---------------------------------------------------------------------------
# Exit with appropriate code
# ---------------------------------------------------------------------------
if [ "${HTTP_STATUS}" = "200" ]; then
    log "Update completed successfully." | tee -a "${LOG_FILE}"
    exit 0
else
    log "ERROR: Update failed with HTTP ${HTTP_STATUS}." | tee -a "${LOG_FILE}"
    exit 1
fi

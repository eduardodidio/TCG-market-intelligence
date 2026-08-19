#!/usr/bin/env bash
# =============================================================================
# expand_collection.sh — Backfill popular Magic sets from MYP Cards
# =============================================================================
#
# This script runs the backfill CLI command for several popular Magic: The
# Gathering sets beyond the initial DMR (Dominaria Remastered) collection.
#
# USAGE:
#   cd <project-root>
#   bash scripts/expand_collection.sh
#
# PREREQUISITES:
#   - Virtual environment set up:  make setup
#   - Database exists (or will be created on first run)
#
# RUNTIME:
#   Each set takes roughly 10-30 minutes depending on card count and rate
#   limiting. Total expected runtime: 1-3 hours for all sets below.
#
# RESUME SAFETY:
#   The backfill command has built-in resume support (enabled by default).
#   If the script is interrupted (Ctrl+C, network drop, etc.), simply re-run
#   it. Cards that already have observations in the database will be skipped
#   automatically. INSERT ON CONFLICT DO NOTHING ensures no duplicate data.
#
# RATE LIMITING:
#   - 1 second delay between requests (default)
#   - Max 3 concurrent card fetches (asyncio.Semaphore)
#   - Automatic retry with exponential backoff on 429/403
#
# SLUG FORMAT:
#   MYP Cards uses lowercase, hyphenated English set names as URL slugs.
#   Example: "dominaria-remastered" -> https://mypcards.com/magic/dominaria-remastered
#   The slugs below were chosen based on popular/recent sets likely to have
#   active price movement. If a slug does not exist on MYP, the backfill
#   will fail gracefully for that set and continue to the next one.
# =============================================================================

set -euo pipefail

# Change to project root (one level up from scripts/)
cd "$(dirname "$0")/.."

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
    # Windows Git Bash / MSYS2
    source .venv/Scripts/activate
fi

# ---------------------------------------------------------------------------
# Popular Magic sets to collect
# ---------------------------------------------------------------------------
# Each slug corresponds to https://mypcards.com/magic/<slug>
#
# To discover all available slugs, run:
#   python -m src.cli.main backfill --dry-run
# or check https://mypcards.com/magic/edicoes
SETS=(
    "foundations"                                # FDN — current Standard staple set
    "duskmourn-house-of-horror"                   # DSK — recent Standard set
    "modern-horizons-3"                          # MH3 — high-value Modern set
    "outlaws-of-thunder-junction"                # OTJ — recent Standard
    "murders-at-karlov-manor"                    # MKM — recent Standard
    "the-lord-of-the-rings-tales-of-middle-earth" # LTR — popular crossover set
    "march-of-the-machine"                       # MOM — popular Standard set
)

echo "============================================================"
echo "  TCG Market Intelligence — Collection Expansion"
echo "  Sets to process: ${#SETS[@]}"
echo "============================================================"
echo ""

FAILED_SETS=()
SUCCEEDED=0

for slug in "${SETS[@]}"; do
    echo "------------------------------------------------------------"
    echo "  Backfilling set: ${slug}"
    echo "  Started at: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "------------------------------------------------------------"

    if python -m src.cli.main backfill --set "${slug}"; then
        SUCCEEDED=$((SUCCEEDED + 1))
        echo ""
        echo "  [OK] ${slug} completed successfully."
    else
        FAILED_SETS+=("${slug}")
        echo ""
        echo "  [WARN] ${slug} finished with errors (see log above)."
        echo "         You can retry later with: python -m src.cli.main backfill --set ${slug}"
    fi

    echo ""
done

echo "============================================================"
echo "  Collection Expansion Summary"
echo "  Succeeded: ${SUCCEEDED} / ${#SETS[@]}"
if [ ${#FAILED_SETS[@]} -gt 0 ]; then
    echo "  Failed:    ${FAILED_SETS[*]}"
fi
echo "============================================================"
echo ""
echo "Verify results:"
echo "  curl http://localhost:8000/api/v1/sets"
echo "  curl http://localhost:8000/api/v1/market/stats"
echo "  python -m src.cli.main analyze list"

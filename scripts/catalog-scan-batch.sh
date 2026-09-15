#!/usr/bin/env bash
# =============================================================
# Catalog Liga Price Scan — Batch Script
# Run sets sequentially with Liga price scanning
# Usage: bash scripts/catalog-scan-batch.sh
# =============================================================

set -e
cd "$(dirname "$0")/.."

CLI="python -m src.cli.main"

# Sets already scanned (2026-09-04):
#   mh3 (524 cards, 489 priced)
#   fdn (770 cards, 770 priced)
#   cmm (1067 cards, 1067 priced)

# --- Priority 1: Large sets (500+ cards) ---
SETS_P1=(
  "plst"   # 5579 cards — The List (reprints)
  "sld"    # 2726 cards — Secret Lair Drop
  "who"    # 1178 cards — Doctor Who
  "pip"    # 1068 cards — Fallout
  "clb"    # 936 cards  — Commander Legends: Baldur's Gate
  "msc"    # 866 cards  — Miscellaneous
  "ltr"    # 858 cards  — Lord of the Rings
  "j22"    # 835 cards  — Jumpstart 2022
)

# --- Priority 2: Popular Standard/Modern sets (300-700 cards) ---
SETS_P2=(
  "dsk"    # Duskmourn
  "blb"    # Bloomburrow
  "otj"    # Outlaws of Thunder Junction
  "mkm"    # Murders at Karlov Manor
  "lci"    # Lost Caverns of Ixalan
  "woe"    # Wilds of Eldraine
  "mom"    # March of the Machine
  "one"    # Phyrexia: All Will Be One
  "bro"    # Brothers' War
  "dmu"    # Dominaria United
  "snc"    # Streets of New Capenna
  "neo"    # Kamigawa: Neon Dynasty
  "vow"    # Crimson Vow
  "mid"    # Midnight Hunt
  "afr"    # Adventures in Forgotten Realms
  "stx"    # Strixhaven
  "khm"    # Kaldheim
  "znr"    # Zendikar Rising
  "m21"    # Core Set 2021
  "iko"    # Ikoria
  "thb"    # Theros Beyond Death
  "eld"    # Throne of Eldraine
  "2xm"   # Double Masters
  "2x2"   # Double Masters 2022
  "mh2"   # Modern Horizons 2
  "mh1"   # Modern Horizons 1
)

echo "============================================"
echo "  CATALOG LIGA SCAN — BATCH"
echo "  Started: $(date)"
echo "============================================"

scan_set() {
  local code=$1
  echo ""
  echo "--- Scanning set: $code ($(date)) ---"
  $CLI catalog scan --set "$code" --delay 5 --batch-size 20 --batch-pause 60
  echo "--- Done: $code ($(date)) ---"
}

echo ""
echo "=== PRIORITY 1: Large sets ==="
for s in "${SETS_P1[@]}"; do
  scan_set "$s"
done

echo ""
echo "=== PRIORITY 2: Standard/Modern sets ==="
for s in "${SETS_P2[@]}"; do
  scan_set "$s"
done

echo ""
echo "============================================"
echo "  BATCH COMPLETE: $(date)"
echo "============================================"
$CLI catalog stats

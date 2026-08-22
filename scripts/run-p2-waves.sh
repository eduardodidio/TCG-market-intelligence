#!/usr/bin/env bash
# =============================================================================
# P2 Market Intelligence — Parallel Execution Script
# =============================================================================
# Executes 13 features (F32-F44) in 4 orchestration waves.
# Within each wave, features run in parallel via separate claude sessions.
# Waves are sequential (deps must be satisfied before next wave starts).
#
# Usage:
#   ./scripts/run-p2-waves.sh [wave_number]
#
# Examples:
#   ./scripts/run-p2-waves.sh        # Run ALL waves sequentially (0→3)
#   ./scripts/run-p2-waves.sh 0      # Run only Wave 0
#   ./scripts/run-p2-waves.sh 2      # Run only Wave 2 (assumes 0+1 done)
# =============================================================================

set -euo pipefail

LOGDIR="logs/p2-execution"
mkdir -p "$LOGDIR"

run_feature() {
  local fid="$1"
  local desc="$2"
  local logfile="$LOGDIR/${fid}-$(date +%Y%m%d-%H%M%S).log"

  echo "[$(date +%H:%M:%S)] Starting $fid: $desc"
  echo "[$(date +%H:%M:%S)] Log: $logfile"

  claude --print \
    --allowedTools "Agent,Bash,Edit,Glob,Grep,Read,Write,Skill" \
    "Run /create-feature $fid $desc

IMPORTANT: The Architect phase is ALREADY DONE for this feature.
Task files exist at tasks/features/$fid-*/. Do NOT re-run the Architect.
Skip straight to Step 1.5 (readiness gate) and then execute the Waves.
Follow the /create-feature pipeline from Step 1.5 onward:
1.5) Readiness gate (or skip with DIDIO_SKIP_READINESS=1 if needed)
2) Run each internal Wave in order (developer implements tasks)
3) TechLead review
4) QA validation
5) Final report" \
    > "$logfile" 2>&1 &

  echo $!
}

wait_for_pids() {
  local pids=("$@")
  local failed=0
  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      echo "[$(date +%H:%M:%S)] ERROR: Process $pid failed"
      failed=1
    fi
  done
  if [ "$failed" -eq 1 ]; then
    echo "[$(date +%H:%M:%S)] WARNING: Some features in this wave failed. Check logs in $LOGDIR/"
    echo "[$(date +%H:%M:%S)] Continue to next wave? (Ctrl+C to abort, Enter to continue)"
    read -r
  fi
}

# ---------------------------------------------------------------------------
run_wave_0() {
  echo ""
  echo "================================================================"
  echo " WAVE 0 — No deps (4 features in parallel)"
  echo "================================================================"
  local pids=()
  pids+=("$(run_feature F32 "Varredura em tempo real — SSE streaming progress for scans")")
  pids+=("$(run_feature F33 "Historico de precos — period-based price history with aggregation")")
  pids+=("$(run_feature F37 "Varredura global rotineira — APScheduler automated periodic scans")")
  pids+=("$(run_feature F41 "Lista de banimentos — Scryfall legality sync and ban list management")")
  echo "[$(date +%H:%M:%S)] Wave 0: ${#pids[@]} features launched. Waiting..."
  wait_for_pids "${pids[@]}"
  echo "[$(date +%H:%M:%S)] Wave 0 COMPLETE"
}

run_wave_1() {
  echo ""
  echo "================================================================"
  echo " WAVE 1 — Deps on Wave 0 (3 features in parallel)"
  echo "================================================================"
  local pids=()
  pids+=("$(run_feature F34 "Metricas de historico — analytics metrics per card per period")")
  pids+=("$(run_feature F42 "Motor de banidas em My Collection — collection ban analysis and alerts")")
  pids+=("$(run_feature F43 "Historico de banimentos — ban history timeline and market impact stub")")
  echo "[$(date +%H:%M:%S)] Wave 1: ${#pids[@]} features launched. Waiting..."
  wait_for_pids "${pids[@]}"
  echo "[$(date +%H:%M:%S)] Wave 1 COMPLETE"
}

run_wave_2() {
  echo ""
  echo "================================================================"
  echo " WAVE 2 — Deps on Wave 1 (3 features in parallel)"
  echo "================================================================"
  local pids=()
  pids+=("$(run_feature F35 "Top Decks por valor — deck ranking by total value with sparklines")")
  pids+=("$(run_feature F36 "Cards em alta e em baixa — trending engine with composite scoring")")
  pids+=("$(run_feature F44 "Arquitetura compartilhada de dados — MarketDataService facade and cache")")
  echo "[$(date +%H:%M:%S)] Wave 2: ${#pids[@]} features launched. Waiting..."
  wait_for_pids "${pids[@]}"
  echo "[$(date +%H:%M:%S)] Wave 2 COMPLETE"
}

run_wave_3() {
  echo ""
  echo "================================================================"
  echo " WAVE 3 — Deps on Wave 2 (3 features in parallel)"
  echo "================================================================"
  local pids=()
  pids+=("$(run_feature F38 "Landing Page Em Alta Em Baixa — trending sections on dashboard")")
  pids+=("$(run_feature F39 "Ticker estilo Bolsa — stock-style horizontal ticker animation")")
  pids+=("$(run_feature F40 "Pagina global de Mercado — unified market dashboard page")")
  echo "[$(date +%H:%M:%S)] Wave 3: ${#pids[@]} features launched. Waiting..."
  wait_for_pids "${pids[@]}"
  echo "[$(date +%H:%M:%S)] Wave 3 COMPLETE"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
WAVE="${1:-all}"

echo "================================================================"
echo " P2 Market Intelligence — Parallel Execution"
echo " 13 features | 82 tasks | 4 waves"
echo " Started: $(date)"
echo " Logs: $LOGDIR/"
echo "================================================================"

case "$WAVE" in
  0) run_wave_0 ;;
  1) run_wave_1 ;;
  2) run_wave_2 ;;
  3) run_wave_3 ;;
  all)
    run_wave_0
    run_wave_1
    run_wave_2
    run_wave_3
    echo ""
    echo "================================================================"
    echo " ALL WAVES COMPLETE — $(date)"
    echo " Check logs: $LOGDIR/"
    echo "================================================================"
    ;;
  *)
    echo "Usage: $0 [0|1|2|3|all]"
    exit 1
    ;;
esac

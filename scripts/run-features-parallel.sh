#!/usr/bin/env bash
# ============================================================================
# run-features-parallel.sh — Execute planned features in parallel batches
# ============================================================================
#
# Strategy:
#   Batch 1 (parallel): F99 (backend) + F95 (frontend) + F97 (frontend)
#     - F99 touches only backend (models, repo, services) — zero overlap
#     - F95 touches empty states (Dashboard, MyCollection, DeckList, Evaluations)
#     - F97 touches navigation (breadcrumbs, Market, Trending, CardDetail, DeckView)
#     - Overlap: Evaluations, DeckList, TopDecksPage (but orthogonal changes)
#     - i18n keys: each feature uses unique key prefixes to avoid conflicts
#
#   Batch 2 (parallel): F96 (credits) + F98 (scan feedback)
#     - F96 touches CreditConfirmModal, TreasureBalance, MyCollection (refresh btns)
#     - F98 touches scans backend + ScanProgressBar + undo delete
#     - Overlap: MyCollection, CollectionCardDetail (but orthogonal areas)
#     - Runs after Batch 1 merges to avoid i18n/page conflicts
#
# Isolation: git worktrees give each feature its own working copy
# Merge: sequential merge back to homol after each batch
#
# Usage:
#   ./scripts/run-features-parallel.sh [--batch 1|2|all] [--dry-run]
#
# Prerequisites:
#   - Clean homol branch (no uncommitted changes)
#   - All features planned (tasks/features/F9X-*/ exist)
#   - claude CLI available in PATH
# ============================================================================

set -euo pipefail

# --- Config ---
BASE_BRANCH="homol"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKTREE_DIR="$REPO_ROOT/../tcg-worktrees"
LOG_DIR="$REPO_ROOT/logs/parallel-run"
TIMESTAMP=$(date +%Y%m%dT%H%M%S)

# Feature definitions: ID, slug, type (for ordering merges)
BATCH1_FEATURES=(
  "F99:data-integrity-hardening:backend"
  "F95:onboarding-empty-states:frontend"
  "F97:navigation-cross-links:frontend"
)

BATCH2_FEATURES=(
  "F96:credit-transparency:frontend"
  "F98:scan-results-feedback:fullstack"
)

# --- Args ---
BATCH="all"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch) BATCH="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# --- Helpers ---
log() { echo "[$(date +%H:%M:%S)] $*"; }
err() { echo "[$(date +%H:%M:%S)] ERROR: $*" >&2; }

ensure_clean() {
  cd "$REPO_ROOT"
  if ! git diff --quiet || ! git diff --cached --quiet; then
    err "Working tree not clean. Commit or stash changes first."
    exit 1
  fi
  local branch
  branch=$(git branch --show-current)
  if [[ "$branch" != "$BASE_BRANCH" ]]; then
    err "Not on $BASE_BRANCH (on: $branch). Switch first."
    exit 1
  fi
}

create_worktree() {
  local fid="$1" slug="$2"
  local branch="feature/${fid}-${slug}"
  local wt_path="$WORKTREE_DIR/$fid"

  log "Creating worktree for $fid at $wt_path (branch: $branch)"

  if [[ "$DRY_RUN" == true ]]; then
    log "[DRY-RUN] Would create worktree: $wt_path"
    return 0
  fi

  mkdir -p "$WORKTREE_DIR"

  # Create branch from current homol HEAD
  git branch "$branch" "$BASE_BRANCH" 2>/dev/null || true
  git worktree add "$wt_path" "$branch"

  echo "$wt_path"
}

run_feature_in_worktree() {
  local fid="$1" slug="$2" ftype="$3"
  local wt_path="$WORKTREE_DIR/$fid"
  local log_file="$LOG_DIR/${fid}-${TIMESTAMP}.log"
  local pid_file="$LOG_DIR/${fid}.pid"

  log "Starting $fid ($slug) in $wt_path"

  if [[ "$DRY_RUN" == true ]]; then
    log "[DRY-RUN] Would run: claude -p '$wt_path' --yes '/create-feature $fid'"
    echo "SUCCESS" > "$LOG_DIR/${fid}.status"
    return 0
  fi

  mkdir -p "$LOG_DIR"

  # Run claude in the worktree directory with the create-feature command
  # The --yes flag auto-approves safe operations
  # Redirect output to log file while also showing progress
  (
    cd "$wt_path"
    claude --yes --dangerously-skip-permissions \
      -p "Run /create-feature $fid $slug — execute all waves (Developer → TechLead → QA). The feature is already planned in tasks/features/${fid}-${slug}/. Do NOT re-run the Architect. Start from Wave 0 Developer." \
      2>&1 | tee "$log_file"

    local exit_code=${PIPESTATUS[0]}
    if [[ $exit_code -ne 0 ]]; then
      err "$fid failed with exit code $exit_code. See: $log_file"
      echo "FAILED" > "$LOG_DIR/${fid}.status"
    else
      echo "SUCCESS" > "$LOG_DIR/${fid}.status"
    fi
  ) &

  echo $! > "$pid_file"
}

wait_for_batch() {
  local pids=("$@")
  local all_ok=true

  log "Waiting for ${#pids[@]} features to complete..."

  for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
      all_ok=false
    fi
  done

  if [[ "$all_ok" != true ]]; then
    err "One or more features in this batch failed."
    return 1
  fi

  log "All features in batch completed successfully."
}

merge_feature() {
  local fid="$1" slug="$2"
  local branch="feature/${fid}-${slug}"
  local wt_path="$WORKTREE_DIR/$fid"

  log "Merging $branch into $BASE_BRANCH"

  if [[ "$DRY_RUN" == true ]]; then
    log "[DRY-RUN] Would merge $branch into $BASE_BRANCH"
    return 0
  fi

  cd "$REPO_ROOT"
  git merge "$branch" --no-ff -m "feat: merge $fid $slug into $BASE_BRANCH"

  # Cleanup worktree
  git worktree remove "$wt_path" --force 2>/dev/null || true
  git branch -d "$branch" 2>/dev/null || true

  log "Merged and cleaned up $fid"
}

run_batch() {
  local -n features=$1
  local batch_name="$2"

  log "=== Starting $batch_name (${#features[@]} features) ==="

  mkdir -p "$LOG_DIR"

  # Create worktrees
  for entry in "${features[@]}"; do
    IFS=: read -r fid slug ftype <<< "$entry"
    create_worktree "$fid" "$slug"
  done

  # Launch features in parallel
  for entry in "${features[@]}"; do
    IFS=: read -r fid slug ftype <<< "$entry"
    run_feature_in_worktree "$fid" "$slug" "$ftype"
  done

  # Wait for all background jobs (skip in dry-run — no bg jobs)
  if [[ "$DRY_RUN" != true ]]; then
    local pids=()
    for entry in "${features[@]}"; do
      IFS=: read -r fid slug ftype <<< "$entry"
      local pid_file="$LOG_DIR/${fid}.pid"
      if [[ -f "$pid_file" ]]; then
        pids+=("$(cat "$pid_file")")
        log "$fid launched (PID: $(cat "$pid_file"))"
      fi
    done
    wait_for_batch "${pids[@]}"
  else
    log "[DRY-RUN] Skipping wait — no background processes"
  fi

  # Check status files
  local failed=()
  for entry in "${features[@]}"; do
    IFS=: read -r fid slug ftype <<< "$entry"
    local status_file="$LOG_DIR/${fid}.status"
    if [[ -f "$status_file" ]] && [[ "$(cat "$status_file")" == "FAILED" ]]; then
      failed+=("$fid")
    fi
  done

  if [[ ${#failed[@]} -gt 0 ]]; then
    err "Failed features: ${failed[*]}"
    err "Check logs in $LOG_DIR/"
    if [[ "$DRY_RUN" != true ]]; then
      echo ""
      echo "Options:"
      echo "  1. Fix issues in worktree and re-run manually"
      echo "  2. Skip failed features: edit this script to remove them"
      echo "  3. Merge successful features and retry failed ones later"
      echo ""
      read -p "Continue merging successful features? [y/N] " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
      fi
    fi
  fi

  # Merge back to homol (sequential, backend first for Batch 1)
  # Sort: backend first, then frontend, then fullstack
  local merge_order=()
  for entry in "${features[@]}"; do
    IFS=: read -r fid slug ftype <<< "$entry"
    if [[ "$ftype" == "backend" ]]; then
      merge_order=("$entry" "${merge_order[@]}")
    else
      merge_order+=("$entry")
    fi
  done

  for entry in "${merge_order[@]}"; do
    IFS=: read -r fid slug ftype <<< "$entry"
    local status_file="$LOG_DIR/${fid}.status"
    if [[ -f "$status_file" ]] && [[ "$(cat "$status_file")" == "FAILED" ]]; then
      log "Skipping merge of failed feature $fid"
      continue
    fi
    merge_feature "$fid" "$slug"
  done

  log "=== $batch_name complete ==="
}

# --- Main ---
log "============================================"
log "Parallel Feature Execution — $TIMESTAMP"
log "Batch: $BATCH | Dry-run: $DRY_RUN"
log "============================================"

ensure_clean

case "$BATCH" in
  1)
    run_batch BATCH1_FEATURES "Batch 1 (F99+F95+F97)"
    ;;
  2)
    run_batch BATCH2_FEATURES "Batch 2 (F96+F98)"
    ;;
  all)
    run_batch BATCH1_FEATURES "Batch 1 (F99+F95+F97)"
    log ""
    log "Batch 1 merged. Pausing 5s before Batch 2..."
    sleep 5
    run_batch BATCH2_FEATURES "Batch 2 (F96+F98)"
    ;;
  *)
    err "Invalid batch: $BATCH (use 1, 2, or all)"
    exit 1
    ;;
esac

log ""
log "============================================"
log "ALL DONE"
log "Logs: $LOG_DIR/"
log "============================================"

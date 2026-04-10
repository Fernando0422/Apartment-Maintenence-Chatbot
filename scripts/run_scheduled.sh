#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$ROOT_DIR/data/reports"
mkdir -p "$LOG_DIR"

MODE="${1:-hybrid}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/scheduler_${STAMP}.log"

cd "$ROOT_DIR"
python3 scripts/run_pipeline.py --mode "$MODE" >>"$LOG_FILE" 2>&1
echo "Scheduled run complete. Log: $LOG_FILE"

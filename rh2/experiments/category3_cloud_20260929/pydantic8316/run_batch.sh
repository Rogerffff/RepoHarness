#!/usr/bin/env bash
# pydantic-8316：按模式顺序跑一组正式评分；每组跑完立即汇总并归档到 docs 证据目录（09-30 主审，防止 runs/ 丢失）。
# 用法：run_batch.sh <orig|rev1|rev2|rev3> <候选名...>    候选名同 run_formal.sh
set -uo pipefail
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/pydantic8316
W=$ROOT/runs/category3_cloud_20260929/pydantic8316
DOC=$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/pydantic__pydantic-8316/evidence
MODE=$1; shift
case $MODE in
  orig) OUT=$W/formal ;;
  rev1) OUT=$W/formal_revised_v1 ;;
  rev2) OUT=$W/formal_revised_v2 ;;
  rev3) OUT=$W/formal_revised_v3 ;;
  *) echo "bad mode $MODE"; exit 2 ;;
esac
bash "$E/run_formal.sh" "$MODE" "$@" 2>&1 | tee -a "$W/formal_${MODE}_driver.log"
python3 "$E/summarize_formal.py" "$OUT" 2>&1 | tee -a "$W/formal_${MODE}_driver.log"
cd "$ROOT" && python3 rh2/experiments/category3_cloud_20260929/archive_evidence.py runs/category3_cloud_20260929/pydantic8316 "$DOC"
echo "BATCH DONE $MODE $(date -u +%FT%TZ)"

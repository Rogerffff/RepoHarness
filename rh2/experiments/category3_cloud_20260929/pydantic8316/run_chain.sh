#!/usr/bin/env bash
# pydantic-8316（09-30 主审）：私有行为矩阵 → 原材料补跑 skip_if_digit → 修订 v1 → 修订 v2，顺序执行；每步结束立即归档。
set -uo pipefail
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/pydantic8316
W=$ROOT/runs/category3_cloud_20260929/pydantic8316
DOC=$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/pydantic__pydantic-8316/evidence
BUNDLES=$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl
ALL="noop gold keep_digit lookaround scan upstream_main normalize lead_only first_only acr3 literal lower_or_start no_lower_upper acr_max4 only_if_no_us skip_if_underscore skip_if_digit lower_or_start_la acr_max5 no_trailing_upper no_digit_split no_digit_upper"
archive() { cd "$ROOT" && python3 rh2/experiments/category3_cloud_20260929/archive_evidence.py runs/category3_cloud_20260929/pydantic8316 "$DOC"; }

if [ "${SKIP_SEMANTIC:-0}" != 1 ]; then
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  echo "== $(date -u +%FT%TZ) semantic_full"
  cd "$ROOT" && python3 rh2/experiments/task2_swegym_dev_20260925/semantic_control.py "$E/semantic_spec_full.json" \
    --out "$W/semantic_full" > "$W/semantic_full.log" 2>&1 || echo "SEMANTIC FAILED rc=$?"
  python3 "$E/summarize_semantic.py" "$W/semantic_full" "$BUNDLES" > "$W/semantic_full_summary.md" 2>&1
  archive
  echo "== $(date -u +%FT%TZ) semantic_full archived"
fi
bash "$E/run_batch.sh" orig skip_if_digit
# shellcheck disable=SC2086
bash "$E/run_batch.sh" rev1 $ALL
# shellcheck disable=SC2086
bash "$E/run_batch.sh" rev2 $ALL
echo "CHAIN DONE $(date -u +%FT%TZ)"

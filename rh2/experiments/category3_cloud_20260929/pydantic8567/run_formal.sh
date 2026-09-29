#!/usr/bin/env bash
# pydantic-8567 正式评分（09-19 pydantic_v1 安装配方 + 云端等效派生镜像）；可选 --materials 修订版诊断评分。
# 用法：run_formal.sh <orig|rev1|rev2> <候选名...>    候选名：noop | gold | <补丁名，不含 .patch>
set -euo pipefail
MODE=$1; shift
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/pydantic8567
W=$ROOT/runs/category3_cloud_20260929/pydantic8567
RECIPE=$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_recipe_repair_20260919/pydantic_v1/pydantic__pydantic-8567.json
DERIVED=$(python3 -c "import json;print(json.load(open('$W/derived/image.json'))['derived_id'])")
case $MODE in
  orig) OUT=$W/formal; EXTRA=() ;;
  rev1) OUT=$W/formal_revised_v1; EXTRA=(--materials "$E/materials_revised_v1.json") ;;
  rev2) OUT=$W/formal_revised_v2; EXTRA=(--materials "$E/materials_revised_v2.json") ;;
  *) echo "bad mode $MODE"; exit 2 ;;
esac
mkdir -p "$OUT"
cd "$ROOT/rh2"
for C in "$@"; do
  case $C in
    noop) CAND=noop ;;
    gold) CAND=gold-dir:$W/gold ;;
    *) CAND=patch:$E/$C.patch ;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  echo "== $(date -u +%FT%TZ) $MODE $C"
  MILES_RH2_RUN_ID=c3b2-pydantic8567-$MODE-$C .venv/bin/python experiments/env_recipe_repair_20260919/replay_with_install_recipe.py \
    --code-root "$(pwd)" --recipe "$RECIPE" "${EXTRA[@]}" --audit-dir "$OUT/audit_$C" -- \
    run --prepared-summary "$W/prepared/replay_summary.json" --task-ids pydantic__pydantic-8567 --candidate "$CAND" \
    --derived-image "$DERIVED" --derived-image-recipe pydantic-install-v1-c3cloud-equiv \
    --eval-log-dir "$OUT/eval_logs" --artifacts-dir "$OUT/artifacts" --ledger "$OUT/ledger_$C.jsonl" > "$OUT/run_$C.out" 2>&1 \
    || echo "RUN FAILED rc=$? $C"
  python3 - "$OUT/ledger_$C.jsonl" <<'PY'
import json, sys
r = json.loads(open(sys.argv[1]).readline())
rep = r["report"] or {}
print(json.dumps({"cand": r["candidate"].get("origin") or r["candidate"].get("kind"), "reward": rep.get("reward"),
                  "f2p": f"{rep.get('f2p_pass')}/{rep.get('f2p_total')}", "p2p_fail": rep.get("p2p_fail"),
                  "p2p_total": rep.get("p2p_total"), "grader": rep.get("grader_version"),
                  "ref_missing": r.get("reference_missing_count"), "stage_error": r.get("stage_error"),
                  "install_rc": (r.get("install") or {}).get("install_rc_last_command"),
                  "cleanup_removed": (r.get("cleanup") or {}).get("removed")}))
PY
done

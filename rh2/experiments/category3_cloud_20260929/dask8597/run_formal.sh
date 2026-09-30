#!/usr/bin/env bash
# dask__dask-8597 正式评分：09-19 compat_v1 安装配方（离线 pytest 7.4.4）+ 云端等效派生镜像；可选 --materials 修订版诊断评分。
# 用法：run_formal.sh <orig|rev1|rev2|plain> <候选...>    候选：noop | gold | <candidates/ 下补丁名，不含 .patch>
#   orig：原材料 + compat_v1 配方（与 09-19 历史同一条件）
#   rev1：修订测试草案 v1（--materials）+ compat_v1 配方
#   rev2：修订测试草案 v2（c4 改为 12000 个下标）+ compat_v1 配方
#   plain：原材料、原镜像、不加配方（pytest 8.3.2），只用于对照配方是否影响分数
set -uo pipefail
MODE=$1; shift
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/dask8597
W=$ROOT/runs/category3_cloud_20260929/dask8597
IID=dask__dask-8597
RECIPE=$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_recipe_repair_20260919/compat_v1/recipes/$IID.json
DERIVED=$(python3 -c "import json;print(json.load(open('$W/derived/image.json'))['derived_id'])")
case $MODE in
  orig)  OUT=$W/formal;            EXTRA=(--recipe "$RECIPE") ;;
  rev1)  OUT=$W/formal_revised_v1; EXTRA=(--recipe "$RECIPE" --materials "$E/materials_revised_v1.json") ;;
  rev2)  OUT=$W/formal_revised_v2; EXTRA=(--recipe "$RECIPE" --materials "$E/materials_revised_v2.json") ;;
  plain) OUT=$W/formal_plain;      EXTRA=() ;;
  *) echo "bad mode $MODE"; exit 2 ;;
esac
mkdir -p "$OUT"
cd "$ROOT/rh2"
for C in "$@"; do
  case $C in
    noop) CAND=noop ;;
    gold) CAND=gold-dir:$W/gold ;;
    *) CAND=patch:$E/candidates/$C.patch ;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  echo "== $(date -u +%FT%TZ) $MODE $C"
  if [ "$MODE" = plain ]; then
    MILES_RH2_RUN_ID=c3b2-dask8597-$MODE-$C .venv/bin/python scripts/replay_grade.py run \
      --prepared-summary "$W/prepared/replay_summary.json" --task-ids $IID --candidate "$CAND" \
      --eval-log-dir "$OUT/eval_logs" --artifacts-dir "$OUT/artifacts" --ledger "$OUT/ledger_$C.jsonl" \
      > "$OUT/run_$C.out" 2>&1 || echo "RUN FAILED rc=$? $C"
  else
    MILES_RH2_RUN_ID=c3b2-dask8597-$MODE-$C .venv/bin/python experiments/env_recipe_repair_20260919/replay_with_install_recipe.py \
      --code-root "$(pwd)" "${EXTRA[@]}" --audit-dir "$OUT/audit_$C" -- \
      run --prepared-summary "$W/prepared/replay_summary.json" --task-ids $IID --candidate "$CAND" \
      --derived-image "$DERIVED" --derived-image-recipe compat_v1:$IID:c3cloud-equiv \
      --eval-log-dir "$OUT/eval_logs" --artifacts-dir "$OUT/artifacts" --ledger "$OUT/ledger_$C.jsonl" \
      > "$OUT/run_$C.out" 2>&1 || echo "RUN FAILED rc=$? $C"
  fi
  python3 - "$OUT/ledger_$C.jsonl" <<'PY' || echo "LEDGER READ FAILED $C"
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

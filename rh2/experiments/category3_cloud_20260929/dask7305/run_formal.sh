#!/usr/bin/env bash
# dask__dask-7305 正式评分（原材料或修订版诊断评分），逐个候选串行执行。
# 用法：run_formal.sh orig|rev|rev2 <候选...>（rev 为 v1，rev2 为 v2）
#   候选：noop | gold | <candidates/ 下的补丁名，不带 .patch>
set -uo pipefail
MODE=$1; shift
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/dask7305
W=$ROOT/runs/category3_cloud_20260929/dask7305
IID=dask__dask-7305
cd $ROOT/rh2
for C in "$@"; do
  case $C in
    noop) CAND=noop ;;
    gold) CAND=gold-dir:$W/gold ;;
    *) CAND=patch:$E/candidates/$C.patch ;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  if [ "$MODE" = orig ]; then
    O=$W/formal; mkdir -p $O
    MILES_RH2_RUN_ID=c3b2-dask7305-$C .venv/bin/python scripts/replay_grade.py run \
      --prepared-summary $W/prepared/replay_summary.json --task-ids $IID --candidate $CAND \
      --eval-log-dir $O/eval_logs --artifacts-dir $O/artifacts --ledger $O/ledger_$C.jsonl \
      > $O/run_$C.out 2>&1
  else
    # rev = v1（沿用旧名）；rev2 = v2
    V=1; [ "$MODE" = rev2 ] && V=2
    O=$W/formal_revised_v$V; mkdir -p $O
    MILES_RH2_RUN_ID=c3b2-dask7305-r$V-$C .venv/bin/python \
      experiments/env_recipe_repair_20260919/replay_with_install_recipe.py --code-root $(pwd) \
      --materials $E/materials_revised_v$V.json --audit-dir $O/audit_$C -- run \
      --prepared-summary $W/prepared/replay_summary.json --task-ids $IID --candidate $CAND \
      --eval-log-dir $O/eval_logs --artifacts-dir $O/artifacts --ledger $O/ledger_$C.jsonl \
      > $O/run_$C.out 2>&1
  fi
  echo "$MODE $C rc=$? $(date -u +%H:%M:%S)"
done

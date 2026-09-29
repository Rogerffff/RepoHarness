#!/usr/bin/env bash
# dask__dask-8801 正式评分（逐个候选串行）。用法：
#   run_formal.sh original <候选...>      原材料
#   run_formal.sh v3 <候选...>            修订版诊断评分（--materials materials_revised_v3.json）
# 候选名：noop | gold | 本目录下 <名字>.patch 的名字
set -u
MODE=$1; shift
ROOT=/home/user/RepoHarness
ED=$ROOT/rh2/experiments/category3_cloud_20260929/dask8801
W=$ROOT/runs/category3_cloud_20260929/dask8801
cd $ROOT/rh2
if [ "$MODE" = original ]; then OUT=$W/formal; else OUT=$W/formal_revised_$MODE; fi
mkdir -p $OUT
for C in "$@"; do
  case $C in
    noop) SPEC=noop ;;
    gold) SPEC=gold-dir:$W/gold ;;
    *) SPEC=patch:$ED/$C.patch ;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  T0=$(date +%s)
  COMMON=(run --prepared-summary $W/prepared/replay_summary.json --task-ids dask__dask-8801 --candidate $SPEC
          --eval-log-dir $OUT/eval_logs --artifacts-dir $OUT/artifacts --ledger $OUT/ledger_$C.jsonl)
  if [ "$MODE" = original ]; then
    MILES_RH2_RUN_ID=c3b2-dask8801-$C timeout 3600 .venv/bin/python scripts/replay_grade.py "${COMMON[@]}" > $OUT/run_$C.out 2>&1
  else
    MILES_RH2_RUN_ID=c3b2-dask8801-$C-$MODE timeout 3600 .venv/bin/python experiments/env_recipe_repair_20260919/replay_with_install_recipe.py \
      --code-root $(pwd) --materials $ED/materials_revised_$MODE.json --audit-dir $OUT/audit_$C -- "${COMMON[@]}" > $OUT/run_$C.out 2>&1
  fi
  RC=$?
  echo "$C rc=$RC secs=$(( $(date +%s) - T0 )) $(grep -o '"reward": [0-9.]*' $OUT/run_$C.out | head -1)"
done

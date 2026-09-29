#!/usr/bin/env bash
# moto-6185 正式评分（install_wave1 云端重建派生镜像）。
# 用法：run_formal.sh <mode> <候选...>
#   mode = orig（原材料） | v1 | v1s（--materials 修订版诊断评分）
#   候选 = noop | gold | 本目录下 <名字>.patch 的名字
# 每次评分前等机器空闲（运行中的容器少于 3 个），逐个串行执行。
set -u
REPO=/home/user/RepoHarness
E=$REPO/rh2/experiments/category3_cloud_20260929/moto6185
W=$REPO/runs/category3_cloud_20260929/moto6185
IID=getmoto__moto-6185
DERIVED=$(cat "$W/derived_id.txt")
LABEL=install-wave1:$IID:c3cloud-rebuild
mode=$1; shift
cd "$REPO/rh2"
for cand in "$@"; do
  case $cand in
    noop) spec=noop ;;
    gold) spec=gold-dir:$W/gold ;;
    *) spec=patch:$E/$cand.patch ;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  if [ "$mode" = orig ]; then
    D=$W/formal
    mkdir -p "$D"
    MILES_RH2_RUN_ID=c3b2-moto6185-$cand .venv/bin/python scripts/replay_grade.py run \
      --prepared-summary "$W/prepared/replay_summary.json" --task-ids $IID --candidate "$spec" \
      --eval-log-dir "$D/eval_logs" --artifacts-dir "$D/artifacts" --ledger "$D/ledger_$cand.jsonl" \
      --derived-image "$DERIVED" --derived-image-recipe "$LABEL" > "$D/run_$cand.out" 2>&1
  else
    D=$W/formal_revised_$mode
    mkdir -p "$D"
    MILES_RH2_RUN_ID=c3b2-moto6185-$mode-$cand .venv/bin/python \
      experiments/env_recipe_repair_20260919/replay_with_install_recipe.py --code-root "$(pwd)" \
      --materials "$E/materials_revised_$mode.json" --audit-dir "$D/audit_$cand" -- run \
      --prepared-summary "$W/prepared/replay_summary.json" --task-ids $IID --candidate "$spec" \
      --eval-log-dir "$D/eval_logs" --artifacts-dir "$D/artifacts" --ledger "$D/ledger_$cand.jsonl" \
      --derived-image "$DERIVED" --derived-image-recipe "$LABEL" > "$D/run_$cand.out" 2>&1
  fi
  echo "$mode $cand rc=$? $(grep -o '"reward": [0-9.]*' "$D/run_$cand.out" | head -1)"
done

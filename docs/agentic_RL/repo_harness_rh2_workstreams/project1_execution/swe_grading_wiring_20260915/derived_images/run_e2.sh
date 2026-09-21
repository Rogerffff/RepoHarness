#!/bin/bash
# e2 编排（机器上 nohup 执行）：等待全部镜像拉取 → 构建派生镜像 → 开 metacopy → 两条 lane 并行 → E2_DONE。
set -u
cd /work/code/rh2
PY=.venv/bin/python
E=/work/replay
until grep -q PULLS_DONE $E/pull_e2.log; do sleep 30; done; echo "$(date -u +%FT%TZ) pulls done"
bash $E/derived/build_derived.sh > $E/derived/build.log 2>&1; echo "$(date -u +%FT%TZ) derived done"; grep -E "integrity_same|BUILD_FAILED" $E/derived/build.log
echo Y > /sys/module/overlay/parameters/metacopy
A=$(grep "^A=" $E/e2_ids.txt | cut -d= -f2); B=$(grep "^B=" $E/e2_ids.txt | cut -d= -f2)
COMMON="--prepared-summary $E/prepared_e2/replay_summary.json --candidate-stage-seconds 900 --grading-deadline-seconds 3600 --image-pull-seconds 3600 --eval-log-dir $E/eval_logs --artifacts-dir $E/artifacts"
DER_MOTO=$(grep -o '"moto-6913": {[^}]*}' $E/derived/images.json | grep -o 'rh2-derived/moto-6913:[0-9]*'); DER_PYD=$(grep -o '"pydantic-8500": {[^}]*}' $E/derived/images.json | grep -o 'rh2-derived/pydantic-8500:[0-9]*'); DER_MONAI=$(grep -o '"monai-1121": {[^}]*}' $E/derived/images.json | grep -o 'rh2-derived/monai-1121:[0-9]*')
laneA() {
  export MILES_RH2_RUN_ID=e2A-$(date +%Y%m%d)
  for cand in noop gold-dir:$E/gold_e2; do
    $PY scripts/replay_grade.py run $COMMON --task-ids "$A" --candidate "$cand" --repeat 2 --ledger $E/ledger_e2_A.jsonl
  done
  for t in getmoto__moto-6913 pydantic__pydantic-8500; do
    img=$DER_MOTO; [ "$t" = pydantic__pydantic-8500 ] && img=$DER_PYD
    [ -n "$img" ] && for cand in noop gold-dir:$E/gold_e2; do $PY scripts/replay_grade.py run $COMMON --task-ids "$t" --candidate "$cand" --repeat 1 --derived-image "$img" --derived-image-recipe "Dockerfile.${t#*__}" --ledger $E/ledger_e2_derived.jsonl; done
  done
  for t in Project-MONAI__MONAI-1121 Project-MONAI__MONAI-3205 getmoto__moto-4799 Project-MONAI__MONAI-763; do
    $PY scripts/replay_grade.py run $COMMON --task-ids "$t" --candidate gold-dir:$E/gold_e2 --repeat 1 --ledger $E/ledger_e2_C.jsonl
  done
  [ -n "$DER_MONAI" ] && $PY scripts/replay_grade.py run $COMMON --task-ids Project-MONAI__MONAI-1121 --candidate gold-dir:$E/gold_e2 --repeat 1 --derived-image "$DER_MONAI" --derived-image-recipe Dockerfile.monai-1121 --ledger $E/ledger_e2_derived.jsonl
  RH2_GRADER_SHM_BYTES=1073741824 $PY scripts/replay_grade.py run $COMMON --task-ids Project-MONAI__MONAI-763 --candidate gold-dir:$E/gold_e2 --repeat 1 --ledger $E/ledger_e2_C_shm1g.jsonl
  echo LANE_A_DONE
}
laneB() {
  export MILES_RH2_RUN_ID=e2B-$(date +%Y%m%d)
  $PY scripts/replay_grade.py run $COMMON --task-ids "$B" --candidate patch-dir:$E/cc_patches --repeat 1 --ledger $E/ledger_e2_B.jsonl
  $PY scripts/replay_grade.py run $COMMON --task-ids Project-MONAI__MONAI-6975,conan-io__conan-13326,getmoto__moto-6913,iterative__dvc-5822,pydantic__pydantic-8500,python__mypy-12741 --candidate patch-dir:$E/cc_patches --repeat 1 --ledger $E/ledger_e2_B_repeat.jsonl
  [ -n "$DER_MOTO" ] && $PY scripts/replay_grade.py run $COMMON --task-ids getmoto__moto-6913 --candidate patch-dir:$E/cc_patches --repeat 1 --derived-image "$DER_MOTO" --derived-image-recipe Dockerfile.moto-6913 --ledger $E/ledger_e2_derived.jsonl
  [ -n "$DER_PYD" ] && $PY scripts/replay_grade.py run $COMMON --task-ids pydantic__pydantic-8500 --candidate patch-dir:$E/cc_patches --repeat 1 --derived-image "$DER_PYD" --derived-image-recipe Dockerfile.pydantic-8500 --ledger $E/ledger_e2_derived.jsonl
  echo LANE_B_DONE
}
laneA > $E/e2_laneA.log 2>&1 &
laneB > $E/e2_laneB.log 2>&1 &
wait
echo "$(date -u +%FT%TZ) E2_DONE"

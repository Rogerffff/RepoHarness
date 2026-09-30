#!/usr/bin/env bash
# 私有行为矩阵（root、断网、一次性容器）：逐变体调用 semantic_control.py，每个变体前等待机器空闲。
# 用法：run_semantic.sh <v1|v2> [变体...]
set -uo pipefail
V=$1; shift
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/dask8597
W=$ROOT/runs/category3_cloud_20260929/dask8597
SPECS=$W/semantic_$V/specs
python3 $E/make_spec.py $SPECS $V "$@" > /dev/null
for S in $SPECS/*.json; do
  N=$(basename $S .json)
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  echo "== $(date -u +%H:%M:%S) $V $N"
  python3 $ROOT/rh2/experiments/task2_swegym_dev_20260925/semantic_control.py $S --out $W/semantic_$V/out \
    > $W/semantic_$V/out_$N.summary 2>&1 || echo "SEMANTIC FAILED $N"
  cat $W/semantic_$V/out_$N.summary
done
echo "== done $(date -u +%H:%M:%S)"

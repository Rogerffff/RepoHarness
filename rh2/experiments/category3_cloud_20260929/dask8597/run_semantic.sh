#!/usr/bin/env bash
# 私有行为矩阵（root、断网、一次性容器）：逐变体调用 semantic_control.py，每个变体前等待机器空闲。
# 用法：run_semantic.sh <v1|v2> [变体...]（不给变体则跑 make_spec.py 的全部变体）
# 09-30 修正：只跑本次请求的变体（此前会把 specs 目录里已有的变体一并重跑；结果确定，只是重复覆盖同一输出）。
set -uo pipefail
V=$1; shift
ROOT=/home/user/RepoHarness
E=$ROOT/rh2/experiments/category3_cloud_20260929/dask8597
W=$ROOT/runs/category3_cloud_20260929/dask8597
SPECS=$W/semantic_$V/specs
mapfile -t LIST < <(python3 $E/make_spec.py $SPECS $V "$@")
for S in "${LIST[@]}"; do
  N=$(basename $S .json)
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  echo "== $(date -u +%H:%M:%S) $V $N"
  python3 $ROOT/rh2/experiments/task2_swegym_dev_20260925/semantic_control.py $S --out $W/semantic_$V/out \
    > $W/semantic_$V/out_$N.summary 2>&1 || echo "SEMANTIC FAILED $N"
  cat $W/semantic_$V/out_$N.summary
done
echo "== done $(date -u +%H:%M:%S)"

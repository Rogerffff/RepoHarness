#!/bin/bash
# 全量公开测试 tests/（不套测试补丁）。一次性、断网、root 容器内运行。
# 用法（容器内）：bash /rv/run_full.sh <输出目录> <候选名>...
set -u
OUT=$1; shift
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
for cand in "$@"; do
  d="$OUT/$cand"; mkdir -p "$d"
  patch=""
  for p in /rv/cands/$cand.patch /p8567/$cand.patch /gold/$cand.patch; do
    if [ -f "$p" ]; then patch=$p; break; fi
  done
  git checkout -q -- pydantic tests
  if [ "$cand" != "noop" ]; then
    git apply "$patch" || { echo "APPLY FAILED $cand"; continue; }
  fi
  pytest -q -p no:cacheprovider -rf tests/ > "$d/full.out" 2>&1
  echo "RC=$?" >> "$d/full.out"
  git checkout -q -- pydantic tests
  echo "done $cand"
done

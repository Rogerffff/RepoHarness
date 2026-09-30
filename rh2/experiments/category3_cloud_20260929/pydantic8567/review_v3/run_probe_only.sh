#!/bin/bash
# 只跑一个补充探针脚本（不套测试补丁）。一次性、断网、root 容器内运行。
# 用法（容器内）：bash /rv/run_probe_only.sh <输出目录> <探针脚本名，如 probe_extra> <候选名>...
set -u
OUT=$1; shift
PROBE=$1; shift
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
  python "/rv/$PROBE.py" > "$d/$PROBE.out" 2>&1
  git checkout -q -- pydantic tests
done
echo "probe-only done"

#!/bin/bash
# v3 聚焦复核：私有行为矩阵 + 私有模拟评分（不是正式评分）。在一次性、断网、root 容器内运行。
# 用法（容器内）：bash /rv/run_private.sh <输出目录> <测试版本列表，逗号分隔> <候选名>...
# 候选补丁查找顺序：/rv/cands/<名>.patch（本复核）、/p8567/<名>.patch（作者目录）、/gold/<名>.patch；noop 不套补丁。
# 每个候选先 `git checkout -- pydantic tests` 复位；测试命令与评分包 eval_cmd 相同。
set -u
OUT=$1; shift
TVS=$1; shift
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
mkdir -p "$OUT"
for cand in "$@"; do
  d="$OUT/$cand"; mkdir -p "$d"
  patch=""
  for p in /rv/cands/$cand.patch /p8567/$cand.patch /gold/$cand.patch; do
    if [ -f "$p" ]; then patch=$p; break; fi
  done
  git checkout -q -- pydantic tests
  if [ "$cand" != "noop" ]; then
    if [ -z "$patch" ]; then echo "NO PATCH for $cand" > "$d/apply.err"; continue; fi
    git apply "$patch" 2> "$d/apply.err" || { echo "APPLY FAILED $cand"; continue; }
    sha256sum "$patch" > "$d/patch.sha256"
  fi
  python /rv/probe_matrix.py > "$d/probe.out" 2>&1
  for tv in ${TVS//,/ }; do
    git checkout -q -- tests
    git apply "/rv/tests/$tv.patch" 2> "$d/$tv.apply.err" || { echo "TEST APPLY FAILED $cand $tv"; continue; }
    pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_validators.py > "$d/$tv.out" 2>&1
    echo "RC=$?" >> "$d/$tv.out"
  done
  git checkout -q -- pydantic tests
  echo "done $cand"
done

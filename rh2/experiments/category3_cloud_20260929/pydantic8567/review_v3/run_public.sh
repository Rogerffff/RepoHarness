#!/bin/bash
# v3 聚焦复核：候选在公开测试上的表现（不套任何测试补丁）。一次性、断网、root 容器内运行。
# 用法（容器内）：bash /rv/run_public.sh <输出目录> <候选名>...
# 跑相关 5 个模块，外加 tests/test_docs.py 中 validators / serialization / json_schema 相关页面的示例
# （test_docs 需要 ruff：conda activate 后在 PATH 上）。
set -u
OUT=$1; shift
source /opt/miniconda3/bin/activate
conda activate testbed
cd /testbed
git config --global --add safe.directory /testbed
mkdir -p "$OUT"
which ruff > "$OUT/ruff_path.txt" 2>&1
for cand in "$@"; do
  d="$OUT/$cand"; mkdir -p "$d"
  patch=""
  for p in /rv/cands/$cand.patch /p8567/$cand.patch /gold/$cand.patch; do
    if [ -f "$p" ]; then patch=$p; break; fi
  done
  git checkout -q -- pydantic tests
  if [ "$cand" != "noop" ]; then
    git apply "$patch" 2> "$d/apply.err" || { echo "APPLY FAILED $cand"; continue; }
  fi
  pytest -q -p no:cacheprovider -o console_output_style=classic tests/test_validators.py tests/test_serialize.py \
    tests/test_json_schema.py tests/test_annotated.py tests/test_types.py > "$d/modules5.out" 2>&1
  echo "RC=$?" >> "$d/modules5.out"
  pytest -q -p no:cacheprovider -rf tests/test_docs.py -k "validators or serialization or json_schema" > "$d/docs.out" 2>&1
  echo "RC=$?" >> "$d/docs.out"
  git checkout -q -- pydantic tests
  echo "done $cand"
done

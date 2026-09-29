#!/bin/bash
# 决策包 #8 补充：Read 显式 offset/limit 的报错分支、Read 上限环境变量、adapter 溢出回复（空 text + max_tokens）时 CC 的反应。
cd /work/code/rh2
export SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz
R=experiments/decision_package_20260924/p8_9_10/run_p8910.py
COMMON="--prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422"
BASE="--disallowedTools Task WebFetch WebSearch"
run() {
  local name=$1 port=$2 sc=$3 label=$4; shift 4
  rm -rf /work/probe/runs/dp_$name
  timeout 900 .venv/bin/python $R $COMMON --scenario $sc --out-dir /work/probe/runs/dp_$name --attempt-id dp8${name//_/} --stub-port $port --label "$label" "$@" > /work/probe/runs/dp_logs/dp_$name.log 2>&1
  echo "== $name rc=$?"
}
run r8_estlimit 18121 bigread_limit "R8iii count_tokens->chars/4, Read with offset=1 limit=1800" "--stub-extra-args=--count-tokens-mode chars4"
run r8_zerolimit 18122 bigread_limit "R8iii' count_tokens->0, Read with offset=1 limit=1800" "--stub-extra-args=--count-tokens-mode zero"
run r8_estcap8k 18123 bigread "R8iv count_tokens->chars/4 + CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS=8000" "--stub-extra-args=--count-tokens-mode chars4" "--cc-extra-envs={\"CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS\": \"8000\"}"
run c8_emptylen 18124 emptylen "C8h 3rd main request -> empty text + stop_reason max_tokens (adapter overflow shape)" "--cc-extra-args=$BASE --max-turns 40" --wall-seconds 240
echo CHAIN_DONE

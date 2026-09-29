#!/bin/bash
# 决策包 #8：Read 上限（bigread × count_tokens 三种应答）与压缩触发（ramp × 窗口相关环境变量；reactive 400）。
# 顺序执行，端口 18111–18120；环境变量经 SLIME_AGENT_CC_EXTRA_ENVS（正式通道）。
cd /work/code/rh2
export SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz
R=experiments/decision_package_20260924/p8_9_10/run_p8910.py
COMMON="--prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422"
BASE="--disallowedTools Task WebFetch WebSearch"
run() {  # name port scenario label [extra runner args...]
  local name=$1 port=$2 sc=$3 label=$4; shift 4
  rm -rf /work/probe/runs/dp_$name
  timeout 900 .venv/bin/python $R $COMMON --scenario $sc --out-dir /work/probe/runs/dp_$name --attempt-id dp8${name//_/} --stub-port $port --label "$label" "$@" > /work/probe/runs/dp_logs/dp_$name.log 2>&1
  echo "== $name rc=$?"
}
run r8_zero 18111 bigread "R8i count_tokens->0 (vendored adapter behaviour)" "--stub-extra-args=--count-tokens-mode zero"
run r8_est 18112 bigread "R8ii count_tokens->chars/4 estimate" "--stub-extra-args=--count-tokens-mode chars4"
run r8_null 18113 bigread "R8ii' count_tokens->null" "--stub-extra-args=--count-tokens-mode null"
RAMP="--cc-extra-args=$BASE --max-turns 40"
run c8_base 18114 ramp "C8a no env, usage 150k+20k" "$RAMP" --wall-seconds 240 --ramp-steps 10 "--stub-extra-args=--usage-start 150000 --usage-step 20000"
run c8_acw 18115 ramp "C8b AUTO_COMPACT_WINDOW=32768, usage 10k+10k" "$RAMP" --wall-seconds 240 --ramp-steps 10 "--stub-extra-args=--usage-start 10000 --usage-step 10000" "--cc-extra-envs={\"CLAUDE_CODE_AUTO_COMPACT_WINDOW\": \"32768\"}"
run c8_mct 18116 ramp "C8c MAX_CONTEXT_TOKENS=32768, usage 2k+3k" "$RAMP" --wall-seconds 240 --ramp-steps 12 "--stub-extra-args=--usage-start 2000 --usage-step 3000" "--cc-extra-envs={\"CLAUDE_CODE_MAX_CONTEXT_TOKENS\": \"32768\"}"
run c8_mctacw 18117 ramp "C8d MAX_CONTEXT_TOKENS=32768 + AUTO_COMPACT_WINDOW=100000, usage 2k+3k" "$RAMP" --wall-seconds 240 --ramp-steps 12 "--stub-extra-args=--usage-start 2000 --usage-step 3000" "--cc-extra-envs={\"CLAUDE_CODE_MAX_CONTEXT_TOKENS\": \"32768\", \"CLAUDE_CODE_AUTO_COMPACT_WINDOW\": \"100000\"}"
run c8_mctacwmo 18118 ramp "C8e MAX_CONTEXT_TOKENS=32768 + AUTO_COMPACT_WINDOW=100000 + MAX_OUTPUT_TOKENS=4096, usage 2k+3k" "$RAMP" --wall-seconds 240 --ramp-steps 12 "--stub-extra-args=--usage-start 2000 --usage-step 3000" "--cc-extra-envs={\"CLAUDE_CODE_MAX_CONTEXT_TOKENS\": \"32768\", \"CLAUDE_CODE_AUTO_COMPACT_WINDOW\": \"100000\", \"CLAUDE_CODE_MAX_OUTPUT_TOKENS\": \"4096\"}"
run c8_pct 18119 ramp "C8f AUTOCOMPACT_PCT_OVERRIDE=15 only, usage 10k+10k" "$RAMP" --wall-seconds 240 --ramp-steps 10 "--stub-extra-args=--usage-start 10000 --usage-step 10000" "--cc-extra-envs={\"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE\": \"15\"}"
run c8_reactive 18120 reactive "C8g no env, 3rd main request -> 400 prompt is too long" "$RAMP" --wall-seconds 240
echo CHAIN_DONE

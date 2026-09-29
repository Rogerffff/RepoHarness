#!/bin/bash
# 决策包 #8 补充 2：adapter 溢出回复（空 text + max_tokens）连续出现时 CC 的恢复次数与收尾。
cd /work/code/rh2
export SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz
R=experiments/decision_package_20260924/p8_9_10/run_p8910.py
rm -rf /work/probe/runs/dp_c8_emptyrep
timeout 900 .venv/bin/python $R --prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422 --scenario emptylen_repeat --out-dir /work/probe/runs/dp_c8_emptyrep --attempt-id dp8c8emptyrep --stub-port 18125 --label "C8i repeated empty text + max_tokens x6" "--cc-extra-args=--disallowedTools Task WebFetch WebSearch --max-turns 40" --wall-seconds 240 > /work/probe/runs/dp_logs/dp_c8_emptyrep.log 2>&1
echo "== c8_emptyrep rc=$?"
echo CHAIN_DONE

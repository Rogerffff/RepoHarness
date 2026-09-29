#!/bin/bash
# 决策包 #10 工具面 / #9 auto-memory：逐条件跑 probe（或 memwrite），全部走正式 driver；顺序执行，端口 18102–18110。
cd /work/code/rh2
export SLIME_AGENT_CC_PLATFORM_TARBALL=/work/probe/cc/claude-code-linux-x64-2.1.205.tgz
R=experiments/decision_package_20260924/p8_9_10/run_p8910.py
COMMON="--prepared-summary /work/probe/replay/prepared_a1/replay_summary.json --task conan-io__conan-15422"
BASE="--disallowedTools Task WebFetch WebSearch"
NONCORE="CronCreate CronDelete CronList EnterWorktree ExitWorktree ReportFindings ScheduleWakeup SendMessage Skill TaskCreate TaskGet TaskList TaskOutput TaskStop TaskUpdate Workflow"
run() {  # name port scenario label [extra runner args...]
  local name=$1 port=$2 sc=$3 label=$4; shift 4
  rm -rf /work/probe/runs/dp_$name
  timeout 900 .venv/bin/python $R $COMMON --scenario $sc --out-dir /work/probe/runs/dp_$name --attempt-id dp8${name//_/} --stub-port $port --label "$label" "$@" > /work/probe/runs/dp_logs/dp_$name.log 2>&1
  echo "== $name rc=$?"
}
run t10_denycore 18102 probe "T10b deny all non-core" "--cc-extra-args=$BASE $NONCORE --max-turns 8"
run t10_allowcore 18103 probe "T10b' allowedTools core5" "--cc-extra-args=$BASE --allowedTools Bash Read Edit Write NotebookEdit --max-turns 8"
run t10_toolscore 18104 probe "T10b'' --tools core5" "--cc-extra-args=--tools Bash,Read,Edit,Write,NotebookEdit $BASE --max-turns 8"
run t10_denyskill 18105 probe "T10c deny Skill" "--cc-extra-args=$BASE Skill --max-turns 8"
run t10_noslash 18106 probe "T10c' --disable-slash-commands" "--cc-extra-args=$BASE --disable-slash-commands --max-turns 8"
run m9_env 18107 probe "M9b env CLAUDE_CODE_DISABLE_AUTO_MEMORY=1" "--cc-extra-envs={\"CLAUDE_CODE_DISABLE_AUTO_MEMORY\": \"1\"}"
run m9_setfile 18108 probe "M9c user settings.json autoMemoryEnabled:false (write_config wrapper)" "--settings-extra={\"autoMemoryEnabled\": false}"
run m9_setflag 18109 probe "M9c' --settings JSON autoMemoryEnabled:false" "--cc-extra-args=$BASE --max-turns 8 --settings '{\"autoMemoryEnabled\":false}'"
run m9_midsess 18110 memwrite "M9d CC writes settings.json mid-session via Bash"
echo CHAIN_DONE

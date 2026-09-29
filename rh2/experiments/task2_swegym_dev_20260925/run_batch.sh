#!/usr/bin/env bash
# 串行跑一批 devcheck：每行 "<task> <cond> [image]"；清理残留（退出码 4）即停止派发（Codex R6）。
# 用法：run_batch.sh batch.txt ；每条的汇总追加到 /work/task2/runs/batch_summary.jsonl
set -u
cd /work/code/rh2
export SLIME_AGENT_CC_PLATFORM_TARBALL=/work/task2/cc/claude-code-linux-x64-2.1.205.tgz
while read -r task cond image; do
  [ -z "$task" ] && continue; case "$task" in \#*) continue;; esac
  short=$(echo "$task" | sed 's/.*__//; s/[^A-Za-z0-9]//g'); aid="t2${short}${cond//_/}$(date +%H%M%S)"
  out=/work/task2/runs/$short/$cond
  rm -rf "$out"; mkdir -p "$(dirname "$out")"
  .venv/bin/python experiments/task2_swegym_dev_20260925/devcheck.py --prepared-summary /work/task2/replay/prepared_all/replay_summary.json \
    --task "$task" ${image:+--image $image} --commands experiments/task2_swegym_dev_20260925/commands/$task.json \
    --out-dir "$out" --attempt-id "$aid" > "$out.summary.json" 2> "$out.stderr.log" < /dev/null
  rc=$?
  python3 -c "import json,sys; d=json.load(open('$out.summary.json')); print(json.dumps({'task':'$task','cond':'$cond','image':'${image:-public}','rc':$rc,'result':d.get('result'),'commands':d.get('commands'),'residual':d.get('residual'),'failure':d.get('failure_detail')}, ensure_ascii=False))" >> /work/task2/runs/batch_summary.jsonl 2>/dev/null || echo "{\"task\":\"$task\",\"cond\":\"$cond\",\"rc\":$rc,\"summary_unreadable\":true}" >> /work/task2/runs/batch_summary.jsonl
  tail -1 /work/task2/runs/batch_summary.jsonl
  # Codex F2：残留（rc=4）或汇总不可读（清理状态未知）都停止派发
  [ "$rc" = 4 ] && { echo "residual after cleanup; stop"; exit 4; }
  python3 -c "import json,sys; json.load(open('$out.summary.json'))" 2>/dev/null || { echo "summary unreadable, cleanup unknown; stop"; exit 4; }
done < "$1"

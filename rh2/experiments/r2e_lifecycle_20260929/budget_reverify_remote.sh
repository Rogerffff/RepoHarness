#!/bin/bash
# 控制面保护超时题的放宽预算复验（09-29，R2E 单题闭环试行）：等 v5 评分各路结束后，把正式复验里
# `grading_control_surface_protect_timeout_after_300s` 的题在 v5 任务面上以 env_reset_timeout 1200 s 重跑 noop / gold。
# 只放宽"基线重建 + 控制面保护"的时限（replay_grade_budget.py），评分语义不变；结果另记，不冒充缺省预算下的正式结果。
set -euo pipefail
F=/work/r2e/budget_v5; CODE=/work/code_v5/rh2; PY=$CODE/.venv/bin/python
mkdir -p $F
until grep -q "launched" /work/r2e/formal_v5/setup.log 2>/dev/null; do sleep 30; done
while systemctl list-units --no-legend --state=active "r2e-v5-u*" | grep -q .; do sleep 30; done
while systemctl list-units --no-legend --state=active "r2e-ev-*" | grep -q .; do sleep 30; done
IDS=$(python3 - <<'PY'
import json, glob
bad = set()
for f in glob.glob("/work/r2e/grader/ledger*_noop.jsonl") + glob.glob("/work/r2e/grader/ledger*_gold.jsonl"):
    for l in open(f):
        o = json.loads(l)
        if (o.get("report") or {}).get("reward") is None and "control_surface_protect_timeout" in l:
            bad.add(o["task_id"].split("::", 1)[1])
print(",".join(sorted(bad)))
PY
)
echo "[$(date -u +%T)] budget reverify: $IDS"
for c in noop gold; do
  cand=noop; [ $c = gold ] && cand=gold-dir:/work/r2e/gold
  systemd-run --unit=r2e-budget-$c --collect --working-directory=$CODE -p LimitNOFILE=65536 \
    -E MILES_RH2_RUN_ID=r2e-budget-$c-$(date +%m%d%H%M) \
    -p StandardOutput=append:$F/$c.log -p StandardError=append:$F/$c.log \
    $PY experiments/r2e_lifecycle_20260929/replay_grade_budget.py --env-reset-timeout 1200 -- run \
      --prepared-summary /work/r2e/prepared_v5/replay_summary.json --task-ids "$IDS" --candidate $cand \
      --image-overlays /work/r2e/derived/all_v5/overlays.jsonl --eval-log-dir $F/${c}_logs --artifacts-dir $F/${c}_art \
      --ledger $F/ledger_$c.jsonl
done
echo "[$(date -u +%T)] launched"

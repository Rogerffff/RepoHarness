#!/bin/bash
# 链路修复真机验证第二段：P-A（R1–R4 修后）真机对照。gold 建资格 → 人为语法错误补丁带资格。
set -o pipefail
ROOT=/work/claude_chainfix_20260919
OLD=/work/full216_20260919
PY="env PYTHONPATH=$ROOT/code/rh2/src $OLD/code/rh2/.venv/bin/python"
R=$ROOT/replay; mkdir -p $R/broken
cd $ROOT/code/rh2
COMMON="--prepared-summary $OLD/replay/prepared/replay_summary.json --candidate-stage-seconds 900 --grading-deadline-seconds 2400 --image-pull-seconds 3600 --eval-log-dir $R/eval_logs --artifacts-dir $R/artifacts"
export MILES_RH2_RUN_ID=chainfixpa-$(date +%Y%m%d)
echo "$(date -u +%FT%TZ) CHAINFIX_PA_START"
$PY scripts/replay_grade.py run $COMMON --task-ids iterative__dvc-5822,getmoto__moto-6913 --candidate gold-dir:$OLD/replay/gold --repeat 1 --ledger $R/ledger_pa_gold.jsonl
for t in iterative__dvc-5822 getmoto__moto-6913; do
  $PY - "$OLD/replay/gold/$t.gold.patch" "$R/broken/$t.diff" <<'PYEOF'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
lines = open(src, encoding="utf-8").read().splitlines(keepends=True)
out = []; done = False; hdr_idx = None
for line in lines:
    if not done and line.startswith("@@"):
        hdr_idx = len(out)
    out.append(line)
    if not done and hdr_idx is not None and line.startswith("+") and not line.startswith("+++"):
        out.append("+def rh2_broken(:\n"); done = True
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", out[hdr_idx])
        a, al, b, bl, rest = m.groups(); bl = int(bl or 1) + 1
        out[hdr_idx] = f"@@ -{a},{al or 1} +{b},{bl} @@{rest}\n"
open(dst, "w", encoding="utf-8").write("".join(out)); print("wrote", dst, done)
PYEOF
done
$PY scripts/replay_grade.py run $COMMON --task-ids iterative__dvc-5822,getmoto__moto-6913 --candidate patch-dir:$R/broken --repeat 1 --qualification-ledger $R/ledger_pa_gold.jsonl --ledger $R/ledger_pa_broken_q.jsonl
echo "$(date -u +%FT%TZ) CHAINFIX_PA_DONE"

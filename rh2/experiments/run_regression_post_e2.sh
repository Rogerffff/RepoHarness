#!/bin/bash
# e2 之后：同步 P-C/P-D/P-A 代码后的真机回归（机器 1）。先跑 gold 建资格账本，再以资格跑 noop / 候选，看 P-A 三路分布。
set -o pipefail
cd /work/code/rh2_next
PY="env PYTHONPATH=/work/code/rh2_next/src /work/code/rh2/.venv/bin/python"
E=/work/replay
R=$E/reg
mkdir -p $R
TASKS_E1="python__mypy-12741,conan-io__conan-13326,iterative__dvc-5822,pandas-dev__pandas-48106"
TASKS_E2="getmoto__moto-6913,pydantic__pydantic-8500,dask__dask-7894"
COMMON="--prepared-summary $E/prepared_e2/replay_summary.json --candidate-stage-seconds 900 --grading-deadline-seconds 3600 --image-pull-seconds 3600 --eval-log-dir $R/eval_logs --artifacts-dir $R/artifacts"
export MILES_RH2_RUN_ID=reg-$(date +%Y%m%d)
echo "$(date -u +%FT%TZ) REG_START"
$PY scripts/replay_grade.py run $COMMON --task-ids "$TASKS_E1,$TASKS_E2" --candidate gold-dir:$E/gold_e2 --repeat 1 --ledger $R/ledger_reg_gold.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids "$TASKS_E1,$TASKS_E2" --candidate noop --repeat 1 --qualification-ledger $R/ledger_reg_gold.jsonl --ledger $R/ledger_reg_noop.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids "$TASKS_E1,$TASKS_E2" --candidate patch-dir:$E/cc_patches --repeat 1 --qualification-ledger $R/ledger_reg_gold.jsonl --ledger $R/ledger_reg_cc.jsonl
# P-A 真机对照：把 gold 补丁改成语法错误（只对 moto-6913 / dvc-5822 两题），期望 candidate_execution_failed；同一补丁无资格 → infra
mkdir -p $R/broken
for t in getmoto__moto-6913 iterative__dvc-5822; do
  $PY - "$E/gold_e2/$t.gold.patch" "$R/broken/$t.diff" <<'PYEOF'
import re, sys
src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
# 在第一个 hunk 的第一条新增行之后插入一行语法错误（保持 hunk 行数计数正确：把它加成 +1 行并修正 @@ 头）
lines = text.splitlines(keepends=True)
out = []; done = False; hdr_idx = None
for i, line in enumerate(lines):
    if not done and line.startswith("@@"):
        hdr_idx = len(out)
    out.append(line)
    if not done and hdr_idx is not None and line.startswith("+") and not line.startswith("+++"):
        out.append("+def rh2_broken(:\n"); done = True
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)", out[hdr_idx])
        a, al, b, bl, rest = m.groups(); bl = int(bl or 1) + 1
        out[hdr_idx] = f"@@ -{a},{al or 1} +{b},{bl} @@{rest}\n"
open(dst, "w", encoding="utf-8").write("".join(out))
print("wrote", dst, "broken:", done)
PYEOF
done
$PY scripts/replay_grade.py run $COMMON --task-ids getmoto__moto-6913,iterative__dvc-5822 --candidate patch-dir:$R/broken --repeat 1 --qualification-ledger $R/ledger_reg_gold.jsonl --ledger $R/ledger_reg_broken_q.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids getmoto__moto-6913,iterative__dvc-5822 --candidate patch-dir:$R/broken --repeat 1 --ledger $R/ledger_reg_broken_noq.jsonl
echo "$(date -u +%FT%TZ) REG_DONE"

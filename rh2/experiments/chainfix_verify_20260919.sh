#!/bin/bash
# 2026-09-19 链路修复真机验证（新机器，独立代码树 /work/claude_chainfix_20260919，不动 Codex 固定的 /work/full216_20260919/code）。
# 1) dvc-2141 noop/gold ×2：grader 有了 --init 后默认 512 进程配额下 gold 应为 1（B 线：无 --init 时 496–507 僵尸撞满配额 → 0）
# 2) modin-6298 noop/gold ×1：看 --init 是否也解决 modin 的静默退出/挂死（B 线 PID 2048 变体恢复过）
# 3) P-A 真机对照：dvc-5822 / moto-6913 gold 建资格 → 人为语法错误补丁带资格（期望 dvc candidate_execution_failed）
set -o pipefail
ROOT=/work/claude_chainfix_20260919
OLD=/work/full216_20260919
PY="env PYTHONPATH=$ROOT/code/rh2/src $OLD/code/rh2/.venv/bin/python"
R=$ROOT/replay; mkdir -p $R
cd $ROOT/code/rh2
COMMON="--prepared-summary $OLD/replay/prepared/replay_summary.json --candidate-stage-seconds 900 --grading-deadline-seconds 2400 --image-pull-seconds 3600 --eval-log-dir $R/eval_logs --artifacts-dir $R/artifacts"
export MILES_RH2_RUN_ID=chainfix-$(date +%Y%m%d)
echo "$(date -u +%FT%TZ) CHAINFIX_START"
$PY scripts/replay_grade.py run $COMMON --task-ids iterative__dvc-2141 --candidate noop --repeat 2 --ledger $R/ledger_dvc2141.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids iterative__dvc-2141 --candidate gold-dir:$OLD/replay/gold --repeat 2 --ledger $R/ledger_dvc2141.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids modin-project__modin-6298 --candidate noop --repeat 1 --ledger $R/ledger_modin6298.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids modin-project__modin-6298 --candidate gold-dir:$OLD/replay/gold --repeat 1 --ledger $R/ledger_modin6298.jsonl
$PY scripts/replay_grade.py run $COMMON --task-ids iterative__dvc-5822,getmoto__moto-6913 --candidate gold-dir:$OLD/replay/gold --repeat 1 --ledger $R/ledger_pa_gold.jsonl
mkdir -p $R/broken
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
echo "$(date -u +%FT%TZ) CHAINFIX_DONE"

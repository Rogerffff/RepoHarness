#!/usr/bin/env bash
# C5 双 lane 验证（miles 迁移,spike-log R6-ext 定形）：
#   lane A "pin 兼容"：默认 base（reference/miles pin）——adapters_miles 无失败,
#          且全部 skip 都是 integration_base 标记（新功能测试在旧 pin 自动豁免）。
#   lane B "integration 资格"：integration base——adapters_miles 无失败且零 skip
#          （证明 C1 新测试真的跑了,绿色才有效力——R6 §4 的核心要求）。
# 前置：reference/miles-rh2-integration 树哈希与 manifest 一致（防 base 漂移）。
# 重建方法见 docs/.../miles_spike/integration_base_manifest.json 的 rebuild 字段。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MANIFEST="$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json"
INTEGRATION="$ROOT/reference/miles-rh2-integration"

expected_tree=$(python3 -c "import json;print(json.load(open('$MANIFEST'))['expected_tree'])")
actual_tree=$(git -C "$INTEGRATION" rev-parse 'rh2-integration-v2^{tree}')
if [ "$expected_tree" != "$actual_tree" ]; then
  echo "FAIL: integration base 树哈希漂移 expected=$expected_tree actual=$actual_tree" >&2
  echo "      按 manifest 的 rebuild 步骤重建后重试。" >&2
  exit 1
fi
echo "integration base 树哈希校验通过：$actual_tree"

cd "$ROOT/rh2"

echo "=== lane A: pin 兼容（默认 base）==="
outA=$(uv run pytest tests/adapters_miles/ -q 2>&1 | tail -1)
echo "$outA"
echo "$outA" | grep -q "failed" && { echo "FAIL: lane A 有失败" >&2; exit 1; }
# skip 必须全部来自 integration_base 标记（-m 反选后应零 skip）
outA2=$(uv run pytest tests/adapters_miles/ -q -m "not integration_base" 2>&1 | tail -1)
echo "$outA2" | grep -qE "skipped" && { echo "FAIL: lane A 存在非 integration_base 的 skip: $outA2" >&2; exit 1; }
echo "lane A 通过（skip 全部为 integration_base 豁免）"

echo "=== lane B: integration 资格 ==="
outB=$(RH2_MILES_PATH="$INTEGRATION" uv run pytest tests/adapters_miles/ -q 2>&1 | tail -1)
echo "$outB"
echo "$outB" | grep -q "failed" && { echo "FAIL: lane B 有失败" >&2; exit 1; }
echo "$outB" | grep -qE "skipped" && { echo "FAIL: lane B 存在 skip——C1 测试未真正执行,绿色无效力" >&2; exit 1; }
echo "lane B 通过（零 skip,C1 测试全部真实执行）"
echo "C5 双 lane 全部通过"

#!/usr/bin/env bash
# C5 双 lane 验证（miles 迁移,spike-log R6-ext 定形;GPU 前收口第 3 项加固）：
#   lane A "pin 兼容"：默认 base（reference/miles pin）——精确计数匹配 manifest,
#          且全部 skip 都是 integration_base 标记（新功能测试在旧 pin 自动豁免）。
#   lane B "integration 资格"：integration base——精确计数匹配 manifest 且零 skip
#          （证明 C1 新测试真的跑了,绿色才有效力——R6 §4 的核心要求）。
# 绑定加固（codex 复核 C5 finding 的修复,全部以 manifest 为唯一事实源）：
#   1. integration checkout 校验**实际 HEAD^{tree}**（不是 branch ref——HEAD 切走
#      或 detach 时 branch ref 仍旧正确,校验就落空）+ `git status --porcelain`
#      必须干净（否则"校验一份代码、测试另一份工作树"）。
#   2. lane A 前校验 reference/miles 的 HEAD == pin（manifest base_pin_full）。
#   3. rh2 patch 文件 sha256 == manifest rh2_patch_sha256（rebuild 输入本身钉死）。
#   4. 两条 lane 断言**精确 passed/skipped 计数**（manifest expected_counts）——
#      删测试保绿的口子关死;测试增删必须同步改 manifest,构成可审计变更。
# 重建方法见 docs/.../miles_spike/integration_base_manifest.json 的 rebuild 字段。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MANIFEST="$ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/integration_base_manifest.json"
MANIFEST_DIR="$(dirname "$MANIFEST")"
INTEGRATION="$ROOT/reference/miles-rh2-integration"
PIN_CHECKOUT="$ROOT/reference/miles"

mf() { python3 -c "import json,sys;d=json.load(open('$MANIFEST'));print(d$1)"; }

expected_tree=$(mf "['expected_tree']")
pin_full=$(mf "['base_pin_full']")
patch_rel=$(mf "['rh2_patch']")
patch_sha_expected=$(mf "['rh2_patch_sha256']")
laneA_passed=$(mf "['expected_counts']['lane_a_passed']")
laneA_skipped=$(mf "['expected_counts']['lane_a_skipped']")
laneB_passed=$(mf "['expected_counts']['lane_b_passed']")
laneB_skipped=$(mf "['expected_counts']['lane_b_skipped']")

# -- 前置 1：integration checkout = 实际 HEAD 的树 + 干净工作树 --------------
actual_tree=$(git -C "$INTEGRATION" rev-parse 'HEAD^{tree}')
if [ "$expected_tree" != "$actual_tree" ]; then
  echo "FAIL: integration base 实际 HEAD 树哈希漂移 expected=$expected_tree actual=$actual_tree" >&2
  echo "      （校验对象是 HEAD^{tree},不是 branch ref——checkout 切走/detach 也会在这里红。）" >&2
  echo "      按 manifest 的 rebuild 步骤重建后重试。" >&2
  exit 1
fi
dirty=$(git -C "$INTEGRATION" status --porcelain)
if [ -n "$dirty" ]; then
  echo "FAIL: integration checkout 工作树不干净——被测代码 != 已校验的 HEAD 树:" >&2
  echo "$dirty" >&2
  exit 1
fi
echo "integration base 校验通过：HEAD^{tree}=$actual_tree,工作树干净"

# -- 前置 2：patch 文件 digest（rebuild 输入钉死）----------------------------
patch_sha_actual=$(shasum -a 256 "$MANIFEST_DIR/$patch_rel" | awk '{print $1}')
if [ "$patch_sha_expected" != "$patch_sha_actual" ]; then
  echo "FAIL: rh2 patch sha256 漂移 expected=$patch_sha_expected actual=$patch_sha_actual" >&2
  exit 1
fi
echo "rh2 patch digest 校验通过：$patch_sha_actual"

# -- 前置 2b：F2 零信号语义 patch 存档 digest（manifest rh2_patches_f2 表驱动,
#    0002/0003;与 0001 同性质——rebuild 输入本身钉死,存档漂移即红）----------
python3 - "$MANIFEST" "$MANIFEST_DIR" <<'PYEOF'
import hashlib, json, sys
manifest, mdir = sys.argv[1], sys.argv[2]
table = {
    k: v
    for k, v in json.load(open(manifest)).get("rh2_patches_f2", {}).items()
    if k.startswith("patches/")
}
if not table:
    sys.exit("FAIL: manifest 缺 rh2_patches_f2 patch 表（F2 语义 patch 未存档）")
for rel, want in table.items():
    got = hashlib.sha256(open(f"{mdir}/{rel}", "rb").read()).hexdigest()
    if got != want:
        sys.exit(f"FAIL: {rel} sha256 漂移 expected={want} actual={got}")
print(f"F2 patch digest 校验通过：{len(table)} 个")
PYEOF

# -- 前置 3：lane A 的默认 checkout 必须停在 pin ------------------------------
pin_head=$(git -C "$PIN_CHECKOUT" rev-parse HEAD)
if [ "$pin_head" != "$pin_full" ]; then
  echo "FAIL: reference/miles HEAD=$pin_head != pin $pin_full——lane A 的'pin 兼容'失去对象" >&2
  exit 1
fi
echo "reference/miles pin 校验通过：$pin_head"

cd "$ROOT/rh2"

# 尾行计数抽取："68 passed, 111 skipped in 6.81s" -> passed/skipped（缺省 0;
# 无匹配时 grep 退出码非零,用 || true 挡住 set -e/pipefail）
count_of() { # $1=尾行 $2=类别名
  local n
  n=$(echo "$1" | grep -oE "[0-9]+ $2" | head -1 | awk '{print $1}') || true
  echo "${n:-0}"
}
assert_counts() { # $1=lane 名 $2=尾行 $3=期望 passed $4=期望 skipped
  local p s
  p=$(count_of "$2" "passed"); s=$(count_of "$2" "skipped")
  if echo "$2" | grep -qE "[0-9]+ (failed|error)"; then
    echo "FAIL: $1 有失败/错误: $2" >&2; exit 1
  fi
  if [ "$p" != "$3" ] || [ "$s" != "$4" ]; then
    echo "FAIL: $1 计数偏离 manifest expected=${3}p/${4}s actual=${p}p/${s}s: $2" >&2
    echo "      测试增删须同步改 manifest 的 expected_counts（可审计变更）。" >&2
    exit 1
  fi
}

echo "=== lane A: pin 兼容（默认 base）==="
outA=$(uv run pytest tests/adapters_miles/ -q 2>&1 | tail -1)
echo "$outA"
assert_counts "lane A" "$outA" "$laneA_passed" "$laneA_skipped"
# skip 必须全部来自 integration_base 标记（-m 反选后应零 skip）
outA2=$(uv run pytest tests/adapters_miles/ -q -m "not integration_base" 2>&1 | tail -1)
echo "$outA2" | grep -qE "[0-9]+ skipped" && { echo "FAIL: lane A 存在非 integration_base 的 skip: $outA2" >&2; exit 1; }
echo "lane A 通过（精确计数 ${laneA_passed}p/${laneA_skipped}s,skip 全部为 integration_base 豁免）"

echo "=== lane B: integration 资格 ==="
outB=$(RH2_MILES_PATH="$INTEGRATION" uv run pytest tests/adapters_miles/ -q 2>&1 | tail -1)
echo "$outB"
assert_counts "lane B" "$outB" "$laneB_passed" "$laneB_skipped"
echo "lane B 通过（精确计数 ${laneB_passed}p/${laneB_skipped}s,零 skip——C1 测试全部真实执行）"
echo "C5 双 lane 全部通过"

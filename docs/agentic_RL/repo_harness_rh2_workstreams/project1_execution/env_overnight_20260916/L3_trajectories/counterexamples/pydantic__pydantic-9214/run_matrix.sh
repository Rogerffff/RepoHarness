#!/usr/bin/env bash
# L3 反例矩阵 · pydantic__pydantic-9214
#
# 【在哪里跑】只在任务镜像容器内跑，不在开发机上跑（开发机没有镜像，也不该改 /testbed）。
# 容器启动是占位命令，具体主机细节由执行方填：
#
#   IMAGE=xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9214:latest
#   docker run --rm \
#       -u "${CANDIDATE_USER:-agent}" \
#       -v "${HOST_CE_DIR}":/l3/ce:ro \
#       -v "${HOST_PATCH_DIR}":/l3/patches:ro \
#       -v "${HOST_OUT_DIR}":/l3/out \
#       "$IMAGE" bash /l3/ce/run_matrix.sh
#
# 【为什么要用候选用户】24 条轨迹的 init 记录 cwd=/testbed、memory_paths=/home/agent/...，
# 且 pip 输出为 "Defaulting to user installation because normal site-packages is not writeable"，
# 说明 agent 以非 root（agent）身份运行，而 SWE-bench 评分默认 root。两者的 site-packages
# 不同，必须用同一用户复现才能排除"装在 ~/.local 里"的干扰。若容器内无 agent 用户，
# 设 CANDIDATE_USER=root 并在报告里写明这一偏差。
#
# 【脚本里的 git 操作范围】只作用于容器内一次性的 /testbed 工作区，
# 不涉及宿主机仓库；开始时会把镜像自带的未提交改动存成 preexisting.diff 并在每次
# 复位后原样恢复，避免把"镜像出厂状态"洗掉。
set -u

IID="pydantic__pydantic-9214"
: "${WORKDIR:=/testbed}"
: "${CE_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${PATCH_DIR:=/l3/patches}"
: "${OUT_DIR:=/l3/out/${IID}}"
: "${STATES:=base gold candidate}"
: "${CANDIDATE_PATCH:=${PATCH_DIR}/${IID}.candidate.src_only.diff}"
: "${GOLD_PATCH:=${PATCH_DIR}/${IID}.gold.diff}"
: "${TEST_PATCH:=${PATCH_DIR}/${IID}.test_patch.diff}"
: "${DIAG_SRC:=${CE_DIR}/diagnostic_test.py}"
: "${PY:=}"

DIAG_REL="tests/l3_diagnostic_${IID//-/_}.py"
DIAG_DST="${WORKDIR}/${DIAG_REL}"
mkdir -p "$OUT_DIR" || { echo "cannot write $OUT_DIR" >&2; exit 2; }

# ---------------------------------------------------------------- python 解释器
if [ -z "$PY" ]; then
  for c in /opt/miniconda3/envs/testbed/bin/python /usr/local/bin/python python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
  done
fi
echo "[info] PY=$PY"
"$PY" -c "import sys; print('python', sys.version)" || exit 2
"$PY" -m pytest --version >/dev/null 2>&1 || {
  echo "[warn] pytest 不可用；本脚本不联网安装，请由执行方在镜像内用已有依赖解决后重跑" >&2
  echo '{"instance_id":"'"$IID"'","error":"pytest_unavailable"}' > "${OUT_DIR}/result.json"
  exit 3
}

# ---------------------------------------------------------------- 工作区快照/复位
PRE="${OUT_DIR}/preexisting.diff"
git -C "$WORKDIR" diff > "$PRE" 2>/dev/null || : > "$PRE"
git -C "$WORKDIR" status --porcelain > "${OUT_DIR}/preexisting_status.txt" 2>/dev/null || :
git -C "$WORKDIR" rev-parse HEAD > "${OUT_DIR}/head_commit.txt" 2>/dev/null || :

reset_ws() {
  git -C "$WORKDIR" checkout -- . 2>/dev/null
  rm -f "$DIAG_DST"
  if [ -s "$PRE" ]; then
    git -C "$WORKDIR" apply --whitespace=nowarn "$PRE" 2>/dev/null \
      || echo "[warn] 恢复 preexisting.diff 失败（已记录，后续结果按此偏差解读）"
  fi
}

apply_patch() {  # $1=patch file, $2=label
  [ -f "$1" ] || { echo "[error] 缺少补丁 $1" >&2; return 9; }
  if git -C "$WORKDIR" apply --whitespace=nowarn "$1" 2>"${OUT_DIR}/apply_${2}.err"; then
    echo "[info] applied $2"; return 0
  fi
  if (cd "$WORKDIR" && patch -p1 --forward --silent < "$1") 2>>"${OUT_DIR}/apply_${2}.err"; then
    echo "[info] applied $2 (patch -p1 fallback)"; return 0
  fi
  echo "[error] 应用 $2 失败，见 ${OUT_DIR}/apply_${2}.err" >&2
  return 9
}

run_pytest() {  # $1=run 名, 其余=pytest 参数
  local name="$1"; shift
  local log="${OUT_DIR}/${STATE}__${name}.txt"
  ( cd "$WORKDIR" && "$PY" -m pytest -rA -p no:cacheprovider --no-header -q "$@" ) \
    > "$log" 2>&1
  echo "[run] ${STATE}/${name} rc=$? -> $log"
}

# ---------------------------------------------------------------- 三种状态
for STATE in $STATES; do
  echo "=================== STATE=$STATE ==================="
  reset_ws
  case "$STATE" in
    base)      ;;
    gold)      apply_patch "$GOLD_PATCH" gold || continue ;;
    candidate) apply_patch "$CANDIDATE_PATCH" candidate || continue ;;
    *) echo "[error] 未知状态 $STATE" >&2; continue ;;
  esac

  # 诊断测试：四格矩阵（无描述 / 仅 Field / 仅 docstring / 两者都有且不同）
  cp "$DIAG_SRC" "$DIAG_DST"
  run_pytest diagnostic "$DIAG_REL"

  # base 自带的 RootModel 测试（P2P 54 条都在这个文件里）
  run_pytest base_root_model_tests tests/test_root_model.py

  # 官方执行面：打 test_patch 后跑 F2P 与被候选打破的那条 P2P
  if apply_patch "$TEST_PATCH" testpatch_${STATE}; then
    run_pytest official_f2p "tests/test_root_model.py::test_model_with_field_description"
    run_pytest official_p2p_both \
      "tests/test_root_model.py::test_model_with_both_docstring_and_field_description"
    run_pytest official_full_file tests/test_root_model.py
  fi
done
reset_ws

# ---------------------------------------------------------------- 汇总 JSON
"$PY" - "$OUT_DIR" "$IID" <<'PYEOF'
import json, os, re, sys
out_dir, iid = sys.argv[1], sys.argv[2]
RE_OUTCOME = re.compile(r"^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED)\s+(\S+)", re.M)
RE_TOTAL = re.compile(
    r"^=+\s*(.*?\b(?:passed|failed|error|no tests ran)\b.*?)\s*=+\s*$"
    r"|^\s*(\d+\s+(?:passed|failed|error)[^\n]*\bin\s+[\d.]+s?)\s*$", re.M | re.I)
res = {"instance_id": iid, "states": {}}
for fn in sorted(os.listdir(out_dir)):
    if not fn.endswith(".txt") or "__" not in fn:
        continue
    state, run = fn[:-4].split("__", 1)
    text = open(os.path.join(out_dir, fn), errors="replace").read()
    outcomes = {}
    for m in RE_OUTCOME.finditer(text):
        outcomes.setdefault(m.group(1), []).append(m.group(2))
    totals = [(m.group(1) or m.group(2) or "").strip() for m in RE_TOTAL.finditer(text)]
    res["states"].setdefault(state, {})[run] = {
        "log": fn,
        "summary_line": totals[-1] if totals else None,
        "counts": {k: len(v) for k, v in sorted(outcomes.items())},
        "failed": outcomes.get("FAILED", []) + outcomes.get("ERROR", []),
        "passed_sample": outcomes.get("PASSED", [])[:10],
        "output_chars": len(text),
    }
res["preexisting_status"] = open(os.path.join(out_dir, "preexisting_status.txt"), errors="replace").read() \
    if os.path.exists(os.path.join(out_dir, "preexisting_status.txt")) else None
res["head_commit"] = open(os.path.join(out_dir, "head_commit.txt"), errors="replace").read().strip() \
    if os.path.exists(os.path.join(out_dir, "head_commit.txt")) else None
with open(os.path.join(out_dir, "result.json"), "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps(res["states"], ensure_ascii=False, indent=1)[:4000])
print("\n[ok] wrote", os.path.join(out_dir, "result.json"))
PYEOF

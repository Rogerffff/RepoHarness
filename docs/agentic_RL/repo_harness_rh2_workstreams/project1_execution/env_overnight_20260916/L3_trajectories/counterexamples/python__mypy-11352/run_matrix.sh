#!/usr/bin/env bash
# L3 反例矩阵 · python__mypy-11352
#
# 【在哪里跑】只在任务镜像容器内跑，不在开发机上跑。容器启动是占位命令：
#
#   IMAGE=xingyaoww/sweb.eval.x86_64.python_s_mypy-11352:latest
#   docker run --rm \
#       -u "${CANDIDATE_USER:-agent}" \
#       -v "${HOST_CE_DIR}":/l3/ce:ro \
#       -v "${HOST_PATCH_DIR}":/l3/patches:ro \
#       -v "${HOST_OUT_DIR}":/l3/out \
#       "$IMAGE" bash /l3/ce/run_matrix.sh
#
# 【和其它四题不同的地方】本题的诊断不是 pytest 文件，而是一组最小 mypy 输入
# （diagnostic_test.sh），比较 base / gold / candidate 三态下 mypy 的**退出码与诊断行**。
# 官方那三条 F2P 走的是 mypy 自带的 testcheck 数据驱动用例。
#
# 【脚本里的 git 操作范围】只作用于容器内一次性的 /testbed 工作区。
set -u

IID="python__mypy-11352"
: "${WORKDIR:=/testbed}"
: "${CE_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${PATCH_DIR:=/l3/patches}"
: "${OUT_DIR:=/l3/out/${IID}}"
: "${STATES:=base gold candidate}"
: "${CANDIDATE_PATCH:=${PATCH_DIR}/${IID}.candidate.src_only.diff}"
: "${GOLD_PATCH:=${PATCH_DIR}/${IID}.gold.diff}"
: "${TEST_PATCH:=${PATCH_DIR}/${IID}.test_patch.diff}"
: "${DIAG_SH:=${CE_DIR}/diagnostic_test.sh}"
: "${PY:=}"

mkdir -p "$OUT_DIR" || { echo "cannot write $OUT_DIR" >&2; exit 2; }

if [ -z "$PY" ]; then
  for c in /opt/miniconda3/envs/testbed/bin/python /usr/local/bin/python python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
  done
fi
echo "[info] PY=$PY"
"$PY" -c "import sys; print('python', sys.version)" || exit 2

# mypyc 编译检查：若 mypy 是编译过的扩展，改 .py 不生效，三态结果会完全相同 —— 必须先排除
"$PY" -c 'import mypy.plugins.default as m; print("[preflight] plugins.default =", m.__file__)' \
  | tee "${OUT_DIR}/preflight_plugin_path.txt"
"$PY" -c 'import mypy, sys; print("[preflight] mypy pkg =", mypy.__file__)' \
  | tee -a "${OUT_DIR}/preflight_plugin_path.txt"

# ---------------------------------------------------------------- 工作区快照/复位
PRE="${OUT_DIR}/preexisting.diff"
git -C "$WORKDIR" diff > "$PRE" 2>/dev/null || : > "$PRE"
git -C "$WORKDIR" status --porcelain > "${OUT_DIR}/preexisting_status.txt" 2>/dev/null || :
git -C "$WORKDIR" rev-parse HEAD > "${OUT_DIR}/head_commit.txt" 2>/dev/null || :

reset_ws() {
  git -C "$WORKDIR" checkout -- . 2>/dev/null
  if [ -s "$PRE" ]; then
    git -C "$WORKDIR" apply --whitespace=nowarn "$PRE" 2>/dev/null \
      || echo "[warn] 恢复 preexisting.diff 失败（已记录）"
  fi
}

apply_patch() {  # $1=patch, $2=label
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
  ( cd "$WORKDIR" && "$PY" -m pytest -rA -p no:cacheprovider --no-header -q "$@" ) > "$log" 2>&1
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

  # 1) 最小 mypy 输入矩阵（本题的核心证据）
  CASES_DIR="/tmp/l3_mypy_cases_${STATE}" \
  OUT_JSON="${OUT_DIR}/${STATE}__mypy_cases.json" \
  WORKDIR="$WORKDIR" PY="$PY" \
    bash "$DIAG_SH" > "${OUT_DIR}/${STATE}__mypy_cases_stdout.txt" 2>&1
  echo "[run] ${STATE}/mypy_cases rc=$? -> ${OUT_DIR}/${STATE}__mypy_cases.json"

  # 2) 官方执行面：打 test_patch 后跑三条 F2P 与一条 P2P
  if apply_patch "$TEST_PATCH" testpatch_${STATE}; then
    if "$PY" -m pytest --version >/dev/null 2>&1; then
      run_pytest official_f2p \
        "mypy/test/testcheck.py::TypeCheckSuite::testAsyncContextManagerWithGenericFunction" \
        "mypy/test/testcheck.py::TypeCheckSuite::testAsyncContextManagerWithGenericFunctionAndSendType" \
        "mypy/test/testcheck.py::TypeCheckSuite::testContextManagerWithGenericFunctionAndSendType"
      run_pytest official_p2p \
        "mypy/test/testcheck.py::TypeCheckSuite::testContextManagerWithUnspecifiedArguments"
      # 整个 check-default-plugin.test 文件的所有用例
      run_pytest official_default_plugin_file mypy/test/testcheck.py -k "ContextManager"
    else
      echo "[warn] pytest 不可用，跳过官方面（记 unknown，不要在容器里安装）"
    fi
  fi
done
reset_ws

# ---------------------------------------------------------------- 三态对比
"$PY" - "$OUT_DIR" "$IID" <<'PYEOF'
import json, os, re, sys
out_dir, iid = sys.argv[1], sys.argv[2]
RE_OUTCOME = re.compile(r"^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED)\s+(\S+)", re.M)
res = {"instance_id": iid, "states": {}, "mypy_cases": {}, "comparison": {}}

for fn in sorted(os.listdir(out_dir)):
    if fn.endswith(".txt") and "__" in fn and not fn.endswith("_stdout.txt"):
        state, run = fn[:-4].split("__", 1)
        text = open(os.path.join(out_dir, fn), errors="replace").read()
        outcomes = {}
        for m in RE_OUTCOME.finditer(text):
            outcomes.setdefault(m.group(1), []).append(m.group(2))
        res["states"].setdefault(state, {})[run] = {
            "log": fn,
            "counts": {k: len(v) for k, v in sorted(outcomes.items())},
            "failed": outcomes.get("FAILED", []) + outcomes.get("ERROR", []),
            "passed": outcomes.get("PASSED", []),
        }
    if fn.endswith("__mypy_cases.json"):
        state = fn.split("__")[0]
        try:
            res["mypy_cases"][state] = json.load(open(os.path.join(out_dir, fn)))
        except Exception as e:
            res["mypy_cases"][state] = {"error": str(e)}

# 三态对比：分开"语义层"和"展示层"
states = [s for s in ("base", "gold", "candidate") if s in res["mypy_cases"]]
names = set()
for s in states:
    if isinstance(res["mypy_cases"][s], dict):
        names |= set(k for k in res["mypy_cases"][s] if not k.startswith("_"))
for name in sorted(names):
    row = {}
    for s in states:
        c = (res["mypy_cases"].get(s) or {}).get(name) or {}
        row[s] = {
            "rc": c.get("rc"),
            "semantic_signature": c.get("semantic_signature"),
            "revealed_types": [d.get("revealed") for d in (c.get("revealed_types") or [])],
        }
    sem = {s: json.dumps(row[s]["semantic_signature"], sort_keys=True) for s in states}
    disp = {s: json.dumps(row[s]["revealed_types"], sort_keys=True) for s in states}
    row["semantic_differs_gold_vs_candidate"] = (
        sem.get("gold") != sem.get("candidate") if "gold" in sem and "candidate" in sem else None)
    row["display_differs_gold_vs_candidate"] = (
        disp.get("gold") != disp.get("candidate") if "gold" in disp and "candidate" in disp else None)
    res["comparison"][name] = row

res["verdict_hint"] = {
    "cases_with_semantic_diff": sorted(
        k for k, v in res["comparison"].items() if v.get("semantic_differs_gold_vs_candidate")),
    "cases_with_display_only_diff": sorted(
        k for k, v in res["comparison"].items()
        if v.get("display_differs_gold_vs_candidate") and not v.get("semantic_differs_gold_vs_candidate")),
    "note": "cases_with_semantic_diff 非空 => 接受/拒绝的程序集合真的变了；"
            "只有 display_only 非空 => 仅 reveal_type 字符串不同，属 oracle 过严。",
}
with open(os.path.join(out_dir, "result.json"), "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps(res["verdict_hint"], ensure_ascii=False, indent=1))
print("[ok] wrote", os.path.join(out_dir, "result.json"))
PYEOF

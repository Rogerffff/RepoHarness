#!/usr/bin/env bash
# L7 反例矩阵 · 按 manifest.json 批量跑 base / gold / fake* 三类状态
#
# 【在哪里跑】只在任务镜像容器内跑，不在开发机上跑（开发机没有镜像，也不该改 /testbed）。
# 每题一个镜像，所以正常用法是"外层按 manifest 逐题起容器，容器内只跑匹配的那一题"。
# 容器启动是占位命令，具体主机细节由执行方填：
#
#   IMAGE=<manifest.tasks[i].image>
#   docker run --rm \
#       -u "${CANDIDATE_USER:-root}" \
#       --shm-size=1g \
#       -v "${HOST_KITS_DIR}":/l7/kits:ro \
#       -v "${HOST_PATCH_DIR}":/l7/patches:ro \
#       -v "${HOST_OUT_DIR}":/l7/out \
#       -e KIT="<instance_id>" \
#       "$IMAGE" bash /l7/kits/run_matrix.sh
#
# 【为什么提 CANDIDATE_USER】L3 的 24 条轨迹显示 agent 以非 root 的 `agent` 用户运行
# （init 记录 cwd=/testbed、memory_paths=/home/agent/...，pip 输出 "Defaulting to user installation"），
# 而 SWE-bench 评分默认 root。本套件比的是"同一用户下 base/gold/fake 的差别"，
# 所以三态必须用同一个用户跑；用哪个都行，但要在报告里写明。
#
# 【--shm-size】Project-MONAI__MONAI-4676 / 6523 的 P2P 含 DataLoader(num_workers=5) 与
# test_multiprocessing_*，共享内存不足会出 Bus error / worker killed，与本反例无关。
# 这两题请务必带 --shm-size=1g（或 --ipc=host）。
#
# 【脚本里的 git 操作范围】只作用于容器内一次性的 /testbed 工作区，不涉及宿主机仓库；
# 开始时把镜像自带的未提交改动存成 preexisting.diff，每次复位后原样恢复，避免洗掉"镜像出厂状态"。
#
# 【环境变量】
#   KIT        只跑这一个 kit（= instance_id）。不设则按 /testbed 的 HEAD 自动匹配 base_commit；
#              仍匹配不上则跑 manifest 里全部任务（多半会在打补丁时失败，只用于调试）。
#   STATES     默认 "base gold fake"。"fake" 展开成该题全部 fake 变体（fake / fake_alt / ...）。
#              也可以直接写变体名，例如 STATES="base fake_conftest"。
#   RUN_DIAG   默认 1：跑 kits/<kit>/diagnostic_test.py（判别用例，不是官方判分面）。
#   RUN_BLAST  默认 0：置 1 时跑 manifest 的 extra_runs（影响面证据，不进 reward）。
#   MANIFEST / PATCH_DIR / KITS_DIR / OUT_DIR / WORKDIR / PY 可覆盖默认路径。
set -u

: "${KITS_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${MANIFEST:=${KITS_DIR}/../manifest.json}"
: "${PATCH_DIR:=/l7/patches}"
: "${OUT_DIR:=/l7/out}"
: "${WORKDIR:=/testbed}"
: "${STATES:=base gold fake}"
: "${RUN_DIAG:=1}"
: "${RUN_BLAST:=0}"
: "${KIT:=}"
: "${PY:=}"

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
  echo '{"error":"pytest_unavailable"}' > "${OUT_DIR}/result.json"
  exit 3
}
[ -f "$MANIFEST" ] || { echo "[error] 找不到 manifest: $MANIFEST" >&2; exit 2; }

HEAD_SHA="$(git -C "$WORKDIR" rev-parse HEAD 2>/dev/null || echo unknown)"
echo "[info] WORKDIR=$WORKDIR HEAD=$HEAD_SHA"

# ---------------------------------------------------------------- 选题
# 输出每行：kit<TAB>字段名<TAB>值   （字段：gold/test/diag_dest/fake:<id>/extra:<name>/official/f2p）
PLAN="${OUT_DIR}/_plan.tsv"
"$PY" - "$MANIFEST" "$KIT" "$HEAD_SHA" > "$PLAN" <<'PYEOF'
import json, sys
mf, kit, head = sys.argv[1], sys.argv[2], sys.argv[3]
tasks = json.load(open(mf))["tasks"]
if kit:
    sel = [t for t in tasks if t["kit"] == kit]
elif head != "unknown":
    sel = [t for t in tasks if t["base_commit"].startswith(head) or head.startswith(t["base_commit"][:12])]
else:
    sel = []
if not sel:
    sel = tasks
for t in sel:
    k = t["kit"]
    print(f"{k}\tgold\t{t['gold_patch']}")
    print(f"{k}\ttest\t{t['test_patch']}")
    print(f"{k}\tdiag_dest\t{t.get('diagnostic_test') or ''}")
    print(f"{k}\tofficial\t{' '.join(t['official_args'])}")
    print(f"{k}\tf2p\t{' '.join(t['f2p_args'])}")
    print(f"{k}\tnflag\t{'-n0' if '-n0' in (t.get('eval_cmd') or '') else ''}")
    for fk in t["fakes"]:
        print(f"{k}\tfake:{fk['id']}\t{fk['patch']}")
    for e in t.get("extra_runs", []):
        print(f"{k}\textra:{e['name']}\t{' '.join(e['args'])}")
PYEOF
KITS_TO_RUN="$(cut -f1 "$PLAN" | sort -u)"
echo "[info] 本次要跑的 kit: $(echo $KITS_TO_RUN | tr '\n' ' ')"

field() {  # $1=kit $2=字段名 -> 值（取第一条）
  awk -F'\t' -v k="$1" -v f="$2" '$1==k && $2==f {print $3; exit}' "$PLAN"
}
fake_ids() {  # $1=kit -> 该题全部 fake 变体 id
  awk -F'\t' -v k="$1" '$1==k && $2 ~ /^fake:/ {sub(/^fake:/,"",$2); print $2}' "$PLAN"
}
extra_names() {
  awk -F'\t' -v k="$1" '$1==k && $2 ~ /^extra:/ {sub(/^extra:/,"",$2); print $2}' "$PLAN"
}

# ---------------------------------------------------------------- 工作区快照/复位
PRE="${OUT_DIR}/preexisting.diff"
git -C "$WORKDIR" diff > "$PRE" 2>/dev/null || : > "$PRE"
git -C "$WORKDIR" status --porcelain > "${OUT_DIR}/preexisting_status.txt" 2>/dev/null || :
echo "$HEAD_SHA" > "${OUT_DIR}/head_commit.txt"
DIAG_DST=""

reset_ws() {
  git -C "$WORKDIR" checkout -- . 2>/dev/null
  # 只清掉本脚本自己放进去的文件，不动镜像自带的未跟踪产物
  [ -n "$DIAG_DST" ] && rm -f "$DIAG_DST"
  # fake_conftest 之类的补丁会新建文件（git checkout 不会删未跟踪文件），按本次记录的清单删除
  if [ -n "${L7_NEW_FILES:-}" ]; then
    for f in $L7_NEW_FILES; do rm -f "${WORKDIR}/${f}"; done
  fi
  if [ -s "$PRE" ]; then
    git -C "$WORKDIR" apply --whitespace=nowarn "$PRE" 2>/dev/null \
      || echo "[warn] 恢复 preexisting.diff 失败（已记录，后续结果按此偏差解读）"
  fi
}

apply_patch() {  # $1=补丁绝对路径 $2=标签
  [ -f "$1" ] || { echo "[error] 缺少补丁 $1" >&2; return 9; }
  # 记下这个补丁会新建哪些文件，便于 reset_ws 清理
  L7_NEW_FILES="${L7_NEW_FILES:-} $(grep -B1 '^new file mode' "$1" | sed -n 's|^diff --git a/.* b/||p' | tr '\n' ' ')"
  if git -C "$WORKDIR" apply --whitespace=nowarn "$1" 2>"${OUT_DIR}/apply_${2}.err"; then
    echo "[info] applied $2"; return 0
  fi
  if (cd "$WORKDIR" && patch -p1 --forward --silent < "$1") 2>>"${OUT_DIR}/apply_${2}.err"; then
    echo "[info] applied $2 (patch -p1 fallback)"; return 0
  fi
  echo "[error] 应用 $2 失败，见 ${OUT_DIR}/apply_${2}.err" >&2
  return 9
}

run_pytest() {  # $1=kit $2=run 名 $3=pytest 参数（空格分隔，节点 id 里不含空格，已在生成侧校验）
  local kit="$1" name="$2"; shift 2
  local log="${OUT_DIR}/${kit}/${STATE}__${name}.txt"
  mkdir -p "${OUT_DIR}/${kit}"
  # shellcheck disable=SC2086
  ( cd "$WORKDIR" && "$PY" -m pytest -rA -p no:cacheprovider --no-header $NFLAG $* ) > "$log" 2>&1
  echo "[run] ${kit}/${STATE}/${name} rc=$? -> $log"
}

# ---------------------------------------------------------------- 主循环
for KIT_ID in $KITS_TO_RUN; do
  echo "################ KIT=$KIT_ID ################"
  mkdir -p "${OUT_DIR}/${KIT_ID}"
  GOLD_P="${PATCH_DIR}/$(field "$KIT_ID" gold)"
  TEST_P="${PATCH_DIR}/$(field "$KIT_ID" test)"
  DIAG_REL="$(field "$KIT_ID" diag_dest)"
  OFFICIAL="$(field "$KIT_ID" official)"
  F2PARGS="$(field "$KIT_ID" f2p)"
  NFLAG="$(field "$KIT_ID" nflag)"
  DIAG_SRC="${KITS_DIR}/${KIT_ID}/diagnostic_test.py"
  DIAG_DST=""
  [ -n "$DIAG_REL" ] && DIAG_DST="${WORKDIR}/${DIAG_REL}"

  # 把 STATES 里的 "fake" 展开成该题的全部 fake 变体
  EXPANDED=""
  for s in $STATES; do
    if [ "$s" = "fake" ]; then
      for fid in $(fake_ids "$KIT_ID"); do EXPANDED="$EXPANDED $fid"; done
    else
      EXPANDED="$EXPANDED $s"
    fi
  done

  for STATE in $EXPANDED; do
    echo "=================== ${KIT_ID} STATE=$STATE ==================="
    # 先复位（会清掉上一个状态新建的文件，例如 fake_conftest 的 tests/conftest.py
    # 与 test_patch 新增的测试文件），再把新建清单清空
    reset_ws
    L7_NEW_FILES=""
    case "$STATE" in
      base) ;;
      gold) apply_patch "$GOLD_P" "${KIT_ID}_gold" || continue ;;
      *)
        FP="$(awk -F'\t' -v k="$KIT_ID" -v f="fake:$STATE" '$1==k && $2==f {print $3; exit}' "$PLAN")"
        if [ -z "$FP" ]; then echo "[error] ${KIT_ID} 没有名为 $STATE 的 fake 变体" >&2; continue; fi
        apply_patch "${PATCH_DIR}/${FP}" "${KIT_ID}_${STATE}" || continue ;;
    esac

    # 判别用例：断言 base 的既有公开行为与题面目标，**不是**官方判分面的一部分
    if [ "$RUN_DIAG" = "1" ] && [ -n "$DIAG_REL" ] && [ -f "$DIAG_SRC" ]; then
      mkdir -p "$(dirname "$DIAG_DST")"
      cp "$DIAG_SRC" "$DIAG_DST"
      run_pytest "$KIT_ID" diagnostic "$DIAG_REL"
      rm -f "$DIAG_DST"
    fi

    # 官方执行面：打 test_patch 后跑 F2P∪P2P（这一条决定"是否满分"）
    if apply_patch "$TEST_P" "${KIT_ID}_${STATE}_testpatch"; then
      run_pytest "$KIT_ID" official_all $OFFICIAL
      run_pytest "$KIT_ID" official_f2p $F2PARGS
      if [ "$RUN_BLAST" = "1" ]; then
        for en in $(extra_names "$KIT_ID"); do
          EA="$(awk -F'\t' -v k="$KIT_ID" -v f="extra:$en" '$1==k && $2==f {print $3; exit}' "$PLAN")"
          run_pytest "$KIT_ID" "$en" $EA
        done
      fi
    fi
  done
  reset_ws
  L7_NEW_FILES=""
done

# ---------------------------------------------------------------- 汇总 JSON
"$PY" - "$OUT_DIR" "$MANIFEST" "$PLAN" <<'PYEOF'
import json, os, re, sys
out_dir, mf, plan = sys.argv[1], sys.argv[2], sys.argv[3]
manifest = {t["kit"]: t for t in json.load(open(mf))["tasks"]}
kits = sorted({l.split("\t")[0] for l in open(plan) if l.strip()})
RE_OUTCOME = re.compile(r"^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED)\s+(\S+)", re.M)
RE_TOTAL = re.compile(
    r"^=+\s*(.*?\b(?:passed|failed|error|no tests ran)\b.*?)\s*=+\s*$"
    r"|^\s*(\d+\s+(?:passed|failed|error)[^\n]*\bin\s+[\d.]+s?)\s*$", re.M | re.I)
res = {"kits": {}}
for kit in kits:
    d = os.path.join(out_dir, kit)
    if not os.path.isdir(d):
        continue
    t = manifest.get(kit, {})
    f2p, p2p = set(t.get("f2p", [])), set(t.get("p2p", []))
    expected = {f["id"]: f["expected"] for f in t.get("fakes", [])}
    kres = {"expected": expected, "states": {}}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt") or "__" not in fn:
            continue
        state, run = fn[:-4].split("__", 1)
        text = open(os.path.join(d, fn), errors="replace").read()
        outcomes = {}
        for m in RE_OUTCOME.finditer(text):
            outcomes.setdefault(m.group(1), []).append(m.group(2))
        totals = [(m.group(1) or m.group(2) or "").strip() for m in RE_TOTAL.finditer(text)]
        passed = set(outcomes.get("PASSED", []))
        bad = set(outcomes.get("FAILED", [])) | set(outcomes.get("ERROR", []))
        entry = {
            "log": f"{kit}/{fn}",
            "summary_line": totals[-1] if totals else None,
            "counts": {k: len(v) for k, v in sorted(outcomes.items())},
            "failed": sorted(bad)[:40],
            "output_chars": len(text),
        }
        if run == "official_all" and (f2p or p2p):
            entry["f2p_passed"] = sorted(f2p & passed)
            entry["f2p_not_passed"] = sorted(f2p - passed)
            entry["p2p_not_passed"] = sorted(p2p - passed)
            entry["full_score"] = (not (f2p - passed)) and (not (p2p - passed))
        kres["states"].setdefault(state, {})[run] = entry
    # 与预期对照
    verdicts = {}
    for state, runs in kres["states"].items():
        oa = runs.get("official_all")
        if oa is None or "full_score" not in oa:
            verdicts[state] = "unknown"
        else:
            verdicts[state] = "full_score" if oa["full_score"] else "not_full"
    kres["observed"] = verdicts
    kres["matches_expectation"] = {
        fid: (verdicts.get(fid) == exp if exp != "unknown" else None)
        for fid, exp in expected.items() if fid in verdicts}
    res["kits"][kit] = kres
pre = os.path.join(out_dir, "preexisting_status.txt")
res["preexisting_status"] = open(pre, errors="replace").read() if os.path.exists(pre) else None
head = os.path.join(out_dir, "head_commit.txt")
res["head_commit"] = open(head, errors="replace").read().strip() if os.path.exists(head) else None
with open(os.path.join(out_dir, "result.json"), "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
for kit, kres in res["kits"].items():
    print(kit, "观测:", json.dumps(kres["observed"], ensure_ascii=False),
          "对照:", json.dumps(kres["matches_expectation"], ensure_ascii=False))
print("\n[ok] wrote", os.path.join(out_dir, "result.json"))
PYEOF

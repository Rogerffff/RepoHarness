#!/usr/bin/env bash
# 固定候选的 CPU 行为裁决（Codex 09-22 §9.3 高优先工作包 B）：在题目的公开镜像里分别应用 noop / gold / 指定候选的
# **源码段**（自动剔除测试文件段），以 testbed 解释器运行一段公开的行为检查脚本，把每个变体的输出并排落盘。
# 不评分、不改原题、不写历史 evidence；产物只是"输入 → 预期依据 → base / gold / 候选结果"表的原始材料。
#
# 用法：behavior_check.sh <instance_id> <image> <check_script> <out_dir> [name=patch ...]
#   例：behavior_check.sh getmoto__moto-5752 xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752:latest \
#         checks/moto5752.py /work/probe/runs/behavior/moto5752 \
#         gold=/work/probe/replay/gold/getmoto__moto-5752.gold.patch \
#         ds_a1=/work/probe/runs/matrix/attempts/getmoto__moto-5752/deepseek-v4-pro/a1/candidate/getmoto__moto-5752.diff
#   noop 变体总是自动包含。check_script 在容器内以 `python /x/check.py` 运行（cwd=/testbed，conda testbed 已激活，
#   无公网），其 stdout 逐行以 RESULT= 开头的 JSON 会被汇总到 <out_dir>/summary.json。
set -u
IID=${1:?instance_id}; IMG=${2:?image}; CHECK=${3:?check script}; OUT=${4:?out dir}; shift 4
mkdir -p "$OUT"
declare -a NAMES=(noop); declare -A PATCH=([noop]=/dev/null)
for kv in "$@"; do n=${kv%%=*}; p=${kv#*=}; NAMES+=("$n"); PATCH[$n]=$p; done
for name in "${NAMES[@]}"; do
  d="$OUT/$name"; mkdir -p "$d"; src=${PATCH[$name]}
  if [ "$src" != /dev/null ]; then
    python3 - "$src" "$d/src_only.diff" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8", errors="replace").read()
segs = [s for s in re.split(r"(?m)^(?=diff --git )", t) if s.startswith("diff --git ")]
def is_test(h):
    p = h.split(" b/", 1)[1] if " b/" in h else h
    return bool(re.search(r"(^|/)tests?(/|$)|(^|/)test_[^/]*\.py$|_test\.py$|\.test$|(^|/)testing/", p))
keep = [s for s in segs if not is_test(s.split("\n", 1)[0])]
dropped = [s.split("\n", 1)[0][11:] for s in segs if is_test(s.split("\n", 1)[0])]
open(sys.argv[2], "w", encoding="utf-8").write("".join(keep))
print("kept:", [s.split("\n",1)[0][11:80] for s in keep]); print("dropped test segments:", dropped)
PY
  fi
  cp "$CHECK" "$d/check.py"
  docker run --rm --init --network none --cpus 2 --memory 4g -v "$d:/x" "$IMG" bash -c '
set -o pipefail; source /opt/miniconda3/bin/activate testbed 2>/dev/null; cd /testbed
if [ -s /x/src_only.diff ]; then git apply --check /x/src_only.diff && git apply /x/src_only.diff && echo APPLY=ok || { echo APPLY=failed; exit 3; }; else echo APPLY=noop; fi
git status --porcelain | head -20
export AWS_DEFAULT_REGION=eu-west-1 AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_SESSION_TOKEN=testing TEST_SERVER_MODE=false
timeout 1500 python /x/check.py; echo CHECK_RC=$?' > "$d/out.txt" 2>&1
  echo "== $name: $(grep -E '^(APPLY=|CHECK_RC=)' "$d/out.txt" | tr '\n' ' ')"
done
python3 - "$OUT" "${NAMES[@]}" <<'PY'
import json, sys, os
out = sys.argv[1]; res = {}
for name in sys.argv[2:]:
    rows = []
    for ln in open(os.path.join(out, name, "out.txt"), encoding="utf-8", errors="replace"):
        if ln.startswith("RESULT="):
            try: rows.append(json.loads(ln[7:]))
            except Exception: rows.append({"raw": ln.strip()[:300]})
    res[name] = rows
json.dump(res, open(os.path.join(out, "summary.json"), "w"), ensure_ascii=False, indent=1)
keys = sorted({r.get("case") for rows in res.values() for r in rows if isinstance(r, dict) and "case" in r})
print("| case | " + " | ".join(res) + " |"); print("| --- | " + " | ".join("---" for _ in res) + " |")
for k in keys:
    print("| " + str(k) + " | " + " | ".join(str(next((r.get("value") for r in res[n] if r.get("case") == k), "—")) for n in res) + " |")
PY

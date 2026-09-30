#!/usr/bin/env bash
# 聚焦复核（v3）私有对照：在一次性、断网容器里逐个“候选 × 测试版本”运行 F2P。不是正式评分。
# 容器外调用示例（仓库根目录；先等机器上运行中的容器少于 3 个）：
#   EXP=$PWD/rh2/experiments/category3_cloud_20260929/conan13403
#   EVID=$PWD/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/conan-io__conan-13403/evidence
#   docker run --rm --network none -v $EXP:/exp:ro -v $EVID:/evid:ro -v <输出目录>:/out \
#     -e TAG=A -e RUNAS=root -e TESTS="orig v2 v3" -e CANDS="base gold ..." \
#     c3keep/conan13403:src bash /exp/review_v3/run_matrix.sh
# 候选：base（不打补丁）、gold、作者与首轮复核者候选（/exp/<名>.patch）、本轮候选（/exp/review_v3/cands/<名>.patch）。
# 测试：orig（原 test_patch）、v2、v3（作者补丁）、v3_*（/exp/review_v3/tests/<名>.patch，私有变体）。
# 每个组合先复位工作树（git checkout/clean、删 /path），再套候选补丁与测试补丁；
# 测试命令同评分包：pytest -n0 -rA -p no:cacheprovider conans/test/unittests/tools/gnu/autotools_test.py，
# 按 F2P test_source_folder_works 是否 PASSED 判分（P2P 为空）。RUNAS=54322 时用 setpriv 以评分 UID 运行 pytest。
set -u
source /opt/miniconda3/bin/activate testbed >/dev/null 2>&1
cd /testbed
OUT=/out/$TAG
mkdir -p "$OUT/logs"
: > "$OUT/results.tsv"
cand_patch() {
  case $1 in
    base) echo "" ;;
    gold) echo /evid/gold/conan-io__conan-13403.gold.patch ;;
    r3_*|w3_*) echo /exp/review_v3/cands/$1.patch ;;
    *) echo /exp/$1.patch ;;
  esac
}
test_patch() {
  case $1 in
    orig) echo /evid/materials/original_test.patch ;;
    v2) echo /exp/revised_test_v2.patch ;;
    v3) echo /exp/revised_test_v3.patch ;;
    *) echo /exp/review_v3/tests/$1.patch ;;
  esac
}
for T in $TESTS; do
  for C in $CANDS; do
    LOG="$OUT/logs/${T}__${C}.log"
    git checkout -q -- . && git clean -fdq
    rm -rf /path
    ok=1
    CP=$(cand_patch "$C")
    if [ -n "$CP" ]; then git apply "$CP" > "$LOG" 2>&1 || ok=0; else : > "$LOG"; fi
    git apply "$(test_patch "$T")" >> "$LOG" 2>&1 || ok=0
    r=APPLYFAIL; loc=""; eline=""
    if [ $ok = 1 ]; then
      if [ "$RUNAS" = root ]; then
        timeout 180 pytest -n0 -rA -p no:cacheprovider conans/test/unittests/tools/gnu/autotools_test.py >> "$LOG" 2>&1
      else
        timeout 180 setpriv --reuid="$RUNAS" --regid="$RUNAS" --clear-groups env HOME=/tmp \
          pytest -n0 -rA -p no:cacheprovider conans/test/unittests/tools/gnu/autotools_test.py >> "$LOG" 2>&1
      fi
      if grep -q "^PASSED conans/test/unittests/tools/gnu/autotools_test.py::test_source_folder_works" "$LOG"; then r=1; else r=0; fi
      loc=$(grep -oE "[A-Za-z_]+\.py:[0-9]+: [A-Za-z]+" "$LOG" | tail -1)
      # 最后一段回溯里 ">" 行之后的第一条 "E" 行（异常链时即最终抛出的那一个）
      eline=$(awk '/^>/{buf=""; cap=1; next} cap && /^E /{if (buf == "") buf = $0} END{print buf}' "$LOG" \
        | tr -s ' ' | cut -c1-150)
    fi
    printf "%s\t%s\t%s\t%s\t%s\n" "$T" "$C" "$r" "$loc" "$eline" >> "$OUT/results.tsv"
  done
done
echo "done $TAG $(wc -l < "$OUT/results.tsv")"

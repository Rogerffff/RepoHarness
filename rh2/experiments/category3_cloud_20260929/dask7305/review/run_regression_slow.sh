#!/usr/bin/env bash
# （含 --runslow）更宽的回归对照（私有，root、断网、一次性容器）：base、gold 与候选在 dataframe 其它用到 set_index 的测试文件上
# （-k 'set_index or divisions or quantile or repartition or sort'）的失败集合。
# 用法：run_regression.sh <输出目录> <候选...>（候选名同 run_private.py：base | gold | 作者或复核者候选）
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$1; shift
mkdir -p "$OUT"
FILES="dask/dataframe/tests/test_dataframe.py dask/dataframe/tests/test_multi.py dask/dataframe/tests/test_categorical.py dask/dataframe/tests/test_merge_column_and_index.py dask/dataframe/tests/test_rolling.py dask/dataframe/io/tests/test_csv.py dask/dataframe/io/tests/test_io.py"
for C in "$@"; do
  case $C in
    base) P="" ;;
    gold) P="$HERE/work/gold.patch" ;;
    *) if [ -f "$HERE/candidates/$C.patch" ]; then P="$HERE/candidates/$C.patch"; else P="$HERE/../candidates/$C.patch"; fi ;;
  esac
  "$HERE/wait_free.sh" || exit 1
  MNT=(); APPLY=""
  if [ -n "$P" ]; then MNT=(-v "$P:/in/cand.patch:ro"); APPLY="git apply /in/cand.patch && "; fi
  T0=$(date +%s)
  docker run --rm --network none -e PATH=/opt/miniconda3/envs/testbed/bin:/usr/local/bin:/usr/bin:/bin -w /testbed "${MNT[@]}" c3keep/dask7305:src \
    bash -c "${APPLY} pytest -n0 -rA --color=no -p no:cacheprovider --runslow -k 'set_index or divisions or quantile or repartition or sort' $FILES" > "$OUT/$C.log" 2>&1
  echo "$C rc=$? $(( $(date +%s) - T0 ))s $(grep -E '^=+ .*(passed|failed).* =+$' "$OUT/$C.log" | tail -1)"
done

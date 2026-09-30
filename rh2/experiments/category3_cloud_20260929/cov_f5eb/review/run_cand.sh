#!/bin/bash
# 私有模拟评分（复核者）：在一次性、断网容器内执行。/rv 为只读挂载的 review 目录。
# 用法：run_cand.sh <候选名|noop> <测试版本...>；测试版本 X 对应 /rv/materials/test_1_X.py
set -u
cand=$1; shift
cd /testbed
if [ "$cand" = "gold_official" ]; then
  git apply /rv/materials/gold_official.patch || { echo "APPLY_FAIL"; exit 3; }
elif [ "${cand#au_}" != "$cand" ]; then
  # 作者候选：原样 git apply 作者目录（只读挂载在 /au）里的补丁
  git apply /au/${cand#au_}.patch || { echo "APPLY_FAIL"; exit 3; }
elif [ "$cand" != "noop" ]; then
  cp -r /rv/cands/$cand/files/. /testbed/ || { echo "COPY_FAIL"; exit 3; }
fi
echo "=====DIFF"
git diff --stat
for tv in "$@"; do
  rm -rf /testbed/r2e_tests; mkdir /testbed/r2e_tests
  cp /r2e_tests/__init__.py /testbed/r2e_tests/
  cp /rv/materials/test_1_$tv.py /testbed/r2e_tests/test_1.py
  echo "=====BEGIN $tv $(sha256sum /testbed/r2e_tests/test_1.py | cut -c1-12)"
  bash run_tests.sh 2>&1
  echo "=====END $tv rc=$?"
done

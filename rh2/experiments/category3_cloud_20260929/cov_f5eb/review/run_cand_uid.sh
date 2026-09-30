#!/bin/bash
# 同 run_cand.sh，但测试以 uid 54322 运行（私有近似：放开 /root 遍历权限、testbed 改属主；不套正式 profile）
set -u
cand=$1; shift
cd /testbed
if [ "$cand" = "gold_official" ]; then
  git apply /rv/materials/gold_official.patch || { echo "APPLY_FAIL"; exit 3; }
elif [ "${cand#au_}" != "$cand" ]; then
  git apply /au/${cand#au_}.patch || { echo "APPLY_FAIL"; exit 3; }
elif [ "$cand" != "noop" ]; then
  cp -r /rv/cands/$cand/files/. /testbed/ || { echo "COPY_FAIL"; exit 3; }
fi
echo "=====DIFF"
git diff --stat
chmod 755 /root && mkdir -p /tmp/u54322 && chown 54322:54322 /tmp/u54322
for tv in "$@"; do
  rm -rf /testbed/r2e_tests; mkdir /testbed/r2e_tests
  cp /r2e_tests/__init__.py /testbed/r2e_tests/
  cp /rv/materials/test_1_$tv.py /testbed/r2e_tests/test_1.py
  chown -R 54322:54322 /testbed
  echo "=====BEGIN $tv $(sha256sum /testbed/r2e_tests/test_1.py | cut -c1-12)"
  HOME=/tmp/u54322 TMPDIR=/tmp/u54322 setpriv --reuid=54322 --regid=54322 --clear-groups bash run_tests.sh 2>&1
  echo "=====END $tv rc=$?"
done
